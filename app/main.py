from fastapi import FastAPI
from dotenv import load_dotenv

from app.routes.design_assets import router as design_assets_router
from app.routes.designs import router as designs_router
from app.routes.storage import router as storage_router


load_dotenv()

app = FastAPI(title="Lighting Rig Backend")
app.include_router(designs_router)
app.include_router(design_assets_router)
app.include_router(storage_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
