from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from .google_sheets import (
    ClienteGoogleSheetsApi,
    ClienteValoresGoogleSheets,
    ConfiguracionGoogleSheetsIncompletaError,
    analizar_rango_cartera,
)
from .importacion import normalizar_fila_cartera
from .mora import normalizar_fila_mora
from .proyeccion import normalizar_fila_proyeccion
from .snapshot_model import CarteraSnapshot, CarteraSnapshotFila


RANGOS_CARTERA_ENV = {
    "OPERACIONES": "CARTERA_SHEETS_RANGE",
    "MORA": "CARTERA_SHEETS_MORA_RANGE",
    "PROYECCION": "CARTERA_SHEETS_PROYECCION_RANGE",
}


class LecturaSnapshotCarteraError(RuntimeError):
    pass


@dataclass(frozen=True)
class FilaSnapshotCartera:
    tipo: str
    fila_fuente: int
    crudo: Mapping[str, Any]
    normalizado: Mapping[str, Any]


@dataclass(frozen=True)
class SnapshotFuenteCartera:
    cargado_en: datetime
    spreadsheet_id: str
    rangos: Mapping[str, str]
    diagnosticos: tuple[Mapping[str, Any], ...]
    filas: tuple[FilaSnapshotCartera, ...]

    def conteo(self, tipo: str) -> int:
        return sum(
            1
            for fila in self.filas
            if fila.tipo == tipo and bool(fila.normalizado)
        )


def _json_seguro(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return format(valor, "f")
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, Mapping):
        return {
            str(clave): _json_seguro(contenido)
            for clave, contenido in valor.items()
        }
    if isinstance(valor, (tuple, list)):
        return [_json_seguro(item) for item in valor]
    return valor


def _normalizar_snapshot(
    tipo: str,
    fila: Mapping[str, Any],
) -> Mapping[str, Any]:
    if tipo == "OPERACIONES":
        registro = normalizar_fila_cartera(fila)
    elif tipo == "MORA":
        registro = normalizar_fila_mora(fila)
    elif tipo == "PROYECCION":
        registro = normalizar_fila_proyeccion(fila)
    else:
        raise ValueError(f"Tipo de fuente de Cartera desconocido: {tipo}.")

    if registro is None:
        return {}
    return _json_seguro(asdict(registro))


def _mapear_filas(
    valores: list[list[Any]],
    *,
    tipo: str,
    esquema_valido: bool,
) -> tuple[FilaSnapshotCartera, ...]:
    if not valores:
        return ()

    encabezados = [str(valor).strip() for valor in valores[0]]
    filas: list[FilaSnapshotCartera] = []

    for fila_fuente, valores_fila in enumerate(valores[1:], start=2):
        if not any(str(valor or "").strip() for valor in valores_fila):
            continue

        fila = {
            encabezado: (
                valores_fila[indice]
                if indice < len(valores_fila)
                else ""
            )
            for indice, encabezado in enumerate(encabezados)
            if encabezado
        }
        normalizado = (
            _normalizar_snapshot(tipo, fila)
            if esquema_valido
            else {}
        )
        filas.append(
            FilaSnapshotCartera(
                tipo=tipo,
                fila_fuente=fila_fuente,
                crudo={
                    "encabezados": encabezados,
                    "valores": list(valores_fila),
                },
                normalizado=normalizado,
            )
        )

    return tuple(filas)


def capturar_snapshot_cartera_desde_entorno(
    *,
    empresa_id: int,
    cliente: ClienteValoresGoogleSheets | None = None,
) -> SnapshotFuenteCartera:
    empresa_configurada = os.getenv(
        "CARTERA_SHEETS_EMPRESA_ID",
        "",
    ).strip()
    spreadsheet_id = os.getenv(
        "CARTERA_SHEETS_SPREADSHEET_ID",
        "",
    ).strip()

    faltantes_globales = [
        nombre
        for nombre, valor in (
            ("CARTERA_SHEETS_EMPRESA_ID", empresa_configurada),
            ("CARTERA_SHEETS_SPREADSHEET_ID", spreadsheet_id),
        )
        if not valor
    ]
    if faltantes_globales:
        raise ConfiguracionGoogleSheetsIncompletaError(
            "Falta configurar: " + ", ".join(faltantes_globales)
        )

    try:
        empresa_configurada_int = int(empresa_configurada)
    except ValueError as exc:
        raise ConfiguracionGoogleSheetsIncompletaError(
            "CARTERA_SHEETS_EMPRESA_ID debe ser entero."
        ) from exc

    if empresa_configurada_int != empresa_id:
        raise ConfiguracionGoogleSheetsIncompletaError(
            f"No existe configuración de Google Sheets para empresa {empresa_id}."
        )

    rangos = {
        tipo: os.getenv(variable, "").strip()
        for tipo, variable in RANGOS_CARTERA_ENV.items()
    }
    if not any(rangos.values()):
        raise ConfiguracionGoogleSheetsIncompletaError(
            "Falta configurar al menos un rango de Cartera."
        )

    cliente_real = cliente or ClienteGoogleSheetsApi(
        target_principal=os.getenv(
            "GOOGLE_IMPERSONATE_SERVICE_ACCOUNT",
            "",
        ).strip()
        or None,
    )

    diagnosticos: list[Mapping[str, Any]] = []
    filas: list[FilaSnapshotCartera] = []

    for tipo, rango in rangos.items():
        if not rango:
            diagnosticos.append(
                {
                    "tipo": tipo,
                    "rango": "",
                    "filas_datos": 0,
                    "valido": False,
                    "configurado": False,
                    "configuracion_faltante": RANGOS_CARTERA_ENV[tipo],
                    "campos_criticos_faltantes": [],
                    "encabezados_duplicados": [],
                }
            )
            continue

        try:
            valores = cliente_real.obtener_valores(
                spreadsheet_id=spreadsheet_id,
                rango=rango,
            )
        except Exception as exc:
            raise LecturaSnapshotCarteraError(
                f"No se pudo leer {tipo} ({rango}) para capturar el snapshot."
            ) from exc

        diagnostico = analizar_rango_cartera(
            valores,
            tipo=tipo,
            rango=rango,
        )
        diagnostico_dict = diagnostico.como_dict()
        diagnostico_dict["configurado"] = True
        diagnosticos.append(diagnostico_dict)
        filas.extend(
            _mapear_filas(
                valores,
                tipo=tipo,
                esquema_valido=diagnostico.valido,
            )
        )

    return SnapshotFuenteCartera(
        cargado_en=datetime.now(timezone.utc),
        spreadsheet_id=spreadsheet_id,
        rangos=rangos,
        diagnosticos=tuple(diagnosticos),
        filas=tuple(filas),
    )


def _hash_snapshot(snapshot: SnapshotFuenteCartera) -> str:
    payload = {
        "spreadsheet_id": snapshot.spreadsheet_id,
        "rangos": dict(sorted(snapshot.rangos.items())),
        "diagnosticos": [
            dict(item)
            for item in snapshot.diagnosticos
        ],
        "filas": [
            {
                "tipo": fila.tipo,
                "fila_fuente": fila.fila_fuente,
                "crudo": _json_seguro(fila.crudo),
            }
            for fila in snapshot.filas
        ],
    }
    serializado = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(serializado).hexdigest()


def guardar_snapshot_cartera(
    session: Session,
    *,
    empresa_id: int,
    snapshot: SnapshotFuenteCartera,
) -> tuple[CarteraSnapshot, bool]:
    contenido_hash = _hash_snapshot(snapshot)
    existente = session.scalar(
        select(CarteraSnapshot).where(
            CarteraSnapshot.empresa_id == empresa_id,
            CarteraSnapshot.contenido_hash == contenido_hash,
        )
    )
    if existente is not None:
        return existente, False

    persistido = CarteraSnapshot(
        empresa_id=empresa_id,
        spreadsheet_id=snapshot.spreadsheet_id,
        modo_fuente="GOOGLE_SHEETS",
        contenido_hash=contenido_hash,
        cargado_en=snapshot.cargado_en,
        filas=len(snapshot.filas),
        operaciones=snapshot.conteo("OPERACIONES"),
        registros_mora=snapshot.conteo("MORA"),
        proyecciones=snapshot.conteo("PROYECCION"),
        rangos=dict(snapshot.rangos),
        diagnosticos=[dict(item) for item in snapshot.diagnosticos],
    )
    session.add(persistido)
    session.flush()

    for fila in snapshot.filas:
        session.add(
            CarteraSnapshotFila(
                snapshot_id=persistido.id,
                tipo=fila.tipo,
                fila_fuente=fila.fila_fuente,
                crudo=_json_seguro(fila.crudo),
                normalizado=_json_seguro(fila.normalizado),
            )
        )

    return persistido, True


def listar_snapshots_cartera(
    session: Session,
    *,
    empresa_id: int,
    limite: int = 100,
) -> tuple[CarteraSnapshot, ...]:
    return tuple(
        session.scalars(
            select(CarteraSnapshot)
            .where(CarteraSnapshot.empresa_id == empresa_id)
            .order_by(
                CarteraSnapshot.guardado_en.desc(),
                CarteraSnapshot.id.desc(),
            )
            .limit(limite)
        )
    )


def snapshot_cartera_como_dict(
    snapshot: CarteraSnapshot,
) -> dict[str, object]:
    return {
        "id": snapshot.id,
        "empresa_id": snapshot.empresa_id,
        "spreadsheet_id": snapshot.spreadsheet_id,
        "modo_fuente": snapshot.modo_fuente,
        "contenido_hash": snapshot.contenido_hash,
        "cargado_en": snapshot.cargado_en.isoformat(),
        "guardado_en": (
            snapshot.guardado_en.isoformat()
            if snapshot.guardado_en is not None
            else None
        ),
        "filas": snapshot.filas,
        "operaciones": snapshot.operaciones,
        "registros_mora": snapshot.registros_mora,
        "proyecciones": snapshot.proyecciones,
        "rangos": snapshot.rangos,
        "diagnosticos": snapshot.diagnosticos,
    }
