from datetime import date

from app.motores.compras_supply_chain.atencion import evaluar_puntos_atencion
from app.motores.compras_supply_chain.normalizacion import normalizar_fila_compra


def _linea(
    *,
    fila: int,
    oc: str,
    estado: str,
    proveedor: str = "Proveedor",
    transporte: str = "MARITIMO",
    documento: str = "",
    etd: str = "",
    eta: str = "",
    entrega: str = "",
):
    return normalizar_fila_compra(
        {
            "NUMERO OC": oc,
            "CLIENTE": "Cliente",
            "SKU": f"SKU-{fila}",
            "PROVEEDOR": proveedor,
            "ESTADO": estado,
            "MODO TRANSPORTE": transporte,
            "DOCUMENTO DE TRANSPORTE": documento,
            "ETD": etd,
            "ETA": eta,
            "FECHA ENTREGA EN BODEGA BOGOTA": entrega,
            "VALOR TOTAL COMPRA USD": "100",
            "VALOR OCI (DDP)": "150",
        },
        pais="CO",
        fila_fuente=fila,
    )


def test_attention_detects_objective_shipping_and_eta_observations() -> None:
    lineas = (
        _linea(
            fila=2,
            oc="OC-1",
            estado="ENVIADO A DESTINO",
            eta="2026-09-20",
        ),
        _linea(
            fila=3,
            oc="OC-2",
            estado="EN OTM",
            documento="OTM-1",
            etd="2026-09-01",
            eta="20/09/2026",
        ),
        _linea(
            fila=4,
            oc="OC-3",
            estado="ENTREGADO",
            eta="2026-09-01",
            entrega="2026-09-02",
        ),
        _linea(
            fila=5,
            oc="OC-4",
            estado="EN PRODUCCION",
            eta="fecha rara",
        ),
    )

    resultados = {
        punto.codigo: punto
        for punto in evaluar_puntos_atencion(
            lineas,
            hoy=date(2026, 9, 29),
        )
    }

    assert resultados["ENVIADA_SIN_DOCUMENTO"].cantidad == 1
    assert resultados["ENVIADA_SIN_ETD"].cantidad == 1
    assert resultados["ETA_VENCIDA_SIN_ENTREGA"].cantidad == 2
    assert resultados["ETA_NO_INTERPRETABLE"].cantidad == 1
    assert "ENVIADA_SIN_ETA" not in resultados


def test_attention_detects_mixed_order_dimensions_without_aggregating_state() -> None:
    lineas = (
        _linea(
            fila=2,
            oc="OC-MIX",
            estado="EN PRODUCCION",
            proveedor="P1",
            transporte="MARITIMO",
        ),
        _linea(
            fila=3,
            oc="OC-MIX",
            estado="ENVIADO A DESTINO",
            proveedor="P2",
            transporte="AEREO",
            documento="AWB",
            etd="2026-09-20",
            eta="2026-10-10",
        ),
    )

    resultados = {
        punto.codigo: punto
        for punto in evaluar_puntos_atencion(
            lineas,
            hoy=date(2026, 9, 29),
        )
    }

    assert resultados["OC_ESTADOS_MIXTOS"].cantidad == 1
    assert resultados["OC_PROVEEDORES_MULTIPLES"].cantidad == 1
    assert resultados["OC_TRANSPORTES_MULTIPLES"].cantidad == 1
    assert resultados["OC_ESTADOS_MIXTOS"].muestras[0].numero_oc == "OC-MIX"
