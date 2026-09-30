from datetime import date
from decimal import Decimal
import hashlib
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import Auditoria
from app.core.cargas import Carga
from app.core.fuentes import Fuente
from app.core.movimientos import Movimiento, ReglaCategorizacion, normalizar_descripcion
from app.core.periodos import Periodo
from app.core.usuarios.roles import (
    ROL_CONCILIACION,
    ROL_SUPER_ADMINISTRADOR,
    ROL_TI,
)
from tests.apoyo_auth import (
    SECRETO_PRUEBA,
    cliente_con_rol,
    crear_empresa,
    engine,
)


@pytest.fixture(autouse=True)
def entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", SECRETO_PRUEBA)


def _contexto(*, cerrado: bool = False) -> tuple[int, int, int]:
    empresa_id = crear_empresa()
    with Session(engine()) as session:
        fuente = Fuente(empresa_id=empresa_id, nombre=f"Wallet {uuid.uuid4().hex[:6]}")
        session.add(fuente)
        session.flush()
        periodo = Periodo(
            empresa_id=empresa_id,
            fecha_inicio=date(2032, 1, 1),
            fecha_fin=date(2032, 1, 31),
            cerrado=cerrado,
        )
        session.add(periodo)
        session.flush()
        carga = Carga(
            empresa_id=empresa_id,
            fuente_id=fuente.id,
            periodo_id=periodo.id,
            contenido_hash=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
        )
        session.add(carga)
        session.commit()
        return empresa_id, fuente.id, carga.id


def _movimiento(
    *,
    empresa_id: int,
    fuente_id: int,
    carga_id: int,
    descripcion: str = "Pago por orden 123",
    estado: str = "PENDIENTE",
    tipo_fuente: str = "ENTRADA",
) -> int:
    with Session(engine()) as session:
        carga = session.get(Carga, carga_id)
        movimiento = Movimiento(
            fuente_id=fuente_id,
            carga_id=carga_id,
            periodo_id=carga.periodo_id,
            fecha=date(2032, 1, 10),
            monto=Decimal("150.00"),
            descripcion=descripcion,
            descripcion_norm=normalizar_descripcion(descripcion),
            estado_categoria=estado,
            hash_fila=hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
            crudo={"tipo_fuente": tipo_fuente},
        )
        session.add(movimiento)
        session.commit()
        return movimiento.id


def _regla(*, fuente_id: int, requiere_revision: bool = False) -> int:
    with Session(engine()) as session:
        regla = ReglaCategorizacion(
            motor_slug="conciliacion_wallets",
            fuente_id=fuente_id,
            patron="PAGO POR ORDEN",
            tipo_match="EMPIEZA_CON",
            prioridad=10,
            condiciones={"tipo_fuente": "ENTRADA"},
            tipo="INGRESO",
            unidad_negocio="DROPSHIPPING",
            categoria="VENTA",
            modalidad="WALLET",
            fijo_variable="VARIABLE",
            requiere_revision=requiere_revision,
            activa=True,
            origen="PRUEBA",
        )
        session.add(regla)
        session.commit()
        return regla.id


def test_listar_movimientos_respeta_empresas_asignadas() -> None:
    empresa_visible, fuente_visible, carga_visible = _contexto()
    visible = _movimiento(
        empresa_id=empresa_visible,
        fuente_id=fuente_visible,
        carga_id=carga_visible,
    )
    empresa_ajena, fuente_ajena, carga_ajena = _contexto()
    ajeno = _movimiento(
        empresa_id=empresa_ajena,
        fuente_id=fuente_ajena,
        carga_id=carga_ajena,
    )
    client, _ = cliente_con_rol(
        ROL_CONCILIACION,
        empresas=(empresa_visible,),
    )

    respuesta = client.get("/api/v1/movimientos")

    assert respuesta.status_code == 200
    ids = [fila["id"] for fila in respuesta.json()["items"]]
    assert visible in ids
    assert ajeno not in ids


def test_categorizar_manual_deja_auditoria_y_sugerencia_sin_crear_regla() -> None:
    empresa_id, fuente_id, carga_id = _contexto()
    movimiento_id = _movimiento(
        empresa_id=empresa_id,
        fuente_id=fuente_id,
        carga_id=carga_id,
    )
    client, usuario_id = cliente_con_rol(
        ROL_CONCILIACION,
        empresas=(empresa_id,),
    )

    respuesta = client.patch(
        f"/api/v1/movimientos/{movimiento_id}",
        json={
            "tipo": "INGRESO",
            "categoria": "VENTA",
            "unidad_negocio": "DROPSHIPPING",
            "empresa": "ASIATI",
            "tercero": "CLIENTE",
            "modalidad": "WALLET",
            "fijo_variable": "VARIABLE",
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["movimiento"]["estado_categoria"] == "MANUAL"
    assert cuerpo["movimiento"]["categoria"] == "VENTA"
    assert cuerpo["sugerencia_regla"]["tipo_match"] == "EXACTO"
    assert cuerpo["sugerencia_regla"]["origen"] == "APRENDIDA"

    with Session(engine()) as session:
        assert session.scalar(select(ReglaCategorizacion.id)) is None
        auditoria = session.scalars(
            select(Auditoria).where(
                Auditoria.accion == "movimiento.categorizar_manual",
                Auditoria.entidad_id == movimiento_id,
            )
        ).all()
    assert len(auditoria) == 1
    assert auditoria[0].usuario_id == usuario_id


def test_periodo_cerrado_rechaza_categorizacion_manual() -> None:
    empresa_id, fuente_id, carga_id = _contexto(cerrado=True)
    movimiento_id = _movimiento(
        empresa_id=empresa_id,
        fuente_id=fuente_id,
        carga_id=carga_id,
    )
    client, _ = cliente_con_rol(
        ROL_CONCILIACION,
        empresas=(empresa_id,),
    )

    respuesta = client.patch(
        f"/api/v1/movimientos/{movimiento_id}",
        json={"categoria": "NO DEBE CAMBIAR"},
    )

    assert respuesta.status_code == 409
    assert "cerrado" in respuesta.json()["detail"]
    with Session(engine()) as session:
        movimiento = session.get(Movimiento, movimiento_id)
        assert movimiento.estado_categoria == "PENDIENTE"
        assert movimiento.categoria is None


def test_recategorizar_aplica_regla_y_no_pisa_manual() -> None:
    empresa_id, fuente_id, carga_id = _contexto()
    automatico = _movimiento(
        empresa_id=empresa_id,
        fuente_id=fuente_id,
        carga_id=carga_id,
    )
    manual = _movimiento(
        empresa_id=empresa_id,
        fuente_id=fuente_id,
        carga_id=carga_id,
        descripcion="Pago por orden manual",
        estado="MANUAL",
    )
    regla_id = _regla(fuente_id=fuente_id)
    with Session(engine()) as session:
        carga = session.get(Carga, carga_id)
        periodo_id = carga.periodo_id

    client, _ = cliente_con_rol(
        ROL_CONCILIACION,
        empresas=(empresa_id,),
    )
    respuesta = client.post(
        "/api/v1/movimientos/recategorizar",
        json={
            "periodo_id": periodo_id,
            "motor_slug": "conciliacion_wallets",
            "fuente_id": fuente_id,
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["auto"] == 1
    assert respuesta.json()["manual_omitidos"] == 1
    with Session(engine()) as session:
        auto = session.get(Movimiento, automatico)
        sin_tocar = session.get(Movimiento, manual)
        regla = session.get(ReglaCategorizacion, regla_id)
        assert auto.estado_categoria == "AUTO"
        assert auto.regla_id == regla_id
        assert auto.tipo == "INGRESO"
        assert auto.categoria == "VENTA"
        assert sin_tocar.estado_categoria == "MANUAL"
        assert regla.veces_aplicada == 1


def test_importar_catalogo_wallets_es_idempotente_por_fuente() -> None:
    empresa_id, fuente_id, _ = _contexto()
    client, _ = cliente_con_rol(
        ROL_SUPER_ADMINISTRADOR,
        empresas=(empresa_id,),
    )

    primera = client.post(
        "/api/v1/reglas/importar",
        json={"fuente_id": fuente_id},
    )
    segunda = client.post(
        "/api/v1/reglas/importar",
        json={"fuente_id": fuente_id},
    )

    assert primera.status_code == 200, primera.text
    assert primera.json()["creadas"] > 0
    assert segunda.status_code == 200
    assert segunda.json()["creadas"] == 0
    assert segunda.json()["omitidas"] == primera.json()["creadas"]


def test_ti_puede_leer_pero_no_categorizar() -> None:
    empresa_id, fuente_id, carga_id = _contexto()
    movimiento_id = _movimiento(
        empresa_id=empresa_id,
        fuente_id=fuente_id,
        carga_id=carga_id,
    )
    client, _ = cliente_con_rol(ROL_TI)

    assert client.get("/api/v1/movimientos").status_code == 200
    assert (
        client.patch(
            f"/api/v1/movimientos/{movimiento_id}",
            json={"categoria": "X"},
        ).status_code
        == 403
    )
