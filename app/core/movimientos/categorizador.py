from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import re
import unicodedata
from typing import Any, Iterable, Mapping


DIMENSIONES_CATEGORIZACION = (
    "tipo",
    "unidad_negocio",
    "categoria",
    "empresa",
    "tercero",
    "modalidad",
    "fijo_variable",
)


@dataclass(frozen=True)
class ResultadoCategorizacion:
    estado: str
    regla: Any | None
    tipo: str | None = None
    unidad_negocio: str | None = None
    categoria: str | None = None
    empresa: str | None = None
    tercero: str | None = None
    modalidad: str | None = None
    fijo_variable: str | None = None
    ciudad: str | None = None

    @property
    def regla_id(self) -> int | None:
        valor = _valor(self.regla, "id")
        return int(valor) if valor is not None else None


def normalizar_descripcion(valor: object) -> str:
    """Normaliza: mayúsculas, sin tildes y espacios colapsados."""
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.upper().split())


def _valor(regla: Any, nombre: str, defecto: Any = None) -> Any:
    if isinstance(regla, Mapping):
        return regla.get(nombre, defecto)
    return getattr(regla, nombre, defecto)


def _activa(regla: Any) -> bool:
    return bool(_valor(regla, "activa", True))


def _prioridad(regla: Any) -> tuple[int, int]:
    return int(_valor(regla, "prioridad", 0)), int(_valor(regla, "id", 0) or 0)


def _match_patron(descripcion_norm: str, regla: Any) -> bool:
    patron = str(_valor(regla, "patron", "") or "")
    tipo_match = str(_valor(regla, "tipo_match", "") or "").upper()

    if tipo_match == "REGEX":
        return re.search(patron, descripcion_norm, flags=re.IGNORECASE) is not None

    patron_norm = normalizar_descripcion(patron)
    if tipo_match == "EXACTO":
        return descripcion_norm == patron_norm
    if tipo_match == "EMPIEZA_CON":
        return descripcion_norm.startswith(patron_norm)
    if tipo_match == "CONTIENE":
        return patron_norm in descripcion_norm
    raise ValueError(f"Tipo de match no soportado: {tipo_match}")


def _en_lista_normalizada(valor: str | None, esperado: object) -> bool:
    if isinstance(esperado, (list, tuple, set, frozenset)):
        opciones = {normalizar_descripcion(x) for x in esperado}
    else:
        opciones = {normalizar_descripcion(esperado)}
    return normalizar_descripcion(valor) in opciones


def _cumple_condiciones(
    descripcion_norm: str,
    regla: Any,
    *,
    tipo_fuente: str | None,
    monto: Decimal | int | float | str | None,
    contexto: Mapping[str, Any],
) -> bool:
    condiciones = _valor(regla, "condiciones") or {}

    if "tipo_fuente" in condiciones and not _en_lista_normalizada(
        tipo_fuente, condiciones["tipo_fuente"]
    ):
        return False

    if "contiene" in condiciones:
        partes = condiciones["contiene"]
        if not isinstance(partes, (list, tuple, set, frozenset)):
            partes = [partes]
        if any(
            normalizar_descripcion(parte) not in descripcion_norm
            for parte in partes
            if parte not in (None, "")
        ):
            return False

    if "contraparte" in condiciones and not _en_lista_normalizada(
        str(contexto.get("contraparte") or ""), condiciones["contraparte"]
    ):
        return False

    if monto is not None:
        valor_monto = Decimal(str(monto))
        if "monto_min" in condiciones and valor_monto < Decimal(
            str(condiciones["monto_min"])
        ):
            return False
        if "monto_max" in condiciones and valor_monto > Decimal(
            str(condiciones["monto_max"])
        ):
            return False
        signo = condiciones.get("signo")
        if signo == "POSITIVO" and valor_monto <= 0:
            return False
        if signo == "NEGATIVO" and valor_monto >= 0:
            return False
        if signo == "CERO" and valor_monto != 0:
            return False

    return True


def _dimension(regla: Any, contexto: Mapping[str, Any], nombre: str) -> str | None:
    valor = _valor(regla, nombre)
    if valor is None:
        valor = contexto.get(nombre)
    if valor is None:
        return None
    return str(valor)


def categorizar(
    descripcion: str,
    reglas: Iterable[Any],
    *,
    tipo_fuente: str | None = None,
    monto: Decimal | int | float | str | None = None,
    contexto: Mapping[str, Any] | None = None,
) -> ResultadoCategorizacion:
    """Aplica la primera regla activa por prioridad."""
    contexto = contexto or {}
    descripcion_norm = normalizar_descripcion(descripcion)

    for regla in sorted((r for r in reglas if _activa(r)), key=_prioridad):
        if not _match_patron(descripcion_norm, regla):
            continue
        if not _cumple_condiciones(
            descripcion_norm,
            regla,
            tipo_fuente=tipo_fuente,
            monto=monto,
            contexto=contexto,
        ):
            continue

        return ResultadoCategorizacion(
            estado="REVISAR" if bool(_valor(regla, "requiere_revision", False)) else "AUTO",
            regla=regla,
            tipo=_dimension(regla, contexto, "tipo"),
            unidad_negocio=_dimension(regla, contexto, "unidad_negocio"),
            categoria=_dimension(regla, contexto, "categoria"),
            empresa=_dimension(regla, contexto, "empresa"),
            tercero=_dimension(regla, contexto, "tercero"),
            modalidad=_dimension(regla, contexto, "modalidad"),
            fijo_variable=_dimension(regla, contexto, "fijo_variable"),
            ciudad=_dimension(regla, contexto, "ciudad"),
        )

    return ResultadoCategorizacion(estado="PENDIENTE", regla=None)
