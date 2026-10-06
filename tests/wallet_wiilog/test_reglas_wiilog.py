"""Pruebas del motor de la wallet Wiilog con datos sintéticos. No necesitan base de datos ni archivos reales."""
import json
from pathlib import Path

import pandas as pd
import pytest

from app.motores.conciliacion_wallets.wiilog import conciliar_wallet_wiilog
from app.motores.conciliacion_wallets.wiilog import normalizar as n

PARAMS_TEXT = (
    Path(__file__).resolve().parents[2]
    / "docs/motores/conciliacion_wallets/parametros_wallet_wiilog.json"
).read_text(encoding="utf-8")
PARAMS = json.loads(
    PARAMS_TEXT.replace(
        "{{WIILOG_WALLET_PRINCIPAL_EMAIL}}",
        "wallet-principal@wiilog.test",
    )
)

COLS_O = [
    "ID", "NÚMERO GUIA", "ESTATUS", "TIPO DE ENVIO", "TRANSPORTADORA", "BODEGA", "ID DE BODEGA", "FECHA",
    "FECHA GENERACION DE GUIA", "FECHA ENTREGADO", "FECHA DEVOLUCION",
]


def orden(id_, estatus="ENTREGADO", envio="CON RECAUDO", transp="ENVIA", bodega="WIILOG BOGOTÁ", guia="10/09/2026",
          entregado=None, devolucion=None, lineas=1):
    fila = [id_, f"G{id_}", estatus, envio, transp, bodega, 1, "05-09-2026", guia, entregado, devolucion]
    return [fila] * lineas


class Wallet:
    """Arma una wallet con saldo continuo, como la exporta Dropi."""

    def __init__(self, saldo=0.0):
        self.saldo, self.filas, self.id = saldo, [], 1000

    def mov(self, tipo, monto, desc, orden_id=None, fecha="10-09-2026 10:00", actor=None):
        self.id += 1
        self.filas.append([self.id, fecha, tipo, monto, self.saldo, orden_id, None, desc, actor, None, None])
        self.saldo += monto if tipo == "ENTRADA" else -monto
        return self

    def df(self):
        return pd.DataFrame(self.filas, columns=["ID", "FECHA", "TIPO", "MONTO", "MONTO PREVIO", "ORDEN ID", "NUMERO DE GUIA",
                                                 "DESCRIPCIÓN", "USUARIO QUE REALIZA EL MOVIMIENTO", "CUENTA", "CONCEPTO DE RETIRO"])


def ff_gg(oid):
    return f"PAGO POR GANANCIA COMISION FULFILLMENT DE MARCA BLANCA. ORDEN ID *{oid}* GUIA: *G{oid}* CONCEPTO: GUIA_GENERADA"


def ff_cierre(oid):
    return f"PAGO POR GANANCIA COMISION FULFILLMENT DE MARCA BLANCA. ORDEN ID *{oid}* GUIA: *G{oid}* CONCEPTO: ENTREGADO"


def flete(oid):
    return f"PAGO POR GANANCIA FLETE DE MARCA BLANCA. ORDEN ID *{oid}* GUIA: *G{oid}* CONCEPTO: ENTREGADO"


def correr(ordenes_filas, wallet: Wallet):
    o = pd.DataFrame([f for grupo in ordenes_filas for f in grupo], columns=COLS_O)
    # Una última entrada con la fecha de corte del 28 de septiembre.
    wallet.mov("ENTRADA", 1000, flete(999999), orden_id=999999, fecha="28-09-2026 12:00")
    return conciliar_wallet_wiilog(o, wallet.df(), PARAMS, "2026-09-01", "2026-09-30")


def estado_ff(res, oid):
    return res.ff.loc[str(oid), "estado_ff"]


# ------------------------------------------------------------------ C0

def test_c0_bloquea_si_el_saldo_no_cuadra():
    w = Wallet().mov("ENTRADA", 2500, ff_gg(1), 1)
    w.filas[-1][4] = 999  # saldo previo alterado: archivo incompleto
    w.mov("ENTRADA", 2500, ff_gg(2), 2)
    res = correr([orden(1), orden(2)], w)
    assert res.bloqueado is True
    assert res.chequeos[0].codigo == "C0_SALDO"


def test_c0_ordena_por_id_y_no_por_fecha():
    w = Wallet().mov("ENTRADA", 2500, ff_gg(1), 1, fecha="10-09-2026 10:00").mov("ENTRADA", 2500, ff_gg(2), 2, fecha="10-09-2026 10:00")
    res = correr([orden(1), orden(2)], w)
    assert res.bloqueado is False


# ------------------------------------------------------------------ fulfillment

def test_ff_cobrado_una_vez():
    res = correr([orden(1)], Wallet().mov("ENTRADA", 2500, ff_gg(1), 1))
    assert estado_ff(res, 1) == "COBRADO"


def test_ff_agrupa_lineas_antes_de_cruzar():
    res = correr([orden(1, lineas=3)], Wallet().mov("ENTRADA", 2500, ff_gg(1), 1))
    assert estado_ff(res, 1) == "COBRADO"
    assert res.ff.loc["1", "lineas"] == 3


def test_ff_no_cobrado_con_guia_vieja():
    res = correr([orden(1, guia="10/09/2026")], Wallet())
    assert estado_ff(res, 1) == "NO_COBRADO"
    assert res.ff.loc["1", "monto_en_juego_c"] == n.centavos(2500)


def test_ff_en_ventana_con_guia_de_hoy_o_ayer():
    res = correr([orden(1, estatus="GUIA_GENERADA", guia="27/09/2026")], Wallet())
    assert estado_ff(res, 1) == "EN_VENTANA"


def test_ff_duplicado():
    w = Wallet().mov("ENTRADA", 2500, ff_gg(1), 1).mov("ENTRADA", 2500, ff_gg(1), 1)
    res = correr([orden(1)], w)
    assert estado_ff(res, 1) == "DUPLICADO"
    assert res.ff.loc["1", "monto_en_juego_c"] == n.centavos(2500)


def test_ff_diferencia_de_tarifa_en_bodega_con_tarifa_confirmada():
    res = correr([orden(1)], Wallet().mov("ENTRADA", 5000, ff_gg(1), 1))
    assert estado_ff(res, 1) == "DIFERENCIA_TARIFA"


def test_ff_tolera_centavos_de_redondeo():
    res = correr([orden(1)], Wallet().mov("ENTRADA", 2499.99, ff_gg(1), 1))
    assert estado_ff(res, 1) == "COBRADO"


def test_ff_bodega_externa_no_aplica():
    res = correr([orden(1, bodega="Bodega Asiati")], Wallet())
    assert estado_ff(res, 1) == "NO_APLICA"


def test_ff_bodega_con_tabulacion_se_normaliza():
    res = correr([orden(1, bodega="WIILOG MEDELLÍN\t 2.0")], Wallet())
    assert res.ff.loc["1", "bodega"] == "WIILOG MEDELLIN 2.0"
    assert estado_ff(res, 1) == "NO_COBRADO"


def test_ff_sin_recaudo_espera_el_cierre():
    res = correr([orden(1, estatus="EN REPARTO", envio="SIN RECAUDO")], Wallet())
    assert estado_ff(res, 1) == "PENDIENTE_CIERRE"


def test_ff_sin_recaudo_entregado_cobrado_al_cierre():
    res = correr([orden(1, envio="SIN RECAUDO", entregado="12/09/2026")], Wallet().mov("ENTRADA", 2500, ff_cierre(1), 1))
    assert estado_ff(res, 1) == "COBRADO"


def test_ff_sin_recaudo_devuelto_sin_cobro_es_hallazgo():
    res = correr([orden(1, estatus="DEVOLUCION", envio="SIN RECAUDO", devolucion="12/09/2026")], Wallet())
    assert estado_ff(res, 1) == "NO_COBRADO"


def test_ff_rechazado_y_reversado():
    w = Wallet().mov("ENTRADA", 2500, ff_gg(1), 1).mov("SALIDA", 2500, "CORRECCIÓN DE ENTRADA DE FULFILLMENT, ORDEN ID: 1", 1)
    res = correr([orden(1, estatus="RECHAZADO")], w)
    assert estado_ff(res, 1) == "REVERSADO"


def test_ff_cobro_sin_orden_en_el_reporte():
    res = correr([orden(1)], Wallet().mov("ENTRADA", 2500, ff_gg(1), 1).mov("ENTRADA", 2500, ff_gg(77), 77))
    assert "77" in res.ff_fuera.index


# ------------------------------------------------------------------ flete marca blanca

def test_flete_sin_columna_marca_blanca_queda_sin_verificar():
    res = correr([orden(1, entregado="12/09/2026")], Wallet().mov("ENTRADA", 2500, ff_gg(1), 1))
    assert res.flete.loc["1", "estado_flete"] == "SIN_VERIFICAR"


def test_flete_en_transportadora_wiilog_no_aplica():
    res = correr([orden(1, transp="WIILOG", entregado="12/09/2026")], Wallet().mov("ENTRADA", 2500, ff_gg(1), 1))
    assert res.flete.loc["1", "estado_flete"] == "NO_APLICA"


def test_flete_cobrado_en_transportadora_wiilog_es_hallazgo():
    w = Wallet().mov("ENTRADA", 2500, ff_gg(1), 1).mov("ENTRADA", 1000, flete(1), 1)
    res = correr([orden(1, transp="WIILOG", entregado="12/09/2026")], w)
    assert res.flete.loc["1", "estado_flete"] == "COBRADO_NO_CORRESPONDE"


def test_flete_cobrado():
    w = Wallet().mov("ENTRADA", 2500, ff_gg(1), 1).mov("ENTRADA", 1000, flete(1), 1)
    res = correr([orden(1, entregado="12/09/2026")], w)
    assert res.flete.loc["1", "estado_flete"] == "COBRADO"


# ------------------------------------------------------------------ movimientos

def test_transferencia_por_super_admin_queda_para_revisar_con_observacion():
    w = Wallet(5_000_000).mov("SALIDA", 800000, "SALIDA POR RECARGA DE SALDO EN CARTERA AL USUARIO alguien@gmail.com, POR SUPER ADMIN", fecha="21-09-2026 17:25")
    res = correr([orden(1)], w.mov("ENTRADA", 2500, ff_gg(1), 1))
    m = res.movimientos.set_index("mov_id").loc[1001]
    assert m.concepto == "TRANSFERENCIA_ENVIADA"
    assert m.estado_categoria == "REVISAR"
    assert bool(m.requiere_observacion) is True
    assert m.tercero == "alguien@gmail.com"


def test_traslado_a_wallet_wiilog_es_automatico():
    w = Wallet(5_000_000).mov("SALIDA", 1_000_000, "SALIDA POR RECARGA DE SALDO EN CARTERA AL USUARIO wallet-principal@wiilog.test, POR SUPER ADMIN")
    res = correr([orden(1)], w.mov("ENTRADA", 2500, ff_gg(1), 1))
    m = res.movimientos.set_index("mov_id").loc[1001]
    assert m.concepto == "TRASLADO_WALLET_WIILOG"
    assert m.estado_categoria == "AUTO"


def test_cruce_de_cartera_se_empareja_y_queda_neto_cero():
    w = (Wallet(1_000_000)
         .mov("ENTRADA", 87228, "ENTRADA POR RECARGA CRUZADA DE MARCA BLANCA PARA EL USUARIO x@gmail.com, DESDE WALLET DEL OWNER DE DROPI", fecha="09-09-2026 15:53")
         .mov("SALIDA", 87228, "SALIDA POR RECARGA DE SALDO EN CARTERA AL USUARIO x@gmail.com, POR SUPER ADMIN", fecha="09-09-2026 15:53"))
    res = correr([orden(1)], w.mov("ENTRADA", 2500, ff_gg(1), 1))
    cruce = res.movimientos[res.movimientos.cruce_id.notna()]
    assert len(cruce) == 2
    assert set(cruce.flujo) == {"NETO_CERO"}


# ------------------------------------------------------------------ parámetros v2 (28-sep-2026)

def test_v2_bucaramanga_no_cobra_ff():
    res = correr([orden(1, bodega="WIILOG BUCARAMANGA")], Wallet())
    assert estado_ff(res, 1) == "NO_APLICA"


def test_v2_cobro_en_bucaramanga_no_corresponde():
    res = correr([orden(1, bodega="WIILOG BUCARAMANGA")], Wallet().mov("ENTRADA", 2500, ff_gg(1), 1))
    assert estado_ff(res, 1) == "COBRADO_NO_CORRESPONDE"
    assert res.ff.loc["1", "monto_en_juego_c"] == n.centavos(2500)


def test_v2_bogota_3_0_tarifa_3250():
    res = correr([orden(1, bodega="WIILOG BOGOTÁ 3.0")], Wallet().mov("ENTRADA", 3250, ff_gg(1), 1))
    assert estado_ff(res, 1) == "COBRADO"


def test_v2_bogota_3_0_cobrado_a_2500_es_diferencia():
    res = correr([orden(1, bodega="WIILOG BOGOTÁ 3.0")], Wallet().mov("ENTRADA", 2500, ff_gg(1), 1))
    assert estado_ff(res, 1) == "DIFERENCIA_TARIFA"


def test_v2_bodega_con_tarifa_por_confirmar_acepta_el_cobro():
    res = correr([orden(1, bodega="WIILOG BOGOTÁ 2.0")], Wallet().mov("ENTRADA", 4000, ff_gg(1), 1))
    assert estado_ff(res, 1) == "COBRADO"
    assert bool(res.ff.loc["1", "tarifa_confirmada"]) is False



# ------------------------------------------------------------------ catálogo común (Juan Felipe, 6-oct)

CATALOGO_TEXT = (
    Path(__file__).resolve().parents[2]
    / "docs/motores/conciliacion_wallets/catalogo_conceptos_wallets.json"
).read_text(encoding="utf-8")
CATALOGO = json.loads(CATALOGO_TEXT.replace("{{WIILOG_WALLET_PRINCIPAL_EMAIL}}", "wallet-principal@wiilog.test"))


def correr_con_catalogo(ordenes_filas, wallet: Wallet):
    o = pd.DataFrame([f for grupo in ordenes_filas for f in grupo], columns=COLS_O)
    wallet.mov("ENTRADA", 1000, flete(999999), orden_id=999999, fecha="28-09-2026 12:00")
    return conciliar_wallet_wiilog(o, wallet.df(), PARAMS, "2026-09-01", "2026-09-30", catalogo=CATALOGO)


def _dimensiones(res, mov_id):
    m = res.movimientos.set_index("mov_id").loc[mov_id]
    return (m.ingreso_egreso, m.unidad_negocio, m.categoria)


def test_cada_concepto_de_wiilog_apunta_a_una_fila_del_catalogo_comun():
    comunes = {c["codigo"] for c in CATALOGO["conceptos"]}
    propios = {r["codigo"] for r in PARAMS["conceptos_wallet"]}
    mapa = PARAMS["concepto_catalogo_comun"]
    assert propios == set(mapa)
    assert set(mapa.values()) <= comunes


def test_ff_y_flete_de_wiilog_toman_dimensiones_del_catalogo_comun():
    w = Wallet().mov("ENTRADA", 2500, ff_gg(1), 1).mov("ENTRADA", 1000, flete(1), 1)
    w.mov("SALIDA", 2500, "CORRECCION DE ENTRADA DE FULFILLMENT. ORDEN ID *1*", 1)
    res = correr_con_catalogo([orden(1, entregado="12/09/2026")], w)
    assert _dimensiones(res, 1001) == ("INGRESO", "FF", "FF")
    assert _dimensiones(res, 1002) == ("INGRESO", "FF", "COMISIONES")
    assert _dimensiones(res, 1003) == ("EGRESO", "FF", "FF")


def test_traslado_a_wallet_principal_es_traslado_ff_retiro():
    w = Wallet(5_000_000).mov("SALIDA", 1_000_000, "SALIDA POR RECARGA DE SALDO EN CARTERA AL USUARIO wallet-principal@wiilog.test, POR SUPER ADMIN")
    res = correr_con_catalogo([orden(1)], w.mov("ENTRADA", 2500, ff_gg(1), 1))
    assert _dimensiones(res, 1001) == ("TRASLADO", "FF", "RETIRO")


def test_retiro_bancario_de_wiilog_queda_sin_unidad_y_para_revisar():
    w = Wallet(5_000_000)
    w.mov("SALIDA", 1_000_000, "RETIRO DE SALDO")
    w.filas[-1][9] = "CUENTA BANCARIA"
    res = correr_con_catalogo([orden(1)], w.mov("ENTRADA", 2500, ff_gg(1), 1))
    m = res.movimientos.set_index("mov_id").loc[1001]
    assert m.concepto == "RETIRO_BANCARIO"
    assert m.unidad_negocio is None
    assert m.estado_categoria == "REVISAR"


def test_texto_nuevo_en_wiilog_queda_sin_dimensiones():
    w = Wallet(5_000).mov("ENTRADA", 700, "ENTRADA POR UN CONCEPTO QUE DROPI ACABA DE CREAR")
    res = correr_con_catalogo([orden(1)], w.mov("ENTRADA", 2500, ff_gg(1), 1))
    m = res.movimientos.set_index("mov_id").loc[1001]
    assert m.concepto == "SIN_CONCEPTO"
    assert _dimensiones(res, 1001) == (None, None, None)
