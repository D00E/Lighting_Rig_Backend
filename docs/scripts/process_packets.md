# process_packets Script

`archive/process_packets.py` drives the data-preparation stage of the pipeline.
It converts raw GIF animations into the binary-safe RGB565 packet format
expected by the lighting rig hardware.

## Pipeline Overview

```
GIF file
  └─► gif_to_bmp()          – extract frames, resize to 16 × 16, save as BMP
        └─► bmp_to_hex_values()  – convert each BMP to a list of RGB565 hex strings
              └─► save_packets_to_files()  – split hex values into fixed-size packets
                    ├─ writes  *_packet_NNNNN.txt  (one per packet)
                    ├─ writes  *_processed.txt     (master concatenated file)
                    └─ writes  *_meta.json         (frame/packet counts)
              └─► group_packets_into_chunks()  – move packets into chunk sub-folders
```

## Packet Format

Each packet file contains a single line structured as:

```
<5-digit number><8-digit CRC32 hex><3-digit length>@<hex data>![?]
```

- The `?` terminator appears only on the final packet of a transmission.
- CRC32 is calculated over the raw hex data string (before the header is prepended).

## Usage

```bash
python archive/process_packets.py --input path/to/animation.gif --output path/to/output/
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--input` | *(required)* | Path to a GIF file or a directory of GIFs. |
| `--output` | *(required)* | Output directory for packet and metadata files. |
| `--packet-size` | `120` | Number of RGB565 hex values per packet. |
| `--chunk-size` | `100` | Number of packet files per chunk sub-folder. |

## Constants

| Name | Value | Description |
|------|-------|-------------|
| `FRAME_SIZE` | `(16, 16)` | Target pixel dimensions for each frame. |
| `DEFAULT_PACKET_SIZE` | `120` | Default number of hex values per packet. |
| `DEFAULT_CHUNK_SIZE` | `100` | Default packet files per chunk folder. |
| `PREVIEW_SCALE` | `16` | Scale factor for the sharp root-level preview GIF. |

## API Reference

::: archive.process_packets
