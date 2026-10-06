"""Pruebas sintéticas del motor de wallets de tienda y de solo pagos. No usan archivos reales."""
import json
from pathlib import Path

import pandas as pd
import pytest

from app.motores.conciliacion_wallets.catalogo import categorizar, clasificar_concepto, cruzar_entre_wallets
from app.motores.conciliacion_wallets.pagos import conciliar_wallet_pagos
from app.motores.conciliacion_wallets.tiendas import conciliar_wallet_tienda
from app.motores.conciliacion_wallets.wiilog import carga
from app.motores.conciliacion_wallets.wiilog.integracion import resolver_identificador_wallet

RAIZ = Path(__file__).resolve().parents[2]
DOCS = RAIZ / "docs/motores/conciliacion_wallets"
WIILOG_TEST_EMAIL = "wallet-principal@wiilog.test"


def _config_test(nombre: str) -> dict:
    return resolver_identificador_wallet(
        json.loads((DOCS / nombre).read_text(encoding="utf-8")),
        wallet_principal_email=WIILOG_TEST_EMAIL,
    )


PARAMS = _config_test("parametros_wallet_tienda.json")
PAGOS = _config_test("parametros_wallet_pagos.json")
CATALOGO = _config_test("catalogo_conceptos_wallets.json")
TARIFAS = {"WIILOG BOGOTA": 2500, "WIILOG BOGOTA 2.0": None}

DS = {"usuario_email": "tienda@x.co", "nombre": "Tienda", "rol": "DROPSHIPPER", "empresa": None}
PROV = {"usuario_email": "prov@x.co", "nombre": "Prov", "rol": "PROVEEDOR", "empresa": None}


def orden(oid, estatus, envio="CON RECAUDO", ds="tienda@x.co", prov="prov@x.co", gan_ds=50000, gan_prov=30000, ppxc=30000,
          flete=15000, transp="ENVIA", bodega="WIILOG BOGOTÁ", entregado="20/09/2026", devolucion=None, guia="18/09/2026",
          valor=100000):
    return {
        "FECHA DE REPORTE": "28-09-2026", "ID": oid, "ESTATUS": estatus, "TIPO DE ENVIO": envio, "TRANSPORTADORA": transp,
        "BODEGA": bodega, "FECHA GENERACION DE GUIA": guia, "FECHA ENTREGADO": entregado if estatus == "ENTREGADO" else None,
        "FECHA DEVOLUCION": devolucion, "EMAIL": ds, "PROVEEDOR EMAIL": prov, "GANANCIA TOTAL DE DROPSHIPPER": gan_ds,
        "GANANCIA TOTAL DE PROVEEDORES": gan_prov, "PRECIO PROVEEDOR X CANTIDAD": ppxc, "PRECIO FLETE": flete,
        "VALOR DE COMPRA EN PRODUCTOS": valor,
    }


def wallet(movs, saldo_inicial=0.0, email="tienda@x.co"):
    """movs = [(fecha, tipo, monto, orden_id, descripcion)]. El saldo previo se arma para que cuadre."""
    filas, saldo = [], saldo_inicial
    for i, (f, tipo, monto, oid, desc) in enumerate(movs):
        filas.append({"ID": 1000 + i, "USUARIO EMAIL": email, "FECHA": f, "TIPO": tipo, "MONTO": monto, "MONTO PREVIO": saldo,
                      "ORDEN ID": oid, "NUMERO DE GUIA": None, "DESCRIPCIÓN": desc, "USUARIO QUE REALIZA EL MOVIMIENTO": None,
                      "CUENTA": None, "CONCEPTO DE RETIRO": None})
        saldo += monto if tipo == "ENTRADA" else -monto
    return pd.DataFrame(filas)


def gan_ds(oid, monto, f="21-09-2026 03:00"):
    return (f, "ENTRADA", monto, oid, f"ENTRADA POR GANANCIA EN LA ORDEN COMO DROPSHIPPER: {oid}* GUIA: *1*")


def gan_prov(oid, monto, f="21-09-2026 03:00"):
    return (f, "ENTRADA", monto, oid, f"ENTRADA POR GANANCIA EN LA ORDEN COMO PROVEEDOR: {oid}* GUIA: *1*")


def ff(oid, monto=2500, f="18-09-2026 10:00"):
    return (f, "SALIDA", monto, oid, f"SALIDA POR FULFILLMENT, ORDEN ID: {oid}")


def correr(ordenes, movs, tienda=DS, **kw):
    return conciliar_wallet_tienda(pd.DataFrame(ordenes), wallet(movs, 1_000_000), PARAMS, CATALOGO, tienda,
                                   "2026-09-18", "2026-09-30", TARIFAS, corte_ordenes="2026-09-28 14:00", **kw)


# ------------------------------------------------------------------ catálogo


@pytest.mark.parametrize("tipo,texto,esperado", [
    ("ENTRADA", "ENTRADA POR GANANCIA EN LA ORDEN COMO DROPSHIPPER: 1* GUIA: *2*", "GANANCIA_DROPSHIPPER"),
    ("SALIDA", "RET. ADMIN: DESCUENTO POR SALDO NEGATIVO DEL USUARIO A@B.CO", "RET_ADMIN_SALDO_NEGATIVO"),
    ("SALIDA", "RET. ADMIN: TIQUETE ANGEL", "RET_ADMIN_OTRO"),
    ("ENTRADA", "ENTRADA POR RETIRO ADMIN EN USER X@Y.CO: SALDO NEGATIVO", "CRUCE_DESCUENTO_IN"),
    ("ENTRADA", "ENTRADA POR RETIRO ADMIN EN USER X@Y.CO: TIQUETE", "RETIRO_ADMIN_EN_USER"),
    ("SALIDA", f"SALIDA POR RECARGA DE SALDO EN CARTERA AL USUARIO {WIILOG_TEST_EMAIL}", "TRASLADO_WALLET_WIILOG"),
    ("SALIDA", "SALIDA POR RECARGA DE SALDO EN CARTERA AL USUARIO OTRO@X.CO", "TRANSFERENCIA_SUPER_ADMIN"),
    ("SALIDA", "TEXTO QUE DROPI INVENTO MANANA", "SIN_CONCEPTO"),
])
def test_catalogo_primera_regla_gana(tipo, texto, esperado):
    assert clasificar_concepto(tipo, texto, CATALOGO["conceptos"]) == esperado


def test_empresa_sale_de_la_wallet_y_no_del_concepto():
    w = carga.leer_wallet(wallet([gan_ds(1, 100.0)]), PARAMS)
    m = categorizar(w, CATALOGO, {**DS, "empresa": "EMPRESA X"})
    assert m.empresa.iloc[0] == "EMPRESA X"
    m = categorizar(w, CATALOGO, DS)
    assert m.empresa.isna().iloc[0]  # null = por confirmar, no se inventa


def test_transferencia_entre_wallets_propias_es_traslado_y_se_cruza():
    a = carga.leer_wallet(wallet([("08-09-2026 19:23", "SALIDA", 4000000, None,
                                   "SALIDA POR TRANSFERENCIA DE WALLET AL USUARIO prov@x.co")], 5_000_000), PARAMS)
    b = carga.leer_wallet(wallet([("08-09-2026 19:23", "ENTRADA", 4000000, None,
                                   "ENTRADA POR TRANSFERENCIA DE WALLET DESDE EL USUARIO tienda@x.co")], email="prov@x.co"), PARAMS)
    propias = ["tienda@x.co", "prov@x.co"]
    ma = categorizar(a, CATALOGO, {**DS, "wallets_propias": propias})
    mb = categorizar(b, CATALOGO, {**PROV, "wallets_propias": propias})
    assert ma.ingreso_egreso.iloc[0] == "TRASLADO" and not ma.requiere_revision.iloc[0]
    out = cruzar_entre_wallets({"tienda@x.co": ma, "prov@x.co": mb})
    assert out["tienda@x.co"].cruce_id.iloc[0] == out["prov@x.co"].cruce_id.iloc[0] == "INTERCO-001"


def test_transferencia_a_tercero_externo_requiere_revision():
    w = carga.leer_wallet(wallet([("08-09-2026 19:23", "SALIDA", 100, None,
                                   "SALIDA POR TRANSFERENCIA DE WALLET AL USUARIO alguien@gmail.com")], 1000), PARAMS)
    m = categorizar(w, CATALOGO, {**DS, "wallets_propias": []})
    assert m.requiere_revision.iloc[0] and m.tercero.iloc[0] == "alguien@gmail.com"


# ------------------------------------------------------------------ T1 ganancia


def test_ganancia_dropshipper_pagada_y_sin_pago():
    r = correr([orden(1, "ENTREGADO"), orden(2, "ENTREGADO", entregado="10/09/2026")], [gan_ds(1, 50000)])
    g = r.ganancia.estado.to_dict()
    assert g == {"1": "PAGADA", "2": "SIN_PAGO"}
    assert r.ganancia.loc["2", "gravedad"] == "CRITICO"
    assert r.ganancia.loc["2", "monto_en_juego_c"] == 5_000_000


def test_ganancia_en_ventana_no_es_hallazgo():
    r = correr([orden(1, "ENTREGADO", entregado="28/09/2026")], [gan_ds(9, 1.0, "29-09-2026 01:00")])
    assert r.ganancia.loc["1", "estado"] == "EN_VENTANA"


def test_ganancia_duplicada_y_diferencia():
    r = correr([orden(1, "ENTREGADO"), orden(2, "ENTREGADO")], [gan_ds(1, 50000), gan_ds(1, 50000), gan_ds(2, 40000)])
    assert r.ganancia.loc["1", "estado"] == "DUPLICADA"
    assert r.ganancia.loc["2", "estado"] == "DIFERENCIA_VALOR"
    assert r.ganancia.loc["2", "monto_en_juego_c"] == 1_000_000


def test_ganancia_sin_recaudo_no_aplica_para_dropshipper():
    r = correr([orden(1, "ENTREGADO", envio="SIN RECAUDO")], [gan_ds(9, 1.0)])
    assert r.ganancia.loc["1", "estado"] == "NO_APLICA"


def test_pago_de_orden_no_entregada_antes_y_despues_del_reporte():
    r = correr([orden(1, "EN REPARTO"), orden(2, "EN REPARTO")],
               [gan_ds(1, 50000, "20-09-2026 03:00"), gan_ds(2, 50000, "29-09-2026 03:00")])
    assert r.ganancia.loc["1", "estado"] == "PAGO_SIN_ENTREGA"
    assert r.ganancia.loc["2", "estado"] == "PAGO_POSTERIOR_AL_REPORTE"


def test_ganancia_reversada():
    r = correr([orden(1, "DEVOLUCION")], [gan_ds(1, 50000), ("22-09-2026 10:00", "SALIDA", 50000, 1,
                "SALIDA POR CORRECCION DE ESTADO DE GUIA COMO DROPSHIPPER. ORDEN ID: 1 GUIA: 1")])
    assert r.ganancia.loc["1", "estado"] == "REVERSADA"


def test_ganancia_proveedor_un_pago_por_linea():
    ords = [orden(1, "ENTREGADO", gan_prov=10000), orden(1, "ENTREGADO", gan_prov=20000), orden(2, "ENTREGADO", envio="SIN RECAUDO")]
    r = correr(ords, [gan_prov(1, 10000), gan_prov(1, 20000), gan_prov(2, 30000), ff(1, 1250), ff(1, 1250)], tienda=PROV)
    assert r.ganancia.estado.to_dict() == {"1": "PAGADA", "2": "PAGADA"}


# ------------------------------------------------------------ T2 sin recaudo


def test_sin_recaudo_cobro_y_reembolsos():
    ords = [orden(1, "ENTREGADO", envio="SIN RECAUDO"), orden(2, "CANCELADO", envio="SIN RECAUDO"),
            orden(3, "DEVOLUCION", envio="SIN RECAUDO")]
    movs = [("18-09-2026 09:00", "SALIDA", 45000, i, f"SALIDA POR NUEVA ORDEN: {i}") for i in (1, 2, 3)]
    movs += [("19-09-2026 09:00", "ENTRADA", 45000, 2, "ENTRADA POR CAMBIO DE ESTATUS: CANCELADO, EN LA ORDEN: 2")]
    r = correr(ords, movs)
    s = r.sin_recaudo
    assert set(s.estado_cobro) == {"COBRO_CORRECTO"}
    assert s.estado_reembolso.to_dict() == {"1": "NO_APLICA", "2": "REEMBOLSADO", "3": "SIN_REEMBOLSO"}
    assert s.loc["3", "monto_en_juego_c"] == 3_000_000  # devolución: se devuelve solo el producto
    assert s.loc["3", "gravedad"] == "CRITICO"


# ----------------------------------------------------- T3 devolución con recaudo


def test_devolucion_es_el_flete_sin_comision_de_recaudo():
    # flete 15.000, valor 100.000 → Wiilog 15.000 − 3 % = 12.000; Envía 15.000 − 4,5 % − 1.000 = 9.500
    ords = [orden(1, "DEVOLUCION", transp="INTERRAPIDISIMO", devolucion="15/09/2026"),
            orden(2, "DEVOLUCION", transp="WIILOG", devolucion="15/09/2026"),
            orden(3, "DEVOLUCION", transp="ENVIA", devolucion="15/09/2026"),
            orden(4, "DEVOLUCION", transp="ENVIA", devolucion="10/09/2026"),
            orden(5, "DEVOLUCION", transp="WIILOG", devolucion="15/09/2026"),
            orden(6, "DEVOLUCION", transp="COORDINADORA", devolucion="15/09/2026"),
            orden(7, "DEVOLUCION", transp="TCC", devolucion="15/09/2026")]
    movs = [("16-09-2026 09:00", "SALIDA", 15000, 1, "SALIDA POR COBRO DE FLETE INICIAL ORDEN 1"),
            ("16-09-2026 09:00", "SALIDA", 12000, 2, "SALIDA POR COBRO DE FLETE INICIAL ORDEN 2"),
            ("16-09-2026 09:00", "SALIDA", 9500, 3, "SALIDA DE COBRO DE DEVOLUCION POR ENTREGA NO EFECTIVA 3"),
            ("16-09-2026 09:00", "SALIDA", 13000, 5, "SALIDA POR COBRO DE FLETE INICIAL ORDEN 5"),
            ("16-09-2026 09:00", "SALIDA", 16000, 6, "SALIDA DE COBRO DE DEVOLUCION POR ENTREGA NO EFECTIVA 6"),
            ("16-09-2026 09:00", "SALIDA", 14000, 7, "SALIDA DE COBRO DE DEVOLUCION POR ENTREGA NO EFECTIVA 7")]
    r = correr(ords, movs)
    assert r.devoluciones.estado.to_dict() == {
        "1": "COBRADO", "2": "COBRADO", "3": "COBRADO", "4": "SIN_COBRO", "5": "DIFERENCIA_TARIFA",
        "6": "COBRO_MAYOR_AL_FLETE", "7": "COBRADO_SIN_TARIFA"}
    assert r.devoluciones.loc["6", "monto_en_juego_c"] == 100_000


def test_transferencia_a_cuenta_destino_del_grupo_se_categoriza_a_mano():
    w = carga.leer_wallet(wallet([("08-09-2026 19:23", "SALIDA", 100, None,
                                   "SALIDA POR TRANSFERENCIA DE WALLET AL USUARIO teampekop@gmail.com")], 1000), PARAMS)
    m = categorizar(w, CATALOGO, {**DS, "wallets_propias": [], "cuentas_destino_grupo": ["teampekop@gmail.com"]})
    assert m.tipo_tercero.iloc[0] == "CUENTA_DESTINO_GRUPO"
    assert m.ingreso_egreso.iloc[0] == "EGRESO" and m.requiere_revision.iloc[0] and m.categoria.isna().iloc[0]


# ----------------------------------------------------------- T4 fulfillment


def test_fulfillment_proveedor():
    ords = [orden(1, "ENTREGADO"), orden(2, "ENTREGADO"), orden(3, "CANCELADO"), orden(4, "ENTREGADO", envio="SIN RECAUDO"),
            orden(5, "PENDIENTE", guia=None), orden(6, "EN REPARTO", bodega="WIILOG BOGOTÁ 2.0"),
            orden(7, "EN REPARTO", bodega="PROVEEDOR EXTERNO")]
    movs = [ff(1), ff(2), ff(2, f="18-09-2026 11:00"), ff(4), ff(5, f="28-09-2026 15:00"), ff(6, 2000)]
    r = correr(ords, movs, tienda=PROV)
    assert r.fulfillment.estado.to_dict() == {
        "1": "COBRADO", "2": "DUPLICADO", "3": "NO_APLICA", "4": "COBRO_NO_CORRESPONDE",
        "5": "COBRO_POSTERIOR_AL_REPORTE", "6": "COBRADO_SIN_TARIFA", "7": "NO_APLICA"}
    assert r.fulfillment.loc["2", "monto_en_juego_c"] == 250_000


# ----------------------------------------------------------------- C0 y pagos


def test_c0_bloquea_si_el_saldo_no_cuadra():
    w = wallet([gan_ds(1, 100.0), gan_ds(2, 100.0)])
    w.loc[1, "MONTO PREVIO"] += 50
    r = conciliar_wallet_tienda(pd.DataFrame([orden(1, "ENTREGADO")]), w, PARAMS, CATALOGO, DS, "2026-09-21", "2026-09-21")
    assert r.bloqueado


def test_wallet_de_pagos_categoriza_pago_de_cliente():
    w = wallet([("09-09-2026 16:50", "ENTRADA", 3675392, None, "ENTRADA POR TRANSFERENCIA DE WALLET DESDE EL USUARIO cliente@gmail.com"),
                ("10-09-2026 10:00", "SALIDA", 3675392, None, "SALIDA POR PETICION DE RETIRO DE SALDO EN CARTERA")], email="pagos@x.co")
    r = conciliar_wallet_pagos(w, PAGOS, CATALOGO, {"usuario_email": "pagos@x.co", "empresa": None}, "2026-09-09", "2026-09-10")
    m = r.movimientos
    assert m.categoria.tolist()[0] == "PAGO DE CLIENTE POR WALLET"
    assert m.tercero.tolist()[0] == "cliente@gmail.com"
    assert r.resumen["sin_concepto"] == 0


def test_fuera_del_reporte_por_motivo():
    ords = [orden(100, "ENTREGADO"), orden(200, "ENTREGADO", prov="otro@x.co")]
    movs = [ff(50), ff(200), ff(150), ff(300, f="28-09-2026 16:00")]
    r = correr(ords, movs, tienda=PROV)
    motivo = r.fuera_del_reporte.set_index("orden_id").motivo.to_dict()
    assert motivo == {"50": "ORDEN_ANTERIOR_AL_REPORTE", "200": "ORDEN_DE_OTRA_TIENDA",
                      "150": "NO_ENCONTRADA", "300": "ORDEN_POSTERIOR_AL_REPORTE"}


def test_gravedad_fuera_del_reporte_posterior_no_es_hallazgo():
    ords = [orden(100, "ENTREGADO"), orden(200, "ENTREGADO", prov="otro@x.co")]
    movs = [ff(50), ff(200), ff(150), ff(300, f="28-09-2026 16:00")]
    r = correr(ords, movs, tienda=PROV)
    gravedad = r.fuera_del_reporte.set_index("orden_id").gravedad.to_dict()
    assert gravedad == {"50": "INFORMATIVO", "200": "MEDIO", "150": "MEDIO", "300": "OK"}


def test_reembolso_no_esperado_es_informativo():
    ords = [orden(1, "ENTREGADO", envio="SIN RECAUDO")]
    movs = [("18-09-2026 09:00", "SALIDA", 45000, 1, "SALIDA POR NUEVA ORDEN: 1"),
            ("19-09-2026 09:00", "ENTRADA", 45000, 1, "ENTRADA POR CAMBIO DE ESTATUS: CANCELADO, EN LA ORDEN: 1")]
    r = correr(ords, movs)
    assert r.sin_recaudo.loc["1", "estado_reembolso"] == "REEMBOLSO_NO_ESPERADO"
    assert r.sin_recaudo.loc["1", "gravedad"] == "INFORMATIVO"
