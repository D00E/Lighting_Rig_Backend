"""GIF processing pipeline: converts GIF animations into RGB888 packet files.

This module drives the data-preparation stage of the pipeline:

1. Each GIF frame is resized to 16 × 16 pixels and saved as a BMP.
2. BMP pixel data is converted to RGB888 hex values (6-character RRGGBB format).
3. Hex values are concatenated and split into fixed-size packets, each with a
   CRC32 checksum header.
4. Packets are written to individual ``.txt`` files and then grouped into
   chunk sub-folders.
5. A ``*_meta.json`` file is produced alongside the packets.

The module can be run directly or called programmatically via
:func:`run_processing`.
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
    """Calculate a masked CRC32 checksum for a UTF-8 string.

    Args:
        data: The string to checksum.

    Returns:
        An unsigned 32-bit integer checksum.
    """
    return zlib.crc32(data.encode("utf-8")) & 0xFFFFFFFF


def generate_packet_header(packet_number: int, packet_data: str) -> str:
    """Build the fixed-width header for a single packet.

    The header format is::

        <5-digit packet number><8-digit CRC32 hex><3-digit length>@

    Args:
        packet_number: Zero-based index of the packet.
        packet_data: The raw hex-value string that will follow the header.

    Returns:
        The formatted header string.
    """
    checksum = calculate_crc32(packet_data)
    packet_length = len(packet_data)
    return f"{packet_number:05d}{checksum:08X}{packet_length:03d}@"


def create_packet(packet_number: int, packet_data: str, total_packets: int) -> str:
    """Assemble a complete packet string including header, data, and terminator.

    The packet is terminated with a single exclamation mark. Older behavior
    appended a ``"?"`` to the final packet; that terminator has been removed
    to avoid an extraneous character at the end of the output file.

    Args:
        packet_number: Zero-based index of the packet.
        packet_data: The hex-value payload string for this packet.
        total_packets: Total number of packets in the transmission.

    Returns:
        The fully assembled packet string.
    """
    return f"{generate_packet_header(packet_number, packet_data)}{packet_data}!"


def gif_to_bmp(input_gif: Path, output_folder: Path) -> list[Path]:
    """Extract and resize each frame of a GIF, saving them as BMP files.

    Args:
        input_gif: Path to the source GIF file.
                output_folder: Directory in which to write the BMP frame files.

    Returns:
        An ordered list of paths to the generated BMP files.
    """
    gif = Image.open(input_gif)
    gif_base_name = input_gif.stem
    bmp_paths: list[Path] = []

    for index, frame in enumerate(ImageSequence.Iterator(gif)):
        delay = frame.info.get("duration", 0)
        print(f"Frame {index}: Delay {delay} ms")
        resized_frame = frame.convert("RGB").resize(FRAME_SIZE, Image.Resampling.NEAREST)
        bmp_path = output_folder / f"{gif_base_name}_frame_{index:0{FRAME_FILE_DIGITS}d}.bmp"
        resized_frame.save(bmp_path, "BMP")
        bmp_paths.append(bmp_path)

    return bmp_paths


def bmp_to_hex_values(input_bmp: Path) -> list[str]:
    """Convert a BMP frame to a list of RGB888 hex strings.

    Each pixel is encoded as a six-character uppercase hex string in RRGGBB
    format (2 hex digits each for red, green, and blue).

    Args:
        input_bmp: Path to the BMP file to convert.

    Returns:
        A list of six-character hex strings, one per pixel, in row-major
        order.
    """
    bmp = Image.open(input_bmp).convert("RGB").resize(FRAME_SIZE, Image.Resampling.NEAREST)
    hex_values: list[str] = []
    for r, g, b in bmp.getdata():
        hex_values.append(f"{r:02X}{g:02X}{b:02X}")
    return hex_values


def save_packets_to_files(
    hex_values_list: list[list[str]],
    output_folder_path: Path,
    gif_base_name: str,
    packet_size: int,
    master_file_path: Path,
) -> int:
    """Serialise RGB565 hex values into numbered packet files.

    All per-frame hex value lists are flattened into a single sequence, then
    split into fixed-size packets.  Each packet is written to its own
    ``*_packet_NNNNN.txt`` file, and the raw hex data is also appended to a
    master ``*_processed.txt`` file.

    Args:
        hex_values_list: A list where each element is the list of RGB888 hex
            strings for one GIF frame.
        output_folder_path: Directory in which to write the packet files.
        gif_base_name: Base name of the source GIF (used in file naming).
        packet_size: Number of hex values per packet.
        master_file_path: Path of the master output file that aggregates all
            raw hex data.

    Returns:
        The total number of packets written.
    """
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
            master_file.write(packet)
        print(f"Saved packet {packet_index + 1} to: {packet_file_path}")
        packet_index += 1

    return total_packets


def remove_remaining_files(output_folder_path: Path, gif_base_name: str) -> None:
    """Delete the intermediate BMP frame files after packet generation.

    Args:
        output_folder_path: Directory containing the BMP files to remove.
        gif_base_name: Base name of the GIF whose BMP files should be deleted.
    """
    bmp_pattern = re.compile(fr"{re.escape(gif_base_name)}_frame_\d{{{FRAME_FILE_DIGITS}}}\.bmp")
    for file_path in output_folder_path.iterdir():
        if file_path.is_file() and bmp_pattern.match(file_path.name):
            file_path.unlink()
            print(f"Removed .bmp file: {file_path}")


def write_metadata(output_folder_path: Path, gif_base_name: str, num_frames: int, total_packets: int) -> Path:
    """Write a JSON metadata file summarising the processed GIF.

    Args:
        output_folder_path: Directory in which to write the metadata file.
        gif_base_name: Base name of the source GIF.
        num_frames: Total number of frames extracted from the GIF.
        total_packets: Total number of packets generated.

    Returns:
        Path to the written ``*_meta.json`` file.
    """
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
    return meta_path


def process_gif(gif_path: Path, output_folder_path: Path, packet_size: int) -> Path:
    """Run the full processing pipeline for a single GIF file.

    Orchestrates frame extraction, hex conversion, packet generation, BMP
    clean-up, and metadata writing for one GIF.

    Args:
        gif_path: Path to the source GIF file.
        output_folder_path: Directory in which to write all outputs.
        packet_size: Number of hex values per packet.

    Returns:
        Path to the generated ``*_meta.json`` metadata file.
    """
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
    metadata_path = write_metadata(output_folder_path, gif_base_name, len(hex_values_list), total_packets)
    remove_remaining_files(output_folder_path, gif_base_name)
    return metadata_path


def extract_packet_number(filename: str) -> int:
    """Extract the numeric index from a packet filename.

    Args:
        filename: The filename string, e.g. ``"anim_packet_00003.txt"``.

    Returns:
        The extracted integer, or ``-1`` if no number is found.
    """
    match = re.search(r"(\d+)", filename)
    if match:
        return int(match.group(1))
    return -1


def group_packets_into_chunks(source_folder: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
    """Organise packet files into numbered ``chunk<N>`` sub-folders.

    Packet files are sorted by their embedded packet number and then moved into
    sub-folders of ``chunk_size`` files each.  This is useful for reducing the
    number of files in a single directory for large GIFs.

    Args:
        source_folder: Directory containing the ``*_packet_*.txt`` files.
        chunk_size: Maximum number of packet files per chunk folder.
            Defaults to :data:`DEFAULT_CHUNK_SIZE`.
    """
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
    """Collect GIF files from a single file path or a directory.

    Preview GIFs (files ending in ``_16x16.gif``) are excluded automatically.

    Args:
        input_path: Path to either a single GIF file or a directory of GIFs.

    Returns:
        A sorted list of GIF file paths.  Returns an empty list if the input
        path is neither a valid GIF nor a directory.
    """
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


def run_processing(
    input_path: Path,
    output_path: Path,
    packet_size: int = DEFAULT_PACKET_SIZE,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[Path]:
    """Process one or more GIF files and return paths to the generated metadata.

    This is the primary entry point for programmatic use of the pipeline.
    It processes every GIF found at ``input_path``, then groups the resulting
    packet files into chunk sub-folders.

    Args:
        input_path: Path to a single GIF file or a directory containing GIFs.
        output_path: Directory in which to write all processed outputs.
            Created automatically if it does not exist.
        packet_size: Number of RGB888 hex values per packet.
            Defaults to :data:`DEFAULT_PACKET_SIZE`.
        chunk_size: Number of packet files per chunk sub-folder.
            Defaults to :data:`DEFAULT_CHUNK_SIZE`.

    Raises:
        FileNotFoundError: If no valid GIF files are found at ``input_path``.

    Returns:
        A list of paths to the generated ``*_meta.json`` metadata files, one
        per processed GIF.
    """
    output_path.mkdir(parents=True, exist_ok=True)
    gif_files = iter_gif_files(input_path)
    if not gif_files:
        raise FileNotFoundError(f"No valid GIF files found at: {input_path}")

    metadata_paths: list[Path] = []
    for gif_path in gif_files:
        metadata_paths.append(process_gif(gif_path, output_path, packet_size))

    group_packets_into_chunks(output_path, chunk_size)
    return metadata_paths


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
    run_processing(input_path, output_path, args.packet_size, args.chunk_size)


if __name__ == "__main__":
    main()

