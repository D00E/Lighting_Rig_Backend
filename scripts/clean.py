"""Wipe all rows from the SQL tables and all files from the storage bucket.

Tables are truncated (not dropped), and storage objects are deleted (the
bucket itself is preserved).  Run this script from the repository root:

    python scripts/clean.py
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg

from app.db import get_connection, get_database_url
from app.services.storage import get_supabase_url, get_supabase_key, get_supabase_bucket


DEFAULT_BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")


# ---------------------------------------------------------------------------
# Backend management (mirrors import_design.py)
# ---------------------------------------------------------------------------

def health_url_for_base(backend_base_url: str) -> str:
    return f"{backend_base_url.rstrip('/')}/health"


def is_local_backend_url(backend_base_url: str) -> bool:
    parsed = urllib.parse.urlparse(backend_base_url)
    return parsed.scheme in {"http", ""} and parsed.hostname in {"127.0.0.1", "localhost"}


def check_backend_health(backend_base_url: str, timeout_seconds: float = 1.5) -> bool:
    request = urllib.request.Request(health_url_for_base(backend_base_url), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError):
        return False


def start_local_backend_process(backend_base_url: str) -> subprocess.Popen:
    parsed = urllib.parse.urlparse(backend_base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8000
    command = [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", host, "--port", str(port),
    ]
    return subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_backend_ready(backend_base_url: str, timeout_seconds: int) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if check_backend_health(backend_base_url):
            return True
        time.sleep(0.5)
    return False


def stop_backend_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


# ---------------------------------------------------------------------------
# Postgres container management
# ---------------------------------------------------------------------------

def check_postgres_running() -> bool:
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        return True
    except Exception:
        return False


def start_postgres_container() -> None:
    subprocess.run(
        ["docker", "compose", "up", "-d", "postgres"],
        cwd=str(PROJECT_ROOT),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_postgres_ready(timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if check_postgres_running():
            return True
        time.sleep(1)
    return False


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

def truncate_tables() -> None:
    """TRUNCATE design_assets and designs, resetting sequences."""
    print("Truncating SQL tables...")
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE design_assets, designs RESTART IDENTITY CASCADE;")
        connection.commit()
    print("  design_assets — cleared")
    print("  designs       — cleared")


# ---------------------------------------------------------------------------
# Storage helpers (stdlib only, mirrors app/services/storage.py style)
# ---------------------------------------------------------------------------

def _storage_request(method: str, path: str, body: dict | None = None) -> tuple[int, bytes]:
    supabase_url = get_supabase_url()
    supabase_key = get_supabase_key()
    url = f"{supabase_url}/storage/v1{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def _list_objects(bucket: str, prefix: str) -> list[dict]:
    """Return all objects under *prefix* (one level deep)."""
    status, body = _storage_request(
        "POST",
        f"/object/list/{bucket}",
        {"prefix": prefix, "limit": 1000, "offset": 0},
    )
    if status not in (200, 201):
        raise RuntimeError(f"Listing storage failed ({status}): {body.decode()}")
    return json.loads(body)


def _collect_all_paths(bucket: str) -> list[str]:
    """Walk the bucket recursively and return every file path."""
    paths: list[str] = []
    # Top-level items (callsign folders or loose files)
    roots = _list_objects(bucket, "")
    for item in roots:
        name: str = item["name"]
        if item.get("id") is None:
            # It's a pseudo-folder — list its contents
            children = _list_objects(bucket, name)
            for child in children:
                child_name: str = child["name"]
                if child.get("id") is not None:
                    paths.append(f"{name}/{child_name}")
        else:
            paths.append(name)
    return paths


def _delete_objects(bucket: str, paths: list[str]) -> None:
    """Delete a list of storage paths in one request."""
    status, body = _storage_request(
        "DELETE",
        f"/object/{bucket}",
        {"prefixes": paths},
    )
    if status not in (200, 201):
        raise RuntimeError(f"Storage delete failed ({status}): {body.decode()}")


def empty_storage_bucket() -> None:
    """Delete every file in the designs bucket without dropping the bucket."""
    bucket = get_supabase_bucket()
    print(f"Scanning storage bucket '{bucket}'...")
    paths = _collect_all_paths(bucket)
    if not paths:
        print("  Bucket already empty.")
        return
    print(f"  Found {len(paths)} file(s) — deleting...")
    # Supabase accepts up to 1000 prefixes per request
    batch_size = 1000
    for i in range(0, len(paths), batch_size):
        batch = paths[i : i + batch_size]
        _delete_objects(bucket, batch)
        for path in batch:
            print(f"  Deleted: {path}")
    print("  Bucket emptied.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Empty the SQL tables and storage bucket.")
    parser.add_argument("--backend-base-url", default=DEFAULT_BACKEND_BASE_URL)
    parser.add_argument("--backend-start-timeout", type=int, default=20)
    parser.add_argument("--no-auto-start-backend", action="store_true")
    parser.add_argument("--postgres-start-timeout", type=int, default=30)
    parser.add_argument("--no-auto-start-postgres", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    backend_base_url = args.backend_base_url.rstrip("/")

    print("=" * 60)
    print("WARNING: This will permanently erase all designs and")
    print("         assets from both the database and storage.")
    print("=" * 60)
    answer = input("Type YES to continue: ").strip()
    if answer != "YES":
        print("Aborted.")
        return

    if not check_postgres_running():
        if args.no_auto_start_postgres:
            print("FAILED: PostgreSQL is not reachable. Start it with: docker compose up -d postgres")
            raise SystemExit(1)
        print("PostgreSQL not running. Starting container...")
        try:
            start_postgres_container()
        except subprocess.CalledProcessError as error:
            print(f"FAILED: could not start postgres container: {error}")
            raise SystemExit(1)
        if not wait_for_postgres_ready(args.postgres_start_timeout):
            print(f"FAILED: PostgreSQL did not become ready within {args.postgres_start_timeout}s")
            raise SystemExit(1)
        print("PostgreSQL started and ready.")
    else:
        print("PostgreSQL reachable.")

    started_backend_process: subprocess.Popen | None = None
    if check_backend_health(backend_base_url):
        print(f"Backend reachable at {backend_base_url}")
    elif args.no_auto_start_backend:
        print(f"FAILED: backend is not reachable at {backend_base_url}")
        raise SystemExit(1)
    elif not is_local_backend_url(backend_base_url):
        print(f"FAILED: backend is not reachable at {backend_base_url}")
        print("Auto-start is only supported for localhost URLs.")
        raise SystemExit(1)
    else:
        print(f"Backend not running at {backend_base_url}. Starting local backend...")
        started_backend_process = start_local_backend_process(backend_base_url)
        if not wait_for_backend_ready(backend_base_url, args.backend_start_timeout):
            stop_backend_process(started_backend_process)
            print(f"FAILED: backend did not become healthy within {args.backend_start_timeout}s")
            raise SystemExit(1)
        print("Local backend started and healthy.")

    try:
        try:
            truncate_tables()
        except Exception as error:
            print(f"FAILED (SQL): {error}")
            raise SystemExit(1)

        try:
            empty_storage_bucket()
        except Exception as error:
            print(f"FAILED (storage): {error}")
            raise SystemExit(1)

        print("Done. Database and storage are clean.")
    finally:
        if started_backend_process is not None:
            print("Stopping auto-started backend...")
            stop_backend_process(started_backend_process)


if __name__ == "__main__":
    main()
