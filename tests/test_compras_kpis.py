from decimal import Decimal, InvalidOperation

import pytest

from app.motores.compras_supply_chain.contrato import analizar_encabezados
from app.motores.compras_supply_chain.kpis import (
    ESTADOS_ACTIVOS_TABLERO_ACTUAL,
    calcular_familias_monetarias,
    decimal_desde_fuente,
)
from app.motores.compras_supply_chain.normalizacion import normalizar_fila_compra


ENCABEZADOS = [
    "NUMERO OC",
    "CLIENTE",
    "PROVEEDOR",
    "ESTADO",
    "MODO TRANSPORTE",
    "VALOR TOTAL COMPRA USD",
    "VALOR OCI (DDP)",
]


def _diagnosticos(*, sin_ddp_en: str | None = None):
    resultado = []
    for pais in ("CO", "EC", "CL"):
        encabezados = list(ENCABEZADOS)
        if pais == sin_ddp_en:
            encabezados.remove("VALOR OCI (DDP)")
        resultado.append(
            analizar_encabezados(
                encabezados,
                pais=pais,
                rango=f"{pais}!A:Z",
                filas_datos=1,
            )
        )
    return tuple(resultado)


def _linea(
    *,
    estado: str,
    costo: str,
    ddp: str,
    pais: str = "CO",
    fila: int = 2,
):
    return normalizar_fila_compra(
        {
            "NUMERO OC": f"OC-{fila}",
            "CLIENTE": "Cliente",
            "PROVEEDOR": "Proveedor",
            "ESTADO": estado,
            "MODO TRANSPORTE": "MARITIMO",
            "VALOR TOTAL COMPRA USD": costo,
            "VALOR OCI (DDP)": ddp,
        },
        pais=pais,
        fila_fuente=fila,
    )


@pytest.mark.parametrize(
    ("origen", "esperado"),
    [
        ("1.234,56", Decimal("1234.56")),
        ("1,234.56", Decimal("1234.56")),
        ("1.234", Decimal("1234")),
        ("1,234", Decimal("1234")),
        ("1234,5", Decimal("1234.5")),
        ("1234.50", Decimal("1234.50")),
        ("US$ 2.500,25", Decimal("2500.25")),
        ("(10,50)", Decimal("-10.50")),
    ],
)
def test_money_parser_accepts_common_sheet_formats(
    origen: str,
    esperado: Decimal,
) -> None:
    assert decimal_desde_fuente(origen) == esperado


def test_money_parser_returns_none_for_blank_and_rejects_non_numeric() -> None:
    assert decimal_desde_fuente("") is None
    with pytest.raises(InvalidOperation):
        decimal_desde_fuente("sin valor")


def test_two_families_use_distinct_columns_and_same_active_population() -> None:
    lineas = (
        _linea(
            estado="EN PRODUCCION",
            costo="1.000,50",
            ddp="1,500.75",
            fila=2,
        ),
        _linea(
            estado="EN OTM",
            costo="200",
            ddp="300",
            fila=3,
        ),
        _linea(
            estado="ENTREGADO",
            costo="500",
            ddp="800",
            fila=4,
        ),
        _linea(
            estado="ANULADA",
            costo="100",
            ddp="200",
            fila=5,
        ),
    )

    resultados = {
        resultado.familia.codigo: resultado
        for resultado in calcular_familias_monetarias(
            lineas,
            _diagnosticos(),
        )
    }

    costo = resultados["costo_compra"]
    ddp = resultados["valor_comercial_ddp"]

    assert costo.disponible is True
    assert ddp.disponible is True
    assert costo.activo.monto == Decimal("1200.50")
    assert ddp.activo.monto == Decimal("1800.75")
    assert costo.general.monto == Decimal("1800.50")
    assert ddp.general.monto == Decimal("2800.75")

    assert {
        estado
        for estado, activo, _ in costo.por_estado
        if activo
    }.issuperset({"EN PRODUCCION", "EN OTM"})
    assert "ENTREGADO" not in ESTADOS_ACTIVOS_TABLERO_ACTUAL
    assert "ANULADA" not in ESTADOS_ACTIVOS_TABLERO_ACTUAL


def test_active_population_includes_current_supply_chain_pivot_states() -> None:
    assert set(ESTADOS_ACTIVOS_TABLERO_ACTUAL) == {
        "EN BODEGA ASIATI SHENZHEN",
        "EN BODEGA ASIATI YIWU",
        "EN NACIONALIZACION",
        "EN OTM",
        "EN PRODUCCION",
        "ENVIADO A DESTINO",
        "PENDIENTE DEPOSITO",
    }


def test_family_is_unavailable_if_its_source_column_is_missing_in_one_country() -> None:
    lineas = (
        _linea(
            estado="EN PRODUCCION",
            costo="100",
            ddp="150",
            pais="CO",
        ),
    )

    resultados = {
        resultado.familia.codigo: resultado
        for resultado in calcular_familias_monetarias(
            lineas,
            _diagnosticos(sin_ddp_en="EC"),
        )
    }

    assert resultados["costo_compra"].disponible is True
    assert resultados["valor_comercial_ddp"].disponible is False
    assert resultados["valor_comercial_ddp"].hojas_sin_campo == ("EC",)
    assert resultados["valor_comercial_ddp"].activo is None


def test_country_filter_only_requires_the_selected_country_column() -> None:
    lineas = (
        _linea(
            estado="ENVIADO A DESTINO",
            costo="100",
            ddp="150",
            pais="CO",
        ),
    )

    resultados = {
        resultado.familia.codigo: resultado
        for resultado in calcular_familias_monetarias(
            lineas,
            _diagnosticos(sin_ddp_en="EC"),
            pais="CO",
        )
    }

    assert resultados["valor_comercial_ddp"].disponible is True
    assert resultados["valor_comercial_ddp"].activo.monto == Decimal("150")
