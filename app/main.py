from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.auth.api import router as auth_router
from app.core.hallazgos.api import router as hallazgos_router
from app.core.supervision.api import router as supervision_router
from app.core.usuarios.api import router as usuarios_router
from app.motores.cartera_ocs.api import router as cartera_router
from app.motores.conciliacion_wallets.wiilog.api import router as wiilog_wallet_router


WEB_DIR = Path(__file__).parent / "web"
API_V1 = "/api/v1"

app = FastAPI(
    title="Plataforma Financiera ASIATI",
    version="0.1.0",
)

app.include_router(auth_router, prefix=API_V1)
app.include_router(usuarios_router, prefix=API_V1)
app.include_router(supervision_router, prefix=API_V1)
app.include_router(hallazgos_router, prefix=API_V1)
# Sin autenticación hasta la pantalla de login: docs/decisiones/0004.
app.include_router(cartera_router)
app.include_router(wiilog_wallet_router)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/", include_in_schema=False)
def inicio() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}
