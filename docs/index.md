# Lighting Rig Backend

Backend service for managing, processing, and distributing GIF-based lighting
rig designs. Built on **FastAPI** and **PostgreSQL**, with **Supabase** for
binary asset storage.

Theme credit: built with **Material for MkDocs** by squidfunk
(https://github.com/squidfunk/mkdocs-material).

---

## Architecture

```
GIF file
  └─► process_packets  – convert to RGB565 packets + preview GIF
        └─► import_design  – upload assets to Supabase, register in database
              └─► FastAPI     – REST API consumed by the lighting rig controller
```

The backend is split into three layers:

| Layer | Location | Purpose |
|-------|----------|---------|
| **API** | `app/` | FastAPI routes, schemas, and DB sessions |
| **Processing** | `archive/process_packets.py` | GIF → RGB565 packet pipeline |
| **Import** | `scripts/import_design.py` | End-to-end CLI ingestion tool |
| **Utilities** | `modules/comparison.py` | Text comparison helpers (used in tests) |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the database

```bash
docker compose up -d
```

### 3. Run the API

```bash
uvicorn app.main:app --reload
```

The interactive API docs are available at `http://127.0.0.1:8000/docs`.

### 4. Import a design

```bash
python scripts/import_design.py --input path/to/animation.gif
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *(set in environment)* | PostgreSQL connection string |
| `BACKEND_BASE_URL` | `http://127.0.0.1:8000` | Base URL for the API |
| `SUPABASE_URL` | *(required for uploads)* | Supabase project URL |
| `SUPABASE_AUTH` | *(required for uploads)* | Supabase service-role credentials from environment |
| `SUPABASE_BUCKET` | `designs` | Supabase storage bucket name |

---

## Project Layout

```
app/
  main.py            – FastAPI application entry point
  db.py              – database session and connection setup
  routes/            – API route handlers
  schemas/           – Pydantic request/response models
  services/          – storage service abstraction
archive/
  process_packets.py – GIF-to-packet processing pipeline
modules/
  comparison.py      – text file comparison utilities
scripts/
  import_design.py   – end-to-end import CLI tool
migrations/          – SQL migration files
tests/               – pytest test suite
```
