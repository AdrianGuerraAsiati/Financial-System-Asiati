from __future__ import annotations

import os
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.session import obtener_session

from .service import registrar_cambio


router = APIRouter(
    prefix="/integrations/google-sheets",
    tags=["integrations"],
)


class CambioGoogleSheets(BaseModel):
    modulo: Literal["cartera", "compras"]
    empresa_id: int = Field(gt=0)
    spreadsheet_id: str = Field(min_length=1, max_length=255)
    hoja: str | None = Field(default=None, max_length=255)
    rango: str | None = Field(default=None, max_length=255)
    tipo_evento: str | None = Field(default=None, max_length=64)


def _validar_secreto(
    x_asiati_sheet_secret: str | None = Header(
        default=None,
        alias="X-ASIATI-Sheet-Secret",
    ),
) -> None:
    esperado = os.getenv("GOOGLE_SHEETS_CHANGE_SECRET", "")
    if not esperado:
        raise HTTPException(
            status_code=503,
            detail="El webhook de Google Sheets no está configurado.",
        )
    recibido = x_asiati_sheet_secret or ""
    if not secrets.compare_digest(recibido, esperado):
        raise HTTPException(status_code=401, detail="Webhook no autorizado.")


def _configuracion_esperada(modulo: str) -> tuple[int, str]:
    prefijo = "CARTERA_SHEETS" if modulo == "cartera" else "COMPRAS_SHEETS"
    variable_empresa = f"{prefijo}_EMPRESA_ID"
    variable_spreadsheet = f"{prefijo}_SPREADSHEET_ID"
    empresa_cruda = os.getenv(variable_empresa, "").strip()
    spreadsheet_id = os.getenv(variable_spreadsheet, "").strip()

    faltantes = [
        nombre
        for nombre, valor in (
            (variable_empresa, empresa_cruda),
            (variable_spreadsheet, spreadsheet_id),
        )
        if not valor
    ]
    if faltantes:
        raise HTTPException(
            status_code=503,
            detail="Falta configurar: " + ", ".join(faltantes),
        )

    try:
        empresa_id = int(empresa_cruda)
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"{variable_empresa} debe ser entero.",
        ) from exc

    return empresa_id, spreadsheet_id


@router.post("/changed", status_code=202)
def google_sheet_changed(
    cambio: CambioGoogleSheets,
    _secreto: None = Depends(_validar_secreto),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    empresa_esperada, spreadsheet_esperado = _configuracion_esperada(
        cambio.modulo
    )
    if cambio.empresa_id != empresa_esperada:
        raise HTTPException(
            status_code=409,
            detail="La empresa no corresponde al módulo configurado.",
        )
    if cambio.spreadsheet_id != spreadsheet_esperado:
        raise HTTPException(
            status_code=409,
            detail="El spreadsheet no corresponde al módulo configurado.",
        )

    estado = registrar_cambio(
        session,
        empresa_id=cambio.empresa_id,
        modulo=cambio.modulo,
    )
    session.commit()

    return {
        "aceptado": True,
        "modulo": cambio.modulo,
        "empresa_id": cambio.empresa_id,
        "estado": estado.estado,
        "eventos_acumulados": estado.event_count,
        "nota": (
            "El cambio quedó pendiente. La lectura de Google se ejecuta una sola vez "
            "después del período de estabilización."
        ),
    }
