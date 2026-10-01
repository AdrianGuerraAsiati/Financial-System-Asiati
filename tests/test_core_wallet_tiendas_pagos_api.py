"""Tiendas y pagos conectados a la plataforma (PANTALLA_WALLETS.md §2). Datos sintéticos, con Postgres."""
import copy
import io
import uuid
from datetime import date

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.core.fuentes import Fuente
from app.core.periodos import Periodo
from app.core.usuarios import ROL_CONCILIACION, ROL_COORDINACION_FINANCIERA, ROL_TI
from app.motores.conciliacion_wallets.plataforma import integracion
from tests.apoyo_auth import SECRETO_PRUEBA, cliente_con_rol, engine
from tests.wallet_tiendas.test_reglas_tiendas import PAGOS, PARAMS, gan_ds, orden, wallet

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(autouse=True)
def entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", SECRETO_PRUEBA)


def _xlsx(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    return buffer.getvalue()


def _contexto(monkeypatch: pytest.MonkeyPatch, *, cerrado: bool = False) -> dict:
    """Empresa con nombre único, período de septiembre, dos fuentes y parámetros que apuntan a esa empresa."""
    nombre = f"TIENDAS PRUEBA {uuid.uuid4().hex[:6]}"
    with Session(engine()) as session:
        empresa = Empresa(nombre=nombre)
        session.add(empresa)
        session.flush()
        periodo = Periodo(
            empresa_id=empresa.id, fecha_inicio=date(2026, 9, 18), fecha_fin=date(2026, 9, 30), cerrado=cerrado
        )
        otro_periodo = Periodo(empresa_id=empresa.id, fecha_inicio=date(2026, 10, 1), fecha_fin=date(2026, 10, 31))
        fuente_wallet = Fuente(empresa_id=empresa.id, nombre="Wallet tienda")
        fuente_ordenes = Fuente(empresa_id=empresa.id, nombre="Órdenes Dropi")
        session.add_all([periodo, otro_periodo, fuente_wallet, fuente_ordenes])
        session.commit()
        ctx = {
            "empresa_id": empresa.id,
            "periodo_id": periodo.id,
            "otro_periodo_id": otro_periodo.id,
            "fuente_wallet_id": fuente_wallet.id,
            "fuente_ordenes_id": fuente_ordenes.id,
        }

    tiendas = copy.deepcopy(PARAMS)
    tiendas["tiendas"] = [
        {"usuario_email": "tienda@x.co", "nombre": "Tienda", "rol": "DROPSHIPPER", "empresa": nombre},
        {"usuario_email": "otra@x.co", "nombre": "Otra tienda", "rol": "DROPSHIPPER", "empresa": nombre},
        {"usuario_email": "ajena@x.co", "nombre": "Tienda ajena", "rol": "DROPSHIPPER", "empresa": "OTRA EMPRESA"},
    ]
    pagos = copy.deepcopy(PAGOS)
    pagos["wallets"] = [{"usuario_email": "pagos@x.co", "nombre": "Pagos", "empresa": nombre}]
    monkeypatch.setattr(integracion, "cargar_parametros_tienda", lambda: tiendas)
    monkeypatch.setattr(integracion, "cargar_parametros_pagos", lambda: pagos)
    return ctx


ORDENES = _xlsx(pd.DataFrame([orden(1, "ENTREGADO"), orden(2, "ENTREGADO", entregado="10/09/2026")]))


def _wallet(*extra) -> bytes:
    return _xlsx(wallet([gan_ds(1, 50000), *extra], 1_000_000))


def _conciliar_tienda(client, ctx, *, tienda="tienda@x.co", wallet_bytes=None, ordenes=ORDENES,
                      nombre_ordenes="ordenes.xlsx", periodo_id=None, corte=None):
    data = {
        "empresa_id": str(ctx["empresa_id"]),
        "periodo_id": str(periodo_id or ctx["periodo_id"]),
        "tienda": tienda,
        "fuente_wallet_id": str(ctx["fuente_wallet_id"]),
        "fuente_ordenes_id": str(ctx["fuente_ordenes_id"]),
    }
    if corte:
        data["corte_ordenes"] = corte
    files = {
        "wallet": ("wallet.xlsx", wallet_bytes or _wallet(), XLSX),
        "ordenes": (nombre_ordenes, ordenes, XLSX),
    }
    return client.post("/api/v1/wallets/tiendas/conciliar", data=data, files=files)


def _conciliador(ctx):
    return cliente_con_rol(ROL_CONCILIACION, empresas=(ctx["empresa_id"],))[0]


def _hallazgos(client, ctx, ruta="tiendas", **params):
    return client.get(
        f"/api/v1/wallets/{ruta}/hallazgos",
        params={"empresa_id": ctx["empresa_id"], "periodo_id": ctx["periodo_id"], **params},
    )


def test_conciliar_tienda_devuelve_c0_y_guarda_hallazgos_con_gravedad(monkeypatch) -> None:
    ctx = _contexto(monkeypatch)
    client = _conciliador(ctx)

    respuesta = _conciliar_tienda(client, ctx)

    assert respuesta.status_code == 201, respuesta.text
    body = respuesta.json()
    assert body["bloqueado"] is False
    assert body["c0"]["cuadra"] is True
    assert body["c0"]["saldo_inicial"] == "1000000.00"
    assert body["c0"]["saldo_final"] == "1050000.00"
    assert body["hallazgos_por_gravedad"]["CRITICO"] == 1
    assert body["resumen"]["ganancia_por_estado"]["PAGADA"]["ordenes"] == 1

    items = _hallazgos(client, ctx).json()
    [sin_pago] = [h for h in items if h["codigo_regla"] == "TIENDA_T1_SIN_PAGO"]
    assert sin_pago["gravedad"] == "CRITICO"
    assert sin_pago["critico"] is True
    assert sin_pago["estado"] == "detectado"
    assert sin_pago["evidencia"]["wallet"] == "tienda@x.co"
    assert sin_pago["evidencia"]["tipo_wallet"] == "TIENDA"
    assert sin_pago["evidencia"]["carga_wallet_id"] == body["cargas"]["wallet_id"]
    assert sin_pago["evidencia"]["monto_en_juego"] == "50000.00"


def test_c0_que_no_cuadra_no_guarda_otros_hallazgos(monkeypatch) -> None:
    ctx = _contexto(monkeypatch)
    roto = wallet([gan_ds(1, 50000), gan_ds(2, 50000)], 1_000_000)
    roto.loc[1, "MONTO PREVIO"] += 50

    respuesta = _conciliar_tienda(_conciliador(ctx), ctx, wallet_bytes=_xlsx(roto))

    assert respuesta.status_code == 201, respuesta.text
    body = respuesta.json()
    assert body["bloqueado"] is True
    assert body["c0"]["cuadra"] is False
    assert "descárgalo de nuevo" in body["c0"]["mensaje"]
    assert body["hallazgos_por_gravedad"]["CRITICO"] == 1
    codigos = {h["codigo_regla"] for h in _hallazgos(_conciliador(ctx), ctx).json()}
    assert codigos <= {"TIENDA_C0_SALDO", "TIENDA_C0_COBERTURA"}


def test_tienda_de_otra_empresa_es_rechazada(monkeypatch) -> None:
    ctx = _contexto(monkeypatch)

    respuesta = _conciliar_tienda(_conciliador(ctx), ctx, tienda="ajena@x.co")

    assert respuesta.status_code == 422
    assert "Cambia la empresa" in respuesta.json()["detail"]


def test_reporte_de_ordenes_compartido_se_reutiliza_en_el_mismo_periodo(monkeypatch) -> None:
    ctx = _contexto(monkeypatch)
    client = _conciliador(ctx)

    primera = _conciliar_tienda(client, ctx)
    segunda = _conciliar_tienda(client, ctx, tienda="otra@x.co", wallet_bytes=_wallet(gan_ds(2, 1.0)))

    assert primera.status_code == 201, primera.text
    assert segunda.status_code == 201, segunda.text
    assert segunda.json()["cargas"]["ordenes_reutilizadas"] is True
    assert segunda.json()["cargas"]["ordenes_id"] == primera.json()["cargas"]["ordenes_id"]


def test_mismo_reporte_de_ordenes_en_otro_periodo_es_duplicado(monkeypatch) -> None:
    ctx = _contexto(monkeypatch)
    client = _conciliador(ctx)
    assert _conciliar_tienda(client, ctx).status_code == 201

    respuesta = _conciliar_tienda(
        client, ctx, wallet_bytes=_wallet(gan_ds(2, 1.0)), periodo_id=ctx["otro_periodo_id"]
    )

    assert respuesta.status_code == 409
    assert "otro período" in respuesta.json()["detail"]


def test_wallet_repetida_es_duplicada(monkeypatch) -> None:
    ctx = _contexto(monkeypatch)
    client = _conciliador(ctx)
    # El mismo archivo dos veces (cada _xlsx() nuevo cambia de hash por la fecha de creación).
    archivo = _wallet()
    assert _conciliar_tienda(client, ctx, wallet_bytes=archivo).status_code == 201

    respuesta = _conciliar_tienda(client, ctx, wallet_bytes=archivo)

    assert respuesta.status_code == 409
    assert "ya fue cargado" in respuesta.json()["detail"]


def test_periodo_cerrado_no_se_concilia(monkeypatch) -> None:
    ctx = _contexto(monkeypatch, cerrado=True)

    respuesta = _conciliar_tienda(_conciliador(ctx), ctx)

    assert respuesta.status_code == 409
    assert "Reábrelo" in respuesta.json()["detail"]


def test_bandeja_muestra_por_defecto_la_ultima_carga_de_cada_wallet(monkeypatch) -> None:
    ctx = _contexto(monkeypatch)
    client = _conciliador(ctx)
    primera = _conciliar_tienda(client, ctx).json()
    segunda = _conciliar_tienda(client, ctx, wallet_bytes=_wallet(gan_ds(2, 50000, "21-09-2026 04:00"))).json()

    ultima = _hallazgos(client, ctx).json()
    todas = _hallazgos(client, ctx, todas_las_cargas="true").json()

    assert {h["evidencia"]["carga_wallet_id"] for h in ultima} == {segunda["cargas"]["wallet_id"]}
    assert {h["evidencia"]["carga_wallet_id"] for h in todas} == {
        primera["cargas"]["wallet_id"], segunda["cargas"]["wallet_id"]
    }
    # En la segunda carga la orden 2 ya está pagada.
    assert "TIENDA_T1_SIN_PAGO" not in {h["codigo_regla"] for h in ultima}


def test_hora_de_descarga_sale_del_nombre_del_archivo_o_del_formulario(monkeypatch) -> None:
    ctx = _contexto(monkeypatch)
    client = _conciliador(ctx)

    del_nombre = _conciliar_tienda(client, ctx, nombre_ordenes="ordenes_sept_20260928_144134.xlsx")
    escrita = _conciliar_tienda(
        client, ctx, tienda="otra@x.co", wallet_bytes=_wallet(gan_ds(2, 1.0)), corte="2026-09-27 10:00"
    )
    invalida = _conciliar_tienda(client, ctx, wallet_bytes=_wallet(gan_ds(3, 1.0)), corte="ayer")

    assert del_nombre.json()["resumen"]["corte_reporte_ordenes"] == "2026-09-28 14:41:34"
    assert escrita.json()["resumen"]["corte_reporte_ordenes"] == "2026-09-27 10:00:00"
    assert invalida.status_code == 422
    assert "AAAA-MM-DD HH:MM" in invalida.json()["detail"]


def test_conciliar_pagos_guarda_solo_hallazgos_de_pagos(monkeypatch) -> None:
    ctx = _contexto(monkeypatch)
    client = _conciliador(ctx)
    archivo = _xlsx(wallet([
        ("18-09-2026 16:50", "ENTRADA", 3675392, None, "ENTRADA POR TRANSFERENCIA DE WALLET DESDE EL USUARIO cliente@gmail.com"),
        ("19-09-2026 10:00", "SALIDA", 1000, None, "SALIDA POR TRANSFERENCIA DE WALLET AL USUARIO alguien@gmail.com"),
    ], email="pagos@x.co"))

    respuesta = client.post(
        "/api/v1/wallets/pagos/conciliar",
        data={
            "empresa_id": str(ctx["empresa_id"]),
            "periodo_id": str(ctx["periodo_id"]),
            "wallet_pagos": "pagos@x.co",
            "fuente_wallet_id": str(ctx["fuente_wallet_id"]),
        },
        files={"wallet": ("wallet_pagos.xlsx", archivo, XLSX)},
    )

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["c0"]["cuadra"] is True
    assert respuesta.json()["cargas"]["ordenes_id"] is None
    items = _hallazgos(client, ctx, ruta="pagos").json()
    assert items and all(h["codigo_regla"].startswith("PAGOS_") for h in items)
    revisar = [h for h in items if h["codigo_regla"] == "PAGOS_MOVIMIENTO_REVISAR"]
    assert {h["evidencia"]["tercero"] for h in revisar} == {"cliente@gmail.com", "alguien@gmail.com"}
    assert all(h["gravedad"] == "REVISAR" and h["evidencia"]["tipo"] == "REVISAR_MOVIMIENTO" for h in revisar)
    assert _hallazgos(client, ctx).json() == []


def test_catalogo_lista_solo_las_wallets_de_la_empresa(monkeypatch) -> None:
    ctx = _contexto(monkeypatch)

    respuesta = _conciliador(ctx).get("/api/v1/wallets/catalogo", params={"empresa_id": ctx["empresa_id"]})

    assert respuesta.status_code == 200
    body = respuesta.json()
    assert body["wiilog"] is False
    assert [t["usuario_email"] for t in body["tiendas"]] == ["tienda@x.co", "otra@x.co"]
    assert [w["usuario_email"] for w in body["pagos"]] == ["pagos@x.co"]


@pytest.mark.parametrize("rol", [ROL_COORDINACION_FINANCIERA, ROL_TI])
def test_coordinador_y_ti_no_concilian_pero_si_ven(monkeypatch, rol: str) -> None:
    ctx = _contexto(monkeypatch)
    client = cliente_con_rol(rol, empresas=(ctx["empresa_id"],))[0]

    conciliar = _conciliar_tienda(client, ctx)
    ver = _hallazgos(client, ctx)

    assert conciliar.status_code == 403
    assert ver.status_code == 200


def test_empresa_no_asignada_no_existe_para_el_conciliador(monkeypatch) -> None:
    ctx = _contexto(monkeypatch)
    otra = _contexto(monkeypatch)
    client = _conciliador(otra)

    conciliar = _conciliar_tienda(client, ctx)
    ver = _hallazgos(client, ctx)
    catalogo = client.get("/api/v1/wallets/catalogo", params={"empresa_id": ctx["empresa_id"]})

    assert conciliar.status_code == 404
    assert ver.status_code == 404
    assert catalogo.status_code == 404
