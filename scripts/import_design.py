import argparse
import json
import mimetypes
import os
import secrets
import string
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from archive.process_packets import DEFAULT_CHUNK_SIZE, DEFAULT_PACKET_SIZE, run_processing


DEFAULT_BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
CALLSIGN_LENGTH = 6
CALLSIGN_ALPHABET = string.ascii_uppercase + string.digits


def generate_callsign() -> str:
    return "".join(secrets.choice(CALLSIGN_ALPHABET) for _ in range(CALLSIGN_LENGTH))


def load_metadata(metadata_path: Path) -> dict:
    with metadata_path.open("r") as file_handle:
        return json.load(file_handle)


def build_payload(
    metadata: dict,
    design_type: str,
    creator: str | None,
    description: str | None,
    callsign: str | None,
) -> dict:
    payload = {
        "design_type": design_type,
        "gif_name": metadata["gif_name"],
        "callsign": callsign or generate_callsign(),
        "num_frames": int(metadata.get("num_frames", 0)),
        "num_packets": int(metadata.get("num_packets", 0)),
        "creator": creator if creator is not None else metadata.get("creator"),
        "description": description if description is not None else metadata.get("description"),
    }
    return payload


def post_json(url: str, payload: dict) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode("utf-8")
            return response.status, response_body
    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8")
        return error.code, response_body


def post_design(api_url: str, payload: dict) -> tuple[int, str]:
    return post_json(api_url, payload)


def upload_file_via_backend(
    backend_base_url: str,
    callsign: str,
    filename: str,
    file_path: Path,
    content_type: str,
) -> tuple[int, str]:
    query = urllib.parse.urlencode(
        {
            "callsign": callsign,
            "filename": filename,
            "content_type": content_type,
        }
    )
    upload_url = f"{backend_base_url.rstrip('/')}/storage/upload?{query}"
    body = file_path.read_bytes()
    request = urllib.request.Request(
        upload_url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/octet-stream"},
    )

    try:
        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode("utf-8")
            return response.status, response_body
    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8")
        return error.code, response_body


def post_design_asset(api_url: str, payload: dict) -> tuple[int, str]:
    return post_json(api_url, payload)


def create_design_record(designs_url: str, payload: dict) -> tuple[int, str, dict]:
    status, response = post_design(designs_url, payload)
    return status, response, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process design input and ingest metadata via backend API.")
    parser.add_argument("--input", required=True, help="Path to a GIF file or a folder containing GIF files.")
    parser.add_argument("--output", help="Output folder for processed files. Defaults to input folder.")
    parser.add_argument("--backend-base-url", default=DEFAULT_BACKEND_BASE_URL, help="Backend base URL.")
    parser.add_argument("--packet-size", type=int, default=DEFAULT_PACKET_SIZE)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--design-type", default="gif")
    parser.add_argument("--callsign", help="Optional fixed callsign. If omitted, one is generated.")
    parser.add_argument("--creator", help="Optional creator override.")
    parser.add_argument("--description", help="Optional description override.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve() if args.output else (
        input_path.parent if input_path.is_file() else input_path
    )

    backend_base_url = args.backend_base_url.rstrip("/")
    designs_url = f"{backend_base_url}/designs"
    design_assets_url = f"{backend_base_url}/design-assets"

    print(f"[1/3] Processing input: {input_path}")
    metadata_paths = run_processing(
        input_path=input_path,
        output_path=output_path,
        packet_size=args.packet_size,
        chunk_size=args.chunk_size,
    )

    print(f"[2/4] Found {len(metadata_paths)} metadata file(s)")
    for metadata_path in metadata_paths:
        metadata = load_metadata(metadata_path)
        payload = build_payload(
            metadata=metadata,
            design_type=args.design_type,
            creator=args.creator,
            description=args.description,
            callsign=args.callsign,
        )

        payload["description"] = payload.get("description") or ""
        payload["description"] = (
            f"{payload['description']} | output_path={output_path}" if payload["description"] else f"output_path={output_path}"
        )

        gif_name = payload["gif_name"]
        callsign = payload["callsign"]
        preview_path = metadata_path.parent / f"{gif_name}_16x16.gif"
        payload_txt_path = metadata_path.parent / f"{gif_name}_processed.txt"

        if not preview_path.exists():
            print(f"FAILED: missing preview file at {preview_path}")
            raise SystemExit(1)

        if not payload_txt_path.exists():
            print(f"FAILED: missing payload file at {payload_txt_path}")
            raise SystemExit(1)

        print(f"[3/4] Uploading assets for '{gif_name}'...")
        uploads = [
            ("preview_gif", "preview.gif", preview_path, "image/gif"),
            ("encoded_payload", "payload.txt", payload_txt_path, "text/plain"),
            ("metadata_file", "metadata.json", metadata_path, "application/json"),
        ]

        uploaded_assets: list[dict] = []
        for asset_type, remote_name, local_path, forced_content_type in uploads:
            content_type = forced_content_type or (mimetypes.guess_type(local_path.name)[0] or "application/octet-stream")
            status, response = upload_file_via_backend(
                backend_base_url=backend_base_url,
                callsign=callsign,
                filename=remote_name,
                file_path=local_path,
                content_type=content_type,
            )
            if status >= 400:
                print(f"FAILED upload ({status}) {asset_type}: {response}")
                raise SystemExit(1)

            uploaded = json.loads(response)
            uploaded["asset_type"] = asset_type
            uploaded_assets.append(uploaded)

        print(f"[4/4] Posting design '{payload['gif_name']}' with callsign {payload['callsign']}...")
        status, response, used_payload = create_design_record(designs_url, payload)

        if status >= 400:
            if "duplicate key" in response.lower() or "unique" in response.lower():
                print("FAILED: callsign collision after upload. Re-run or pass --callsign.")
            print(f"FAILED ({status}): {response}")
            raise SystemExit(1)

        created_design = json.loads(response)
        design_id = created_design["id"]

        for uploaded in uploaded_assets:
            asset_payload = {
                "design_id": design_id,
                "asset_type": uploaded["asset_type"],
                "storage_bucket": uploaded["storage_bucket"],
                "storage_path": uploaded["storage_path"],
                "content_type": uploaded.get("content_type"),
                "size_bytes": uploaded.get("size_bytes"),
            }
            asset_status, asset_response = post_design_asset(design_assets_url, asset_payload)
            if asset_status >= 400:
                print(f"FAILED asset save ({asset_status}): {asset_response}")
                raise SystemExit(1)

        print(f"SUCCESS ({status}): {response}")
        print(f"Stored output path: {output_path}")
        print(f"Final callsign used: {used_payload['callsign']}")


if __name__ == "__main__":
    main()
