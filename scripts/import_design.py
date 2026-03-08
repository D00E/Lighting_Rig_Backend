import argparse
import json
import secrets
import string
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from archive.process_packets import DEFAULT_CHUNK_SIZE, DEFAULT_PACKET_SIZE, run_processing


DEFAULT_API_URL = "http://127.0.0.1:8000/designs"
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


def post_design(api_url: str, payload: dict) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        api_url,
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


def send_with_callsign_retry(api_url: str, payload: dict, retries: int = 5) -> tuple[int, str, dict]:
    for _ in range(retries):
        status, response = post_design(api_url, payload)
        if status < 400:
            return status, response, payload

        is_unique_error = "duplicate key" in response.lower() or "unique" in response.lower()
        if not is_unique_error:
            return status, response, payload

        payload["callsign"] = generate_callsign()

    return status, response, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process design input and ingest metadata via backend API.")
    parser.add_argument("--input", required=True, help="Path to a GIF file or a folder containing GIF files.")
    parser.add_argument("--output", help="Output folder for processed files. Defaults to input folder.")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Backend endpoint for POST /designs.")
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

    print(f"[1/3] Processing input: {input_path}")
    metadata_paths = run_processing(
        input_path=input_path,
        output_path=output_path,
        packet_size=args.packet_size,
        chunk_size=args.chunk_size,
    )

    print(f"[2/3] Found {len(metadata_paths)} metadata file(s)")
    for metadata_path in metadata_paths:
        metadata = load_metadata(metadata_path)
        payload = build_payload(
            metadata=metadata,
            design_type=args.design_type,
            creator=args.creator,
            description=args.description,
            callsign=args.callsign,
        )

        payload["description"] = (
            f"{payload['description']} | output_path={output_path}" if payload.get("description") else f"output_path={output_path}"
        )

        print(f"[3/3] Posting design '{payload['gif_name']}' with callsign {payload['callsign']}...")
        status, response, used_payload = send_with_callsign_retry(args.api_url, payload)

        if status >= 400:
            print(f"FAILED ({status}): {response}")
            raise SystemExit(1)

        print(f"SUCCESS ({status}): {response}")
        print(f"Stored output path: {output_path}")
        print(f"Final callsign used: {used_payload['callsign']}")


if __name__ == "__main__":
    main()
