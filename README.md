# Embedded lighting rig, SQL and Data Processing Backend

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
	--api-url http://127.0.0.1:8000/designs
```

### DATABASE_URL
The app reads `DATABASE_URL` from environment variables.
If not set, it defaults to:

`postgresql://lighting_user:lighting_password@localhost:5433/lighting_dev`

### Existing Docker volume note
`/docker-entrypoint-initdb.d` SQL files run only on first initialisation of the Postgres data volume.
If your volume already contains an older schema, either:

1. Reset volume and recreate containers.
2. Or run the migration manually:

```bash
docker exec -i lighting_postgres psql -U lighting_user -d lighting_dev < migrations/003_create_designs.sql
```