# import_design Script

`scripts/import_design.py` is the end-to-end command-line tool for ingesting a
GIF animation into the Lighting Rig Backend. It orchestrates three stages:

| Stage | Description |
|-------|-------------|
| **1 – Process** | Calls the packet processing pipeline to convert the GIF into RGB565 packet files, a 16 × 16 preview GIF, and a JSON metadata file. |
| **2 – Upload** | Sends the preview GIF, encoded payload, and metadata file to the backend storage endpoint. |
| **3 – Register** | POSTs a design record to `/designs`, then links each uploaded file as a design asset via `/design-assets`. |

## Usage

```bash
python scripts/import_design.py --input path/to/animation.gif
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--input` | *(required)* | Path to a GIF file or a folder of GIFs. |
| `--output` | Input folder | Output folder for processed files. |
| `--backend-base-url` | `http://127.0.0.1:8000` | Backend base URL (overridden by `BACKEND_BASE_URL` env var). |
| `--packet-size` | `120` | Number of RGB565 hex values per packet. |
| `--chunk-size` | `100` | Number of packet files per chunk sub-folder. |
| `--design-type` | `gif` | Design type label written to the database. |
| `--callsign` | *(auto-generated)* | Fixed six-character callsign. |
| `--creator` | *(from metadata)* | Creator name override. |
| `--description` | *(from metadata)* | Description override. |

## Environment Variables

`BACKEND_BASE_URL` – overrides the default backend URL without needing to pass
`--backend-base-url` on every invocation.

## API Reference

::: scripts.import_design
