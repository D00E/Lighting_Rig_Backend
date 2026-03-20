# Embedded lighting rig, SQL and Data Processing Backend

## Documentation (GitHub Pages)

- Docs source: `docs/` (MkDocs)
- Live docs URL : `https://d00e.github.io/Lighting_Rig_Backend/`

This repository includes a GitHub Actions workflow at
`.github/workflows/deploy-docs.yml` that builds and deploys docs on every push
to `master`.

One-time GitHub setup may still be required:

1. Open repository settings on GitHub.
2. Go to **Pages**.
3. Under **Build and deployment**, set **Source** to **GitHub Actions**.

## FastAPI Designs API

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run backend
```bash
uvicorn app.main:app --reload
```

### Test POST /designs
```bash
curl -X POST http://127.0.0.1:8000/designs \
	-H "Content-Type: application/json" \
	-d '{
		"design_type": "gif",
		"gif_name": "test",
		"callsign": "ABC123",
		"num_frames": 10,
		"num_packets": 21,
		"creator": "derp",
		"description": "something"
	}'
```

### Test GET /designs
```bash
curl http://127.0.0.1:8000/designs
```

### Import design via processing pipeline
```bash
python scripts/import_design.py --input ./tests/payload_samples/test_gif/test.gif
```

Optional explicit output/API flags:
```bash
python scripts/import_design.py \
	--input ./tests/payload_samples/test_gif \
	--output ./tests/payload_samples/test_gif \
	--backend-base-url http://127.0.0.1:8000
```

### Supabase storage environment
Required for backend storage uploads:

- `SUPABASE_URL`
- Supabase service-role credentials via your local environment
- `SUPABASE_BUCKET=designs`

Optional helper env vars:

- `BACKEND_BASE_URL=http://127.0.0.1:8000`
- `DATABASE_URL` (if not using the local default)

### Apply design assets migration
```bash
docker exec -i lighting_postgres psql -U lighting_user -d lighting_dev < migrations/004_create_design_assets.sql
```

### End-to-end one command
```bash
python scripts/import_design.py --input ./tests/payload_samples/BobRoss.gif
```

This command processes the GIF, uploads `preview.gif`, `payload.txt`, and `metadata.json` to Supabase storage under `<callsign>/...`, then creates records in `designs` and `design_assets` through the backend API.

### DATABASE_URL
The app reads `DATABASE_URL` from environment variables.
If not set, it defaults to:

`<set in environment>`

### Existing Docker volume note
`/docker-entrypoint-initdb.d` SQL files run only on first initialisation of the Postgres data volume.
If your volume already contains an older schema, either:

1. Reset volume and recreate containers.
2. Or run the migration manually:

```bash
docker exec -i lighting_postgres psql -U lighting_user -d lighting_dev < migrations/003_create_designs.sql
```