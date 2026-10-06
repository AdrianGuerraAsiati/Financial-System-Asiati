"""Listas de categorización administrables (decisión 0008): el coordinador las administra, el conciliador elige."""
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import Auditoria
from app.core.dimensiones import DimensionValor, cargar_valores_iniciales
from app.core.empresas import Empresa
from app.core.hallazgos import Hallazgo
from app.core.usuarios import ROL_CONCILIACION, ROL_COORDINACION_FINANCIERA, ROL_TI
from tests.apoyo_auth import (
    SECRETO_PRUEBA,
    cliente_con_rol,
    crear_empresa,
    crear_hallazgo,
    crear_periodo,
    engine,
)


@pytest.fixture(autouse=True)
def entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", SECRETO_PRUEBA)


def _unico(base: str) -> str:
    return f"{base} {uuid.uuid4().hex[:6].upper()}"


def _coordinador(empresa_id: int | None = None):
    empresas = (empresa_id,) if empresa_id else ()
    return cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=empresas)[0]


def _crear(client, dimension: str, valor: str):
    return client.post("/api/v1/dimensiones", json={"dimension": dimension, "valor": valor})


def _sembrar(**valores: list[str]) -> None:
    with Session(engine()) as session:
        cargar_valores_iniciales(session, valores)
        session.commit()


def test_coordinador_agrega_un_valor_y_queda_en_auditoria() -> None:
    client = _coordinador()
    valor = _unico("Mensajería")

    respuesta = _crear(client, "categoria", valor)

    assert respuesta.status_code == 201, respuesta.text
    creado = respuesta.json()
    assert (creado["dimension"], creado["valor"], creado["activo"]) == ("categoria", valor, True)
    with Session(engine()) as session:
        accion = session.scalar(
            select(Auditoria.accion).where(Auditoria.entidad == "dimension_valor", Auditoria.entidad_id == creado["id"])
        )
    assert accion == "dimension.crear"


@pytest.mark.parametrize("rol", [ROL_CONCILIACION, ROL_TI])
def test_conciliador_y_ti_no_administran_las_listas(rol: str) -> None:
    client = cliente_con_rol(rol)[0]
    assert _crear(client, "categoria", _unico("X")).status_code == 403


def test_no_se_repite_un_valor_aunque_cambien_tildes_mayusculas_o_espacios() -> None:
    client = _coordinador()
    valor = _unico("Consultoría Externa")
    assert _crear(client, "categoria", valor).status_code == 201

    repetido = _crear(client, "categoria", "  " + valor.upper().replace("Í", "I") + " ")

    assert repetido.status_code == 409
    assert "ya existe" in repetido.json()["detail"].lower()


def test_dimension_desconocida_se_rechaza() -> None:
    respuesta = _crear(_coordinador(), "color", "Rojo")
    assert respuesta.status_code == 422


def test_renombrar_y_desactivar_nunca_borra() -> None:
    client = _coordinador()
    creado = _crear(client, "unidad_negocio", _unico("Bodega")).json()
    nuevo_nombre = _unico("Bodega Norte")

    renombrado = client.patch(f"/api/v1/dimensiones/{creado['id']}", json={"valor": nuevo_nombre})
    desactivado = client.patch(f"/api/v1/dimensiones/{creado['id']}", json={"activo": False})

    assert renombrado.json()["valor"] == nuevo_nombre
    assert desactivado.json()["activo"] is False
    activos = client.get("/api/v1/dimensiones", params={"dimension": "unidad_negocio"}).json()
    todos = client.get(
        "/api/v1/dimensiones", params={"dimension": "unidad_negocio", "incluir_inactivos": True}
    ).json()
    assert creado["id"] not in {v["id"] for v in activos}
    assert creado["id"] in {v["id"] for v in todos}
    assert client.delete(f"/api/v1/dimensiones/{creado['id']}").status_code == 405


def test_el_conciliador_lee_las_listas() -> None:
    _sembrar(fijo_variable=["FIJO", "VARIABLE"])
    client = cliente_con_rol(ROL_CONCILIACION)[0]

    respuesta = client.get("/api/v1/dimensiones", params={"dimension": "fijo_variable"})

    assert respuesta.status_code == 200
    assert {"FIJO", "VARIABLE"} <= {v["valor"] for v in respuesta.json()}


def test_carga_inicial_es_idempotente() -> None:
    valores = {"categoria": [_unico("Inicial A"), _unico("Inicial B")]}
    with Session(engine()) as session:
        primera = cargar_valores_iniciales(session, valores)
        segunda = cargar_valores_iniciales(session, valores)
        session.commit()
    assert (primera.creados, primera.existentes) == (2, 0)
    assert (segunda.creados, segunda.existentes) == (0, 2)


# ------------------------------------------------------------------ categorizar al observar


def _contexto_categorizacion() -> dict:
    sufijo = uuid.uuid4().hex[:6].upper()
    empresa_id = crear_empresa(f"EMPRESA {sufijo}")
    with Session(engine()) as session:
        empresa_nombre = session.get(Empresa, empresa_id).nombre
    otra_empresa = f"OTRA EMPRESA {sufijo}"
    valores = {
        "ingreso_egreso": ["EGRESO"],
        "unidad_negocio": [f"FF {sufijo}"],
        "categoria": [f"RETIRO {sufijo}"],
        "empresa": [empresa_nombre, otra_empresa],
        "fijo_variable": ["VARIABLE"],
    }
    _sembrar(**valores)
    hallazgo_id = crear_hallazgo(crear_periodo(empresa_id))
    client = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa_id,))[0]
    categorizacion = {
        "ingreso_egreso": "EGRESO",
        "unidad_negocio": f"ff {sufijo}",
        "categoria": f"Retiro {sufijo}",
        "empresa": empresa_nombre,
        "fijo_variable": "VARIABLE",
        "modalidad": "WALLET",
        "tercero": "  Proveedor de tiquetes ",
    }
    return {
        "client": client,
        "hallazgo_id": hallazgo_id,
        "categorizacion": categorizacion,
        "sufijo": sufijo,
        "otra_empresa": otra_empresa,
    }


def _observar(ctx: dict, categorizacion: dict, resolver: bool = False):
    return ctx["client"].post(
        f"/api/v1/hallazgos/{ctx['hallazgo_id']}/observar",
        json={"observacion": "Retiro para pago de tiquetes.", "resolver": resolver, "categorizacion": categorizacion},
    )


def test_observar_guarda_la_categorizacion_como_dato_con_los_valores_de_la_lista() -> None:
    ctx = _contexto_categorizacion()

    respuesta = _observar(ctx, ctx["categorizacion"], resolver=True)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "resuelto"
    with Session(engine()) as session:
        guardada = session.get(Hallazgo, ctx["hallazgo_id"]).evidencia["categorizacion"]
        accion = session.scalars(
            select(Auditoria).where(Auditoria.entidad == "hallazgo", Auditoria.entidad_id == ctx["hallazgo_id"])
        ).all()[-1]
    # Se guarda el valor tal como está en la lista, no como lo escribió el navegador.
    assert guardada["unidad_negocio"] == f"FF {ctx['sufijo']}"
    assert guardada["categoria"] == f"RETIRO {ctx['sufijo']}"
    assert guardada["tercero"] == "Proveedor de tiquetes"
    assert guardada["modalidad"] == "WALLET"
    assert set(guardada["valor_ids"]) == {"ingreso_egreso", "unidad_negocio", "categoria", "empresa", "fijo_variable"}
    assert accion.despues["categorizacion"]["categoria"] == f"RETIRO {ctx['sufijo']}"


def test_empresa_de_la_categorizacion_no_se_puede_cambiar() -> None:
    ctx = _contexto_categorizacion()

    respuesta = _observar(
        ctx,
        {**ctx["categorizacion"], "empresa": ctx["otra_empresa"]},
    )

    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"].lower()
    assert "sale de la wallet" in detalle and "no se edita" in detalle


def test_valor_fuera_de_la_lista_se_rechaza_y_sugiere_escalar() -> None:
    ctx = _contexto_categorizacion()

    respuesta = _observar(ctx, {**ctx["categorizacion"], "categoria": "INVENTADA"})

    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert "INVENTADA" in detalle and "escala al coordinador" in detalle.lower()
    with Session(engine()) as session:
        assert session.get(Hallazgo, ctx["hallazgo_id"]).estado == "detectado"


def test_valor_desactivado_ya_no_se_puede_elegir() -> None:
    ctx = _contexto_categorizacion()
    with Session(engine()) as session:
        valor = session.scalar(
            select(DimensionValor).where(DimensionValor.valor == f"RETIRO {ctx['sufijo']}")
        )
        valor.activo = False
        session.commit()

    assert _observar(ctx, ctx["categorizacion"]).status_code == 422


def test_faltan_dimensiones_o_modalidad_distinta_se_rechazan() -> None:
    ctx = _contexto_categorizacion()
    sin_unidad = {k: v for k, v in ctx["categorizacion"].items() if k != "unidad_negocio"}

    assert _observar(ctx, sin_unidad).status_code == 422
    assert _observar(ctx, {**ctx["categorizacion"], "modalidad": "BANCO"}).status_code == 422


def test_tercero_es_el_unico_campo_libre_y_puede_ir_vacio() -> None:
    ctx = _contexto_categorizacion()
    respuesta = _observar(ctx, {**ctx["categorizacion"], "tercero": ""})
    assert respuesta.status_code == 200, respuesta.text
