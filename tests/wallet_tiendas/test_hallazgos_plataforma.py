"""Qué se vuelve hallazgo en tiendas y pagos (PANTALLA_WALLETS.md §2.2). Datos sintéticos, sin base de datos."""
import pandas as pd

from app.motores.conciliacion_wallets.pagos import conciliar_wallet_pagos
from app.motores.conciliacion_wallets.plataforma.hallazgos import (
    hallazgos_pagos,
    hallazgos_tienda,
    resultado_c0,
)
from app.motores.conciliacion_wallets.tiendas import conciliar_wallet_tienda
from tests.wallet_tiendas.test_reglas_tiendas import (
    CATALOGO,
    DS,
    PAGOS,
    PARAMS,
    PROV,
    correr,
    ff,
    gan_ds,
    orden,
    wallet,
)


def _por_codigo(hallazgos):
    out = {}
    for h in hallazgos:
        out.setdefault(h.codigo, []).append(h)
    return out


def test_estados_ok_no_son_hallazgo_y_los_demas_llevan_su_gravedad():
    ords = [orden(1, "ENTREGADO"), orden(2, "ENTREGADO", entregado="10/09/2026"),
            orden(3, "ENTREGADO", entregado="28/09/2026"), orden(4, "ENTREGADO", gan_ds=0)]
    r = correr(ords, [gan_ds(1, 50000), gan_ds(4, 50000)])
    h = _por_codigo(hallazgos_tienda(r))
    # PAGADA, EN_VENTANA y PAGADA_SIN_VALIDAR no son hallazgo.
    assert [c for c in h if c.startswith("TIENDA_T1")] == ["TIENDA_T1_SIN_PAGO"]
    [sin_pago] = h["TIENDA_T1_SIN_PAGO"]
    assert sin_pago.gravedad == "CRITICO" and sin_pago.critico
    assert sin_pago.evidencia["orden_id"] == "2"
    assert sin_pago.evidencia["monto_en_juego"] == "50000.00"
    assert sin_pago.evidencia["esperado"] == "50000.00"


def test_sin_recaudo_lleva_el_estado_mas_grave_y_reembolso_no_esperado_es_informativo():
    ords = [orden(1, "DEVOLUCION", envio="SIN RECAUDO"), orden(2, "ENTREGADO", envio="SIN RECAUDO")]
    movs = [("18-09-2026 09:00", "SALIDA", 45000, i, f"SALIDA POR NUEVA ORDEN: {i}") for i in (1, 2)]
    movs += [("19-09-2026 09:00", "ENTRADA", 45000, 2, "ENTRADA POR CAMBIO DE ESTATUS: CANCELADO, EN LA ORDEN: 2")]
    h = _por_codigo(hallazgos_tienda(correr(ords, movs)))
    [sin_reembolso] = h["TIENDA_T2_SIN_REEMBOLSO"]
    assert sin_reembolso.gravedad == "CRITICO"
    assert sin_reembolso.evidencia["estado_cobro"] == "COBRO_CORRECTO"
    assert sin_reembolso.evidencia["monto_en_juego"] == "30000.00"
    [no_esperado] = h["TIENDA_T2_REEMBOLSO_NO_ESPERADO"]
    assert no_esperado.gravedad == "INFORMATIVO" and not no_esperado.critico


def test_fulfillment_sin_tarifa_y_posterior_al_reporte_no_son_hallazgo():
    ords = [orden(1, "ENTREGADO"), orden(2, "ENTREGADO"), orden(5, "PENDIENTE", guia=None),
            orden(6, "EN REPARTO", bodega="WIILOG BOGOTÁ 2.0")]
    movs = [ff(1), ff(2), ff(2, f="18-09-2026 11:00"), ff(5, f="28-09-2026 15:00"), ff(6, 2000)]
    h = _por_codigo(hallazgos_tienda(correr(ords, movs, tienda=PROV)))
    assert [c for c in h if c.startswith("TIENDA_T4")] == ["TIENDA_T4_DUPLICADO"]
    assert h["TIENDA_T4_DUPLICADO"][0].evidencia["tarifa"] == "2500.00"


def test_fuera_del_reporte_agrupa_anteriores_y_no_encontradas_y_omite_posteriores():
    ords = [orden(100, "ENTREGADO"), orden(200, "ENTREGADO", prov="otro@x.co")]
    movs = [ff(50), ff(60), ff(200), ff(150), ff(160), ff(300, f="28-09-2026 16:00")]
    h = _por_codigo(hallazgos_tienda(correr(ords, movs, tienda=PROV)))
    [anteriores] = h["TIENDA_FUERA_ORDEN_ANTERIOR_AL_REPORTE"]
    assert anteriores.gravedad == "INFORMATIVO"
    assert anteriores.descripcion == (
        "2 movimientos de órdenes anteriores al reporte: carga el reporte de órdenes del mes anterior."
    )
    assert anteriores.evidencia["por_concepto"] == {"COBRO_FULFILLMENT": {"movimientos": 2, "neto": "-5000.00"}}
    [no_encontradas] = h["TIENDA_FUERA_NO_ENCONTRADA"]
    assert no_encontradas.gravedad == "MEDIO"
    assert no_encontradas.evidencia["otros"]["ordenes"] == ["150", "160"]
    assert len(h["TIENDA_FUERA_ORDEN_DE_OTRA_TIENDA"]) == 1
    assert "TIENDA_FUERA_ORDEN_POSTERIOR_AL_REPORTE" not in h


def test_no_encontradas_separa_reembolsos_de_ordenes_reemplazadas():
    ords = [orden(100, "ENTREGADO"), orden(900, "ENTREGADO")]
    movs = [("18-09-2026 09:00", "SALIDA", 45000, 500, "SALIDA POR NUEVA ORDEN: 500"),
            ("19-09-2026 09:00", "ENTRADA", 45000, 500, "ENTRADA POR CAMBIO DE ESTATUS: REEMPLAZADA, EN LA ORDEN: 500"),
            ("19-09-2026 10:00", "ENTRADA", 20000, 600, "ENTRADA POR CAMBIO DE ESTATUS: CANCELADO, EN LA ORDEN: 600")]
    [h] = _por_codigo(hallazgos_tienda(correr(ords, movs)))["TIENDA_FUERA_NO_ENCONTRADA"]
    ev = h.evidencia
    assert ev["movimientos"] == 3
    assert ev["reemplazadas"] == {
        "nombre": "Reembolsos de órdenes reemplazadas", "movimientos": 1, "neto": "45000.00", "ordenes": ["500"]}
    assert ev["otros"]["movimientos"] == 2
    assert ev["otros"]["ordenes"] == ["500", "600"]
    assert ev["otros"]["por_concepto"] == {
        "COBRO_NUEVA_ORDEN": {"movimientos": 1, "neto": "-45000.00"},
        "REEMBOLSO_CAMBIO_ESTATUS": {"movimientos": 1, "neto": "20000.00"},
    }
    assert h.descripcion.startswith(
        "3 movimientos de órdenes que no están en el reporte: 1 reembolsos de órdenes reemplazadas"
    )


def test_movimiento_por_revisar_queda_como_revisar_movimiento():
    movs = [gan_ds(1, 50000), ("22-09-2026 10:00", "SALIDA", 1000, None,
                                "SALIDA POR TRANSFERENCIA DE WALLET AL USUARIO alguien@gmail.com")]
    [h] = _por_codigo(hallazgos_tienda(correr([orden(1, "ENTREGADO")], movs)))["TIENDA_MOVIMIENTO_REVISAR"]
    assert h.gravedad == "REVISAR" and not h.critico
    assert h.evidencia["tipo"] == "REVISAR_MOVIMIENTO"
    assert h.evidencia["tercero"] == "alguien@gmail.com"
    assert h.evidencia["monto"] == "-1000.00"


def test_c0_bloqueado_solo_guarda_el_c0():
    w = wallet([gan_ds(1, 100.0), gan_ds(2, 100.0)])
    w.loc[1, "MONTO PREVIO"] += 50
    r = conciliar_wallet_tienda(pd.DataFrame([orden(1, "ENTREGADO")]), w, PARAMS, CATALOGO, DS, "2026-09-21", "2026-09-21")
    [h] = hallazgos_tienda(r)
    assert h.codigo == "TIENDA_C0_SALDO" and h.gravedad == "CRITICO"
    c0 = resultado_c0(r.chequeos)
    assert c0["cuadra"] is False and c0["quiebres"] == 1


def test_pagos_guarda_c0_y_movimientos_por_revisar():
    w = wallet([("09-09-2026 16:50", "ENTRADA", 3675392, None, "ENTRADA POR TRANSFERENCIA DE WALLET DESDE EL USUARIO cliente@gmail.com"),
                ("10-09-2026 10:00", "SALIDA", 3675392, None, "SALIDA POR PETICION DE RETIRO DE SALDO EN CARTERA")], email="pagos@x.co")
    r = conciliar_wallet_pagos(w, PAGOS, CATALOGO, {"usuario_email": "pagos@x.co", "empresa": None}, "2026-09-09", "2026-09-10")
    c0 = resultado_c0(r.chequeos)
    assert c0["cuadra"] is True
    assert (c0["entradas"], c0["salidas"], c0["saldo_final"]) == ("3675392.00", "3675392.00", "0.00")
    codigos = {h.codigo for h in hallazgos_pagos(r)}
    assert codigos <= {"PAGOS_C0_COBERTURA", "PAGOS_MOVIMIENTO_REVISAR"}



def test_revisar_lleva_texto_de_dropi_entrada_salida_y_monto():
    texto = "SALIDA POR TRANSFERENCIA DE WALLET AL USUARIO alguien@gmail.com"
    movs = [gan_ds(1, 50000), ("22-09-2026 10:00", "SALIDA", 1000, None, texto)]
    [h] = _por_codigo(hallazgos_tienda(correr([orden(1, "ENTREGADO")], movs)))["TIENDA_MOVIMIENTO_REVISAR"]
    assert h.evidencia["texto_dropi"] == texto
    assert h.evidencia["entrada_salida"] == "SALIDA"
    assert h.evidencia["monto"] == "-1000.00"
    assert h.evidencia["texto_nuevo"] is False
    assert h.evidencia["ingreso_egreso"] == "EGRESO"


def test_texto_nuevo_de_dropi_llega_a_revisar_con_campos_vacios():
    movs = [gan_ds(1, 50000), ("22-09-2026 10:00", "ENTRADA", 700, None, "ENTRADA POR UN CONCEPTO QUE DROPI ACABA DE CREAR")]
    [h] = _por_codigo(hallazgos_tienda(correr([orden(1, "ENTREGADO")], movs)))["TIENDA_MOVIMIENTO_REVISAR"]
    assert h.evidencia["texto_nuevo"] is True
    assert h.evidencia["concepto"] == "SIN_CONCEPTO"
    assert (h.evidencia["ingreso_egreso"], h.evidencia["unidad_negocio"], h.evidencia["categoria"]) == (None, None, None)
    assert h.evidencia["entrada_salida"] == "ENTRADA"
