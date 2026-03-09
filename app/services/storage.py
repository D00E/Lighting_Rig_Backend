import os
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_SUPABASE_BUCKET = "designs"


def get_supabase_url() -> str:
    value = os.getenv("SUPABASE_URL", "").strip()
    if not value:
        raise RuntimeError("SUPABASE_URL is not configured")
    return value.rstrip("/")


def get_supabase_key() -> str:
    value = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not value:
        raise RuntimeError("SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY is not configured")
    return value


def get_supabase_bucket() -> str:
    return os.getenv("SUPABASE_BUCKET", DEFAULT_SUPABASE_BUCKET)


def upload_bytes(storage_path: str, content: bytes, content_type: str) -> dict:
    supabase_url = get_supabase_url()
    supabase_key = get_supabase_key()
    bucket = get_supabase_bucket()

    encoded_path = urllib.parse.quote(storage_path, safe="/")
    upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{encoded_path}"

    request = urllib.request.Request(
        upload_url,
        data=content,
        method="POST",
        headers={
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "x-upsert": "true",
            "Content-Type": content_type,
        },
    )

    try:
        with urllib.request.urlopen(request):
            pass
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8")
        raise RuntimeError(f"Supabase upload failed ({error.code}): {message}") from error

    return {
        "storage_bucket": bucket,
        "storage_path": storage_path,
        "content_type": content_type,
        "size_bytes": len(content),
    }
