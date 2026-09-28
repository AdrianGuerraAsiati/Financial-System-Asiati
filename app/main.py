from fastapi import FastAPI

from app.motores.cartera_ocs.api import router as cartera_router


app = FastAPI(
    title="Plataforma Financiera ASIATI",
    version="0.1.0",
)

app.include_router(cartera_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
