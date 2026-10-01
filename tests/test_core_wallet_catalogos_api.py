import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.core.fuentes import Fuente
from app.core.periodos import Periodo
from app.core.usuarios.roles import (
    ROL_ANALISTA_TESORERIA,
    ROL_CONCILIACION,
    ROL_COORDINACION_FINANCIERA,
    ROL_TI,
)
from tests.apoyo_auth import cliente, cliente_con_rol, cliente_superadmin, engine


def _catalogo() -> tuple[int, int, int]:
    with Session(engine()) as session:
        empresa = Empresa(nombre=f"Catálogo Wallets {uuid.uuid4().hex[:8]}")
        session.add(empresa)
        session.flush()

        periodo = Periodo(
            empresa_id=empresa.id,
            fecha_inicio=date(2026, 9, 1),
            fecha_fin=date(2026, 9, 30),
            cerrado=False,
        )
        fuente = Fuente(
            empresa_id=empresa.id,
            nombre="Wallet Menpros",
        )
        session.add_all([periodo, fuente])
        session.commit()
        return empresa.id, periodo.id, fuente.id


def test_periodos_y_fuentes_salen_del_nucleo_por_empresa() -> None:
    empresa_id, periodo_id, fuente_id = _catalogo()
    client = cliente_superadmin()

    periodos = client.get("/api/v1/periodos", params={"empresa_id": empresa_id})
    fuentes = client.get("/api/v1/fuentes", params={"empresa_id": empresa_id})

    assert periodos.status_code == 200
    assert periodos.json() == [
        {
            "id": periodo_id,
            "empresa_id": empresa_id,
            "fecha_inicio": "2026-09-01",
            "fecha_fin": "2026-09-30",
            "cerrado": False,
        }
    ]
    assert fuentes.status_code == 200
    assert fuentes.json() == [
        {
            "id": fuente_id,
            "empresa_id": empresa_id,
            "nombre": "Wallet Menpros",
        }
    ]


def test_catalogos_respetan_empresas_asignadas() -> None:
    empresa_id, _, _ = _catalogo()
    conciliador, _ = cliente_con_rol(
        ROL_CONCILIACION,
        empresas=(empresa_id,),
    )
    ajeno, _ = cliente_con_rol(ROL_CONCILIACION)

    assert (
        conciliador.get("/api/v1/periodos", params={"empresa_id": empresa_id}).status_code
        == 200
    )
    assert (
        conciliador.get("/api/v1/fuentes", params={"empresa_id": empresa_id}).status_code
        == 200
    )
    assert (
        ajeno.get("/api/v1/periodos", params={"empresa_id": empresa_id}).status_code
        == 404
    )
    assert (
        ajeno.get("/api/v1/fuentes", params={"empresa_id": empresa_id}).status_code
        == 404
    )


def test_coordinacion_y_ti_pueden_consultar_catalogos() -> None:
    empresa_id, _, _ = _catalogo()
    coordinador, _ = cliente_con_rol(
        ROL_COORDINACION_FINANCIERA,
        empresas=(empresa_id,),
    )
    ti, _ = cliente_con_rol(ROL_TI)

    assert (
        coordinador.get("/api/v1/periodos", params={"empresa_id": empresa_id}).status_code
        == 200
    )
    assert (
        ti.get("/api/v1/fuentes", params={"empresa_id": empresa_id}).status_code
        == 200
    )


def test_analista_tesoreria_no_tiene_conciliacion_ver() -> None:
    empresa_id, _, _ = _catalogo()
    analista, _ = cliente_con_rol(
        ROL_ANALISTA_TESORERIA,
        empresas=(empresa_id,),
    )

    assert (
        analista.get("/api/v1/periodos", params={"empresa_id": empresa_id}).status_code
        == 403
    )
    assert (
        analista.get("/api/v1/fuentes", params={"empresa_id": empresa_id}).status_code
        == 403
    )


def test_catalogos_requieren_sesion() -> None:
    empresa_id, _, _ = _catalogo()
    sin_sesion = cliente()

    assert (
        sin_sesion.get("/api/v1/periodos", params={"empresa_id": empresa_id}).status_code
        == 401
    )
    assert (
        sin_sesion.get("/api/v1/fuentes", params={"empresa_id": empresa_id}).status_code
        == 401
    )


def test_catalogos_de_empresa_inexistente_responden_404() -> None:
    client = cliente_superadmin()

    assert (
        client.get("/api/v1/periodos", params={"empresa_id": 999999999}).status_code
        == 404
    )
    assert (
        client.get("/api/v1/fuentes", params={"empresa_id": 999999999}).status_code
        == 404
    )
