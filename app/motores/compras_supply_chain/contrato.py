from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .normalizacion import normalizar_encabezado


@dataclass(frozen=True)
class CampoContrato:
    canonico: str
    aliases: tuple[str, ...]
    critico: bool = False


CAMPOS: tuple[CampoContrato, ...] = (
    CampoContrato("numero_oc", ("NUMERO OC",), critico=True),
    CampoContrato("cliente", ("CLIENTE",), critico=True),
    CampoContrato("sku", ("SKU",), critico=False),
    CampoContrato("descripcion", ("DESCRIPCION", "DESCRIPCIÓN"), critico=False),
    CampoContrato("proveedor", ("PROVEEDOR",), critico=True),
    CampoContrato("estado", ("ESTADO", "ESTADO "), critico=True),
    CampoContrato("modo_transporte", ("MODO TRANSPORTE",), critico=True),
    CampoContrato(
        "documento_transporte",
        ("DOCUMENTO DE TRANSPORTE", "DOC TRANSPORTE"),
        critico=False,
    ),
    CampoContrato("etd", ("ETD",), critico=False),
    CampoContrato("eta", ("ETA", " ETA"), critico=False),
    CampoContrato(
        "fecha_entrega_bodega_destino",
        (
            "FECHA ENTREGA EN BODEGA BOGOTA",
            "FECHA ENTREGA EN BODEGA BOGOTÁ",
            "FECHA ENTREGA EN BODEGA QUITO",
            "FECHA ENTREGA EN BODEGA SANTIAGO",
            "FECHA ENTREGA A BODEGA EN BOG",
            "FECHA ENTREGA A BODEGA EN QUITO",
            "FECHA ENTREGA A BODEGA EN SANTIAGO",
            "FECHA ENTREGA BODEGA DESTINO",
        ),
        critico=False,
    ),
    CampoContrato(
        "valor_total_compra_usd",
        ("VALOR TOTAL COMPRA USD",),
        critico=False,
    ),
    CampoContrato("valor_oci_ddp", ("VALOR OCI (DDP)",), critico=False),
)


_ALIAS_A_CAMPO = {
    normalizar_encabezado(alias): campo.canonico
    for campo in CAMPOS
    for alias in campo.aliases
}


@dataclass(frozen=True)
class DiagnosticoEsquema:
    pais: str
    rango: str
    encabezados: tuple[str, ...]
    filas_datos: int
    campos_reconocidos: tuple[str, ...]
    campos_criticos_faltantes: tuple[str, ...]
    campos_esperados_faltantes: tuple[str, ...]
    encabezados_duplicados: tuple[str, ...]
    encabezados_no_consumidos: tuple[str, ...]

    @property
    def valido(self) -> bool:
        return not self.campos_criticos_faltantes and not self.encabezados_duplicados

    def como_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["valido"] = self.valido
        return data


def es_encabezado_consumido(encabezado: Any) -> bool:
    return normalizar_encabezado(encabezado) in _ALIAS_A_CAMPO


def analizar_encabezados(
    encabezados: Iterable[Any],
    *,
    pais: str,
    rango: str,
    filas_datos: int,
) -> DiagnosticoEsquema:
    originales = tuple(str(valor or "").strip() for valor in encabezados)
    normalizados = [normalizar_encabezado(valor) for valor in originales]

    conteos: dict[str, int] = {}
    for encabezado in normalizados:
        if not encabezado:
            continue
        conteos[encabezado] = conteos.get(encabezado, 0) + 1

    duplicados = tuple(
        sorted(
            encabezado
            for encabezado, cantidad in conteos.items()
            if cantidad > 1 and encabezado in _ALIAS_A_CAMPO
        )
    )

    reconocidos = {
        _ALIAS_A_CAMPO[encabezado]
        for encabezado in normalizados
        if encabezado in _ALIAS_A_CAMPO
    }

    criticos = {campo.canonico for campo in CAMPOS if campo.critico}
    esperados = {campo.canonico for campo in CAMPOS}

    faltantes_criticos = tuple(sorted(criticos - reconocidos))
    faltantes_esperados = tuple(sorted((esperados - reconocidos) - criticos))

    no_consumidos = tuple(
        original
        for original, normalizado in zip(originales, normalizados, strict=True)
        if normalizado and normalizado not in _ALIAS_A_CAMPO
    )

    return DiagnosticoEsquema(
        pais=pais,
        rango=rango,
        encabezados=originales,
        filas_datos=filas_datos,
        campos_reconocidos=tuple(sorted(reconocidos)),
        campos_criticos_faltantes=faltantes_criticos,
        campos_esperados_faltantes=faltantes_esperados,
        encabezados_duplicados=duplicados,
        encabezados_no_consumidos=no_consumidos,
    )
