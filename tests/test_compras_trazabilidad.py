from datetime import date

from app.motores.compras_supply_chain.cobertura import resumen_cobertura
from app.motores.compras_supply_chain.normalizacion import normalizar_fila_compra
from app.motores.compras_supply_chain.trazabilidad import (
    construir_timeline_oc,
    proximas_llegadas,
)


def _linea(
    *,
    pais: str = "CO",
    oc: str = "OC-1",
    estado: str = "ENVIADO A DESTINO",
    eta: str = "2026-10-05",
    entrega: str = "",
    factura_destino: str = "",
):
    return normalizar_fila_compra(
        {
            "NUMERO OC": oc,
            "CLIENTE": "Cliente",
            "SKU": "SKU-1",
            "DESCRIPCION": "Producto",
            "PROVEEDOR": "Proveedor",
            "NUMERO DE FACTURA": "FAC-P-1",
            "VALOR TOTAL COMPRA USD": "100",
            "VALOR OCI (DDP)": "130",
            "FECHA DE COMPRA EN CHINA (ABONO)": "2026-08-01",
            "FECHA PAGO TOTAL EN CHINA": "",
            "FECHA ENTREGA PROV. ESTIMADA (auto)": "2026-08-20",
            "FECHA FINALIZACIÓN DE PRODUCCIÓN": "2026-08-18",
            "FECHA INGRESO A BODEGA EN ORIGEN": "2026-08-22",
            "MODO TRANSPORTE": "MARITIMO",
            "DOC TRANSPORTE": "BL-1",
            "FECHA CARGUE": "2026-08-25",
            "ETD": "2026-08-26",
            "ETA": eta,
            "NACIONALIZACION": "",
            "FECHA ENTREGA A BODEGA EN BOG": entrega,
            "FACTURA": factura_destino,
            "ESTADO": estado,
            "FECHA SOLICITUD PAGO (abono)": "",
            "ELABORO OC": "Compras",
            "COMERCIAL ASIGNADO": "Comercial",
        },
        pais=pais,
        fila_fuente=7,
    )


def test_normalization_preserves_extended_procurement_and_logistics_fields() -> None:
    linea = normalizar_fila_compra(
        {
            "NUMERO OC": "OC-99",
            "CLIENTE": "Cliente",
            "DESCRIPCION": "Producto",
            "QTY": "12",
            "UNIDAD COMERCIAL": "PCE",
            "NOMBRE UNIDAD COMERCIAL (auto)": "Pieza",
            "SKU": "SKU-X",
            "SOLICITUD COTIZACION ID COTIZACION": "COT-1",
            "PROVEEDOR": "Proveedor",
            "NUMERO DE FACTURA": "INV-7",
            "INCOTERMS": "FOB",
            "COSTO COMPRA CHINA/VENTA A LATAM USD": "3.25",
            "VALOR TOTAL COMPRA USD": "39.00",
            "TIPO DE NEGOCIACION": "CREDITO",
            "VALOR OCI (DDP)": "55.00",
            "FECHA DE COMPRA EN CHINA (ABONO)": "2026-01-10",
            "FECHA PAGO TOTAL EN CHINA": "2026-02-10",
            "PRODUCTION TIME DAYS (ESTIMADO)": "20",
            "CTN": "2",
            "PESO VOL (auto)": "10",
            "LARGO (cm)": "30",
            "ANCHO (cm)": "20",
            "ALTO (cm)": "10",
            "CBM": "0.5",
            "PESO TOTAL (Kg)": "8",
            "FECHA ENTREGA PROV. ESTIMADA (auto)": "2026-02-01",
            "FECHA FINALIZACIÓN DE PRODUCCIÓN": "2026-01-29",
            "FECHA INGRESO A BODEGA EN ORIGEN": "2026-02-02",
            "MODO TRANSPORTE": "MARITIMO",
            "DOC TRANSPORTE": "BL-99",
            "CERTIFICADO DE ORIGEN": "SI",
            "FECHA CARGUE": "2026-02-03",
            "ETD": "2026-02-04",
            "Telex/BL (auto)": "TLX-99",
            "ETA": "2026-03-01",
            "NACIONALIZACION": "2026-03-03",
            "FECHA ENTREGA A BODEGA EN QUITO": "2026-03-05",
            "FACTURA": "FAC-DEST-1",
            "ESTADO": "ENTREGADO",
            "COMERCIAL ASIGNADO": "Comercial",
            "FECHA SOLICITUD PAGO (abono)": "2026-01-09",
            "MOTIVO DEMORA ABONO": "",
            "ELABORO OC": "Compras",
        },
        pais="EC",
        fila_fuente=9,
    )

    assert linea.cantidad == "12"
    assert linea.unidad_comercial == "PCE"
    assert linea.id_cotizacion == "COT-1"
    assert linea.numero_factura_proveedor == "INV-7"
    assert linea.incoterm == "FOB"
    assert linea.costo_unitario_usd_origen == "3.25"
    assert linea.fecha_abono_compra == "2026-01-10"
    assert linea.fecha_pago_total_compra == "2026-02-10"
    assert linea.cbm_origen == ""  # EC/CL conservan CBM ambiguo solo en crudo.
    assert linea.fecha_fin_produccion == "2026-01-29"
    assert linea.fecha_cargue == "2026-02-03"
    assert linea.telex_bl == "TLX-99"
    assert linea.nacionalizacion == "2026-03-03"
    assert linea.factura_destino == "FAC-DEST-1"
    assert linea.comercial_asignado == "Comercial"
    assert linea.elaboro_oc == "Compras"


def test_coverage_is_descriptive_and_separates_current_population_from_delivered() -> None:
    activa = _linea()
    entregada = _linea(
        oc="OC-2",
        estado="ENTREGADO",
        eta="2026-09-01",
        entrega="2026-09-05",
        factura_destino="FAC-D-2",
    )

    resumen = resumen_cobertura((activa, entregada))

    assert resumen["general"]["lineas"] == 2
    assert resumen["poblacion_actual"]["lineas"] == 1
    assert resumen["entregado"]["lineas"] == 1
    assert resumen["general"]["campos"]["valor_oci_ddp"]["faltantes"] == 0
    assert (
        resumen["poblacion_actual"]["campos"]["fecha_solicitud_pago_abono"]["faltantes"]
        == 1
    )
    assert resumen["entregado"]["campos"]["factura_destino"]["faltantes"] == 0


def test_timeline_keeps_milestones_per_source_line_without_inventing_oc_dates() -> None:
    linea = _linea()

    timeline = construir_timeline_oc((linea,), pais="CO", numero_oc="OC-1")

    assert timeline["pais"] == "CO"
    assert timeline["numero_oc"] == "OC-1"
    assert timeline["lineas"] == 1
    item = timeline["items"][0]
    assert item["fila_fuente"] == 7
    assert item["sku"] == "SKU-1"
    codigos = [hito["codigo"] for hito in item["hitos"]]
    assert codigos == [
        "ABONO_COMPRA",
        "ENTREGA_PROVEEDOR_ESTIMADA",
        "FIN_PRODUCCION",
        "INGRESO_BODEGA_ORIGEN",
        "CARGUE",
        "ETD",
        "ETA",
    ]


def test_next_arrivals_use_parsed_eta_and_exclude_delivered_lines() -> None:
    dentro = _linea(oc="OC-1", eta="2026-10-05")
    fuera = _linea(oc="OC-2", eta="2026-11-20")
    entregada = _linea(
        oc="OC-3",
        estado="ENTREGADO",
        eta="2026-10-03",
        entrega="2026-10-04",
    )

    resultado = proximas_llegadas(
        (dentro, fuera, entregada),
        hoy=date(2026, 9, 29),
        dias=30,
    )

    assert resultado["desde"] == "2026-09-29"
    assert resultado["hasta"] == "2026-10-29"
    assert resultado["lineas"] == 1
    assert resultado["items"][0]["numero_oc"] == "OC-1"
    assert resultado["items"][0]["eta"] == "2026-10-05"
