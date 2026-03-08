""" use

/usr/bin/python3 archive/process_packets.py \
  --input tests/payload_samples/test_gif/test.gif \
  --output tests/payload_samples/test_gif \
  --packet-size 120 \
  --chunk-size 100
"""

import argparse
import json
import re
import shutil
import zlib
from pathlib import Path

from PIL import Image, ImageSequence


FRAME_SIZE = (16, 16)
PACKET_FILE_DIGITS = 5
FRAME_FILE_DIGITS = 3
DEFAULT_PACKET_SIZE = 120
DEFAULT_CHUNK_SIZE = 100


def calculate_crc32(data: str) -> int:
    return zlib.crc32(data.encode("utf-8")) & 0xFFFFFFFF


def generate_packet_header(packet_number: int, packet_data: str) -> str:
    checksum = calculate_crc32(packet_data)
    packet_length = len(packet_data)
    return f"{packet_number:05d}{checksum:08X}{packet_length:03d}@"


def create_packet(packet_number: int, packet_data: str, total_packets: int) -> str:
    transmission_end = "?" if packet_number == total_packets - 1 else ""
    return f"{generate_packet_header(packet_number, packet_data)}{packet_data}!{transmission_end}"


def gif_to_bmp(input_gif: Path, output_folder: Path) -> list[Path]:
    gif = Image.open(input_gif)
    gif_base_name = input_gif.stem
    resized_frames: list[Image.Image] = []
    durations: list[int] = []
    bmp_paths: list[Path] = []

    for index, frame in enumerate(ImageSequence.Iterator(gif)):
        delay = frame.info.get("duration", 0)
        print(f"Frame {index}: Delay {delay} ms")
        resized_frame = frame.convert("RGB").resize(FRAME_SIZE)
        bmp_path = output_folder / f"{gif_base_name}_frame_{index:0{FRAME_FILE_DIGITS}d}.bmp"
        resized_frame.save(bmp_path, "BMP")
        bmp_paths.append(bmp_path)
        resized_frames.append(resized_frame)
        durations.append(delay)

    if resized_frames:
        small_gif_path = output_folder / f"{gif_base_name}_16x16.gif"
        first_frame, *other_frames = resized_frames
        first_frame.save(
            small_gif_path,
            save_all=True,
            append_images=other_frames,
            loop=0,
            duration=durations or None,
            disposal=2,
        )
        print(f"Saved 16x16 GIF preview to: {small_gif_path}")

    return bmp_paths


def bmp_to_hex_values(input_bmp: Path) -> list[str]:
    bmp = Image.open(input_bmp).convert("RGB").resize(FRAME_SIZE)
    hex_values: list[str] = []
    for r, g, b in bmp.getdata():
        r5 = int((r * 31) / 255)
        g6 = int((g * 63) / 255)
        b5 = int((b * 31) / 255)
        rgb565 = (r5 << 11) | (g6 << 5) | b5
        hex_values.append(f"{rgb565:04X}")
    return hex_values


def save_packets_to_files(
    hex_values_list: list[list[str]],
    output_folder_path: Path,
    gif_base_name: str,
    packet_size: int,
    master_file_path: Path,
) -> int:
    output_folder_path.mkdir(parents=True, exist_ok=True)
    all_hex_values = [hex_value for hex_values in hex_values_list for hex_value in hex_values]
    total_packets = len(all_hex_values) // packet_size + (1 if len(all_hex_values) % packet_size > 0 else 0)
    master_file_path.write_text("")

    packet_index = 0
    for i in range(0, len(all_hex_values), packet_size):
        packet_data = "".join(all_hex_values[i : i + packet_size])
        packet = create_packet(packet_index, packet_data, total_packets)
        packet_file_path = output_folder_path / f"{gif_base_name}_packet_{packet_index:0{PACKET_FILE_DIGITS}d}.txt"
        packet_file_path.write_text(packet)
        with master_file_path.open("a") as master_file:
            master_file.write(packet_data)
        print(f"Saved packet {packet_index + 1} to: {packet_file_path}")
        packet_index += 1

    return total_packets


def remove_remaining_files(output_folder_path: Path, gif_base_name: str) -> None:
    bmp_pattern = re.compile(fr"{re.escape(gif_base_name)}_frame_\d{{{FRAME_FILE_DIGITS}}}\.bmp")
    for file_path in output_folder_path.iterdir():
        if file_path.is_file() and bmp_pattern.match(file_path.name):
            file_path.unlink()
            print(f"Removed .bmp file: {file_path}")


def write_metadata(output_folder_path: Path, gif_base_name: str, num_frames: int, total_packets: int) -> None:
    metadata = {
        "gif_name": gif_base_name,
        "num_frames": num_frames,
        "num_packets": total_packets,
        "creator": "",
        "description": "",
    }
    meta_path = output_folder_path / f"{gif_base_name}_meta.json"
    with meta_path.open("w") as file_handle:
        json.dump(metadata, file_handle, indent=2)
    print(f"Wrote metadata to: {meta_path}")


def process_gif(gif_path: Path, output_folder_path: Path, packet_size: int) -> None:
    gif_base_name = gif_path.stem
    bmp_files = gif_to_bmp(gif_path, output_folder_path)
    frame_index_pattern = re.compile(r"_frame_(\d{3})\.bmp")
    sorted_bmps = sorted(
        bmp_files,
        key=lambda path: int(frame_index_pattern.search(path.name).group(1)) if frame_index_pattern.search(path.name) else 0,
    )

    hex_values_list: list[list[str]] = [bmp_to_hex_values(bmp_file) for bmp_file in sorted_bmps]
    master_file_path = output_folder_path / f"{gif_base_name}_processed.txt"
    total_packets = save_packets_to_files(hex_values_list, output_folder_path, gif_base_name, packet_size, master_file_path)
    total_packets -= 1
    write_metadata(output_folder_path, gif_base_name, len(hex_values_list), total_packets)
    remove_remaining_files(output_folder_path, gif_base_name)


def extract_packet_number(filename: str) -> int:
    match = re.search(r"(\d+)", filename)
    if match:
        return int(match.group(1))
    return -1


def group_packets_into_chunks(source_folder: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
    files = [
        path
        for path in source_folder.iterdir()
        if path.is_file() and "_packet_" in path.name
    ]
    files.sort(key=lambda path: extract_packet_number(path.name))

    total_files = len(files)
    if total_files == 0:
        return

    total_chunks = (total_files // chunk_size) + (1 if total_files % chunk_size > 0 else 0)
    for chunk_num in range(total_chunks):
        chunk_folder = source_folder / f"chunk{chunk_num + 1}"
        chunk_folder.mkdir(exist_ok=True)
        start_index = chunk_num * chunk_size
        end_index = min((chunk_num + 1) * chunk_size, total_files)
        for file_path in files[start_index:end_index]:
            destination_path = chunk_folder / file_path.name
            shutil.move(str(file_path), str(destination_path))
        print(f"Moved {end_index - start_index} files to {chunk_folder}")


def iter_gif_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.lower() == ".gif" and not input_path.name.endswith("_16x16.gif") else []

    if input_path.is_dir():
        return sorted(
            [
                path
                for path in input_path.iterdir()
                if path.is_file() and path.suffix.lower() == ".gif" and not path.name.endswith("_16x16.gif")
            ]
        )

    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process GIF files into RGB565 packet files.")
    parser.add_argument("--input", required=True, help="Path to a GIF file or a directory of GIFs.")
    parser.add_argument("--output", required=True, help="Output directory for packet and metadata files.")
    parser.add_argument("--packet-size", type=int, default=DEFAULT_PACKET_SIZE, help="Number of values per packet.")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Number of packet files per chunk folder.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    gif_files = iter_gif_files(input_path)
    if not gif_files:
        raise FileNotFoundError(f"No valid GIF files found at: {input_path}")

    for gif_path in gif_files:
        process_gif(gif_path, output_path, args.packet_size)

    group_packets_into_chunks(output_path, args.chunk_size)


if __name__ == "__main__":
    main()

