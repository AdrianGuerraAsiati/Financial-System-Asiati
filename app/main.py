from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.motores.cartera_ocs.api import router as cartera_router


WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(
    title="Plataforma Financiera ASIATI",
    version="0.1.0",
)

app.include_router(cartera_router)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/", include_in_schema=False)
def inicio() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
