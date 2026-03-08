from fastapi import FastAPI

from app.routes.designs import router as designs_router


app = FastAPI(title="Lighting Rig Backend")
app.include_router(designs_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
