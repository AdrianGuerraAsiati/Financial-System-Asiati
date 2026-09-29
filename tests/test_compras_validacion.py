from decimal import Decimal

from app.motores.compras_supply_chain.normalizacion import normalizar_fila_compra
from app.motores.compras_supply_chain.validacion import (
    comparar_con_supply_chain,
    extraer_referencias_supply_chain,
    resumen_validacion,
)


def _linea(*, pais: str, estado: str, ddp: str, fila: int):
    return normalizar_fila_compra(
        {
            "NUMERO OC": f"OC-{pais}-{fila}",
            "CLIENTE": "Cliente",
            "PROVEEDOR": "Proveedor",
            "ESTADO": estado,
            "MODO TRANSPORTE": "MARITIMO",
            "VALOR TOTAL COMPRA USD": "100",
            "VALOR OCI (DDP)": ddp,
        },
        pais=pais,
        fila_fuente=fila,
    )


def test_validation_parser_finds_country_pivots_and_compares_exact_ddp() -> None:
    valores = [
        ["COLOMBIA"],
        ["ESTADO", "SUM de VALOR OCI (DDP)"],
        ["EN PRODUCCION", "300.00"],
        ["ENVIADO A DESTINO", "150.00"],
        [],
        ["ECUADOR"],
        ["ESTADO", "SUM DE VALOR OCI (DDP)"],
        ["EN NACIONALIZACION", "80.00"],
    ]
    referencias = extraer_referencias_supply_chain(valores)

    assert [ref.pais for ref in referencias] == ["CO", "EC"]
    assert dict(referencias[0].estados_ddp)["EN PRODUCCION"] == Decimal("300.00")

    lineas = (
        _linea(pais="CO", estado="EN PRODUCCION", ddp="100", fila=2),
        _linea(pais="CO", estado="EN PRODUCCION", ddp="200", fila=3),
        _linea(pais="CO", estado="ENVIADO A DESTINO", ddp="150", fila=4),
        _linea(pais="EC", estado="EN NACIONALIZACION", ddp="80", fila=2),
        _linea(pais="CO", estado="ENTREGADO", ddp="999", fila=5),
    )
    comparaciones = comparar_con_supply_chain(lineas, referencias)

    assert all(item.resultado == "COINCIDE" for item in comparaciones)
    assert resumen_validacion(comparaciones)["todo_coincide"] is True


def test_validation_does_not_guess_country_when_pivot_has_no_country_marker() -> None:
    referencias = extraer_referencias_supply_chain(
        [
            ["ESTADO", "SUM de VALOR OCI (DDP)"],
            ["EN PRODUCCION", "100"],
        ]
    )

    assert referencias == ()


def test_validation_reports_difference_and_missing_active_state() -> None:
    referencias = extraer_referencias_supply_chain(
        [
            ["CHILE"],
            ["ESTADO", "SUM de VALOR OCI (DDP)"],
            ["EN PRODUCCION", "100"],
        ]
    )
    lineas = (
        _linea(pais="CL", estado="EN PRODUCCION", ddp="90", fila=2),
        _linea(pais="CL", estado="EN OTM", ddp="25", fila=3),
    )

    por_estado = {
        item.estado: item
        for item in comparar_con_supply_chain(lineas, referencias)
    }

    assert por_estado["EN PRODUCCION"].resultado == "DIFERENCIA"
    assert por_estado["EN PRODUCCION"].diferencia == Decimal("-10")
    assert por_estado["EN OTM"].resultado == "SOLO_DETALLE"
