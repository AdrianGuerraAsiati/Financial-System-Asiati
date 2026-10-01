"""Cada endpoint de la sesión contra cada rol (ROLES_Y_PERMISOS.md §7)."""
import os
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import Auditoria
from app.core.hallazgos import Hallazgo, HallazgoMensaje
from app.core.permisos import PERMISOS
from app.core.usuarios import (
    ROLES,
    ROL_CONCILIACION,
    ROL_COORDINACION_FINANCIERA,
    ROL_SUPER_ADMINISTRADOR,
    ROL_TI,
    Usuario,
    UsuarioEmpresa,
)
from tests.apoyo_auth import (
    PASSWORD_PRUEBA,
    SECRETO_PRUEBA,
    cliente,
    cliente_con_rol,
    crear_empresa,
    crear_hallazgo,
    crear_periodo,
    crear_usuario_prueba,
    email_unico,
    engine,
    iniciar_sesion,
)


@pytest.fixture(autouse=True)
def entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", SECRETO_PRUEBA)


@dataclass(frozen=True)
class Endpoint:
    metodo: str
    permiso: str
    # Recibe la empresa asignada y devuelve (ruta, cuerpo JSON).
    preparar: Callable[[int], tuple[str, dict | None]]

    def llamar(self, client, empresa_id: int):
        ruta, cuerpo = self.preparar(empresa_id)
        return client.request(self.metodo, ruta, json=cuerpo)


def _otro_usuario(_: int) -> int:
    return crear_usuario_prueba(ROL_CONCILIACION)[0]


def _hallazgo(empresa_id: int, estado: str = "detectado") -> int:
    return crear_hallazgo(crear_periodo(empresa_id), estado=estado)


ENDPOINTS = {
    "listar_usuarios": Endpoint("GET", "usuarios.gestionar", lambda e: ("/api/v1/usuarios", None)),
    "crear_usuario": Endpoint(
        "POST",
        "usuarios.gestionar",
        lambda e: (
            "/api/v1/usuarios",
            {"email": email_unico(), "nombre": "Nuevo", "rol": ROL_CONCILIACION, "empresas": [e]},
        ),
    ),
    "editar_usuario": Endpoint(
        "PATCH",
        "usuarios.gestionar",
        lambda e: (f"/api/v1/usuarios/{_otro_usuario(e)}", {"nombre": "Editado"}),
    ),
    "asignar_empresas": Endpoint(
        "PUT",
        "usuarios.gestionar",
        lambda e: (f"/api/v1/usuarios/{_otro_usuario(e)}/empresas", {"empresas": [e]}),
    ),
    "restablecer_password": Endpoint(
        "POST",
        "usuarios.gestionar",
        lambda e: (f"/api/v1/usuarios/{_otro_usuario(e)}/restablecer", None),
    ),
    "supervision_conciliaciones": Endpoint(
        "GET", "supervision.ver", lambda e: ("/api/v1/supervision/conciliaciones", None)
    ),
    "supervision_ingresos": Endpoint(
        "GET", "supervision.ver", lambda e: ("/api/v1/supervision/ingresos", None)
    ),
    "supervision_acciones": Endpoint(
        "GET", "supervision.ver", lambda e: ("/api/v1/supervision/acciones", None)
    ),
    "listar_hallazgos": Endpoint(
        "GET", "conciliacion.ver", lambda e: ("/api/v1/hallazgos?estado=escalado", None)
    ),
    "detalle_hallazgo": Endpoint(
        "GET", "conciliacion.ver", lambda e: (f"/api/v1/hallazgos/{_hallazgo(e)}", None)
    ),
    "escalar_hallazgo": Endpoint(
        "POST",
        "hallazgos.escalar",
        lambda e: (f"/api/v1/hallazgos/{_hallazgo(e)}/escalar", {"pregunta": "¿Se cobra?"}),
    ),
    "observar_hallazgo": Endpoint(
        "POST",
        "hallazgos.gestionar",
        lambda e: (
            f"/api/v1/hallazgos/{_hallazgo(e)}/observar",
            {"observacion": "Transferencia a proveedor", "resolver": False},
        ),
    ),
    "responder_escalado": Endpoint(
        "POST",
        "hallazgos.responder_escalado",
        lambda e: (
            f"/api/v1/hallazgos/{_hallazgo(e, 'escalado')}/responder",
            {"respuesta": "Sí", "resolver": False},
        ),
    ),
}


@pytest.fixture(scope="module")
def clientes_por_rol() -> dict[str, tuple[object, int]]:
    # Una empresa asignada a todos: así el alcance ASIGNADAS también es permitido.
    # El login ocurre antes de los fixtures por test, por eso el secreto va aquí.
    os.environ.setdefault("JWT_SECRET", SECRETO_PRUEBA)
    empresa_id = crear_empresa()
    return {
        rol: (cliente_con_rol(rol, empresas=(empresa_id,))[0], empresa_id)
        for rol in ROLES
    }


@pytest.mark.parametrize("rol", ROLES)
@pytest.mark.parametrize("nombre", sorted(ENDPOINTS))
def test_each_endpoint_against_each_role(
    nombre: str, rol: str, clientes_por_rol: dict[str, tuple[object, int]]
) -> None:
    endpoint = ENDPOINTS[nombre]
    client, empresa_id = clientes_por_rol[rol]

    respuesta = endpoint.llamar(client, empresa_id)

    if rol in PERMISOS[endpoint.permiso]:
        assert respuesta.status_code < 400, respuesta.text
    else:
        assert respuesta.status_code == 403, respuesta.text
        assert "superadministrador" in respuesta.json()["detail"]


@pytest.mark.parametrize("nombre", sorted(ENDPOINTS))
def test_each_endpoint_requires_a_session(nombre: str) -> None:
    empresa_id = crear_empresa()

    respuesta = ENDPOINTS[nombre].llamar(cliente(), empresa_id)

    assert respuesta.status_code == 401


def _auditoria(accion: str, entidad_id: int) -> list[Auditoria]:
    with Session(engine()) as session:
        return list(
            session.scalars(
                select(Auditoria).where(
                    Auditoria.accion == accion, Auditoria.entidad_id == entidad_id
                )
            )
        )


# --- Empresas asignadas -----------------------------------------------------


def test_conciliator_does_not_see_or_operate_unassigned_company() -> None:
    wiilog = crear_empresa("WIILOG")
    chin_chin = crear_empresa("CHIN CHIN")
    propio = _hallazgo(wiilog)
    ajeno = _hallazgo(chin_chin)
    client, _ = cliente_con_rol(ROL_CONCILIACION, empresas=(wiilog,))

    listado = client.get("/api/v1/hallazgos").json()
    detalle = client.get(f"/api/v1/hallazgos/{ajeno}")
    escalar = client.post(f"/api/v1/hallazgos/{ajeno}/escalar", json={"pregunta": "¿?"})

    ids = [hallazgo["id"] for hallazgo in listado]
    assert propio in ids
    assert ajeno not in ids
    assert all(hallazgo["empresa_id"] == wiilog for hallazgo in listado)
    assert detalle.status_code == 404
    assert escalar.status_code == 404
    assert detalle.json()["detail"] == client.get("/api/v1/hallazgos/999999999").json()["detail"]


def test_conciliator_without_companies_sees_an_empty_list() -> None:
    _hallazgo(crear_empresa())
    client, _ = cliente_con_rol(ROL_CONCILIACION)

    assert client.get("/api/v1/hallazgos").json() == []


def test_coordinator_only_answers_cases_of_assigned_companies() -> None:
    asignada = crear_empresa()
    ajena = crear_empresa()
    client, _ = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(asignada,))

    respuesta = client.post(
        f"/api/v1/hallazgos/{_hallazgo(ajena, 'escalado')}/responder",
        json={"respuesta": "Sí", "resolver": True},
    )

    assert respuesta.status_code == 404


def test_it_support_reads_findings_but_cannot_escalate_them() -> None:
    empresa_id = crear_empresa()
    hallazgo_id = _hallazgo(empresa_id)
    client, _ = cliente_con_rol(ROL_TI)

    assert client.get(f"/api/v1/hallazgos/{hallazgo_id}").status_code == 200
    assert (
        client.post(
            f"/api/v1/hallazgos/{hallazgo_id}/escalar", json={"pregunta": "¿?"}
        ).status_code
        == 403
    )


# --- Caso especial ----------------------------------------------------------


def test_escalating_without_question_is_rejected_and_changes_nothing() -> None:
    empresa_id = crear_empresa()
    hallazgo_id = _hallazgo(empresa_id)
    client, _ = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa_id,))

    respuesta = client.post(f"/api/v1/hallazgos/{hallazgo_id}/escalar", json={"pregunta": "  "})

    assert respuesta.status_code == 422
    assert "pregunta" in respuesta.json()["detail"]
    with Session(engine()) as session:
        assert session.get(Hallazgo, hallazgo_id).estado == "detectado"
    assert _auditoria("hallazgo.escalar", hallazgo_id) == []


def test_escalate_and_answer_leave_thread_and_audit_rows() -> None:
    empresa_id = crear_empresa()
    hallazgo_id = _hallazgo(empresa_id)
    conciliador, conciliador_id = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa_id,))
    coordinador, coordinador_id = cliente_con_rol(
        ROL_COORDINACION_FINANCIERA, empresas=(empresa_id,)
    )

    escalar = conciliador.post(
        f"/api/v1/hallazgos/{hallazgo_id}/escalar",
        json={"pregunta": "¿Este flete se cobra?"},
    )
    bandeja = coordinador.get("/api/v1/hallazgos?estado=escalado").json()
    responder = coordinador.post(
        f"/api/v1/hallazgos/{hallazgo_id}/responder",
        json={"respuesta": "No, se reclama a la transportadora.", "resolver": True},
    )
    detalle = coordinador.get(f"/api/v1/hallazgos/{hallazgo_id}").json()

    assert escalar.status_code == 200
    assert escalar.json()["estado"] == "escalado"
    assert hallazgo_id in [hallazgo["id"] for hallazgo in bandeja]
    assert responder.status_code == 200
    assert detalle["estado"] == "resuelto"
    assert detalle["resuelto"] is True
    assert [(m["tipo"], m["usuario_id"]) for m in detalle["mensajes"]] == [
        ("PREGUNTA", conciliador_id),
        ("RESPUESTA", coordinador_id),
    ]

    [fila_escalar] = _auditoria("hallazgo.escalar", hallazgo_id)
    assert fila_escalar.usuario_id == conciliador_id
    assert fila_escalar.empresa_id == empresa_id
    assert fila_escalar.antes == {"estado": "detectado"}
    assert fila_escalar.despues["estado"] == "escalado"
    [fila_responder] = _auditoria("hallazgo.responder_escalado", hallazgo_id)
    assert fila_responder.usuario_id == coordinador_id
    assert fila_responder.despues["estado"] == "resuelto"


def test_answer_without_resolving_returns_case_to_reconciler() -> None:
    empresa_id = crear_empresa()
    hallazgo_id = _hallazgo(empresa_id, "escalado")
    client, _ = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(empresa_id,))

    respuesta = client.post(
        f"/api/v1/hallazgos/{hallazgo_id}/responder",
        json={"respuesta": "Revisa la guía.", "resolver": False},
    )

    assert respuesta.json()["estado"] == "en_gestion"
    assert respuesta.json()["resuelto"] is False


def test_findings_of_a_closed_period_cannot_be_escalated() -> None:
    empresa_id = crear_empresa()
    hallazgo_id = crear_hallazgo(crear_periodo(empresa_id, cerrado=True))
    client, _ = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa_id,))

    respuesta = client.post(
        f"/api/v1/hallazgos/{hallazgo_id}/escalar", json={"pregunta": "¿Se cobra?"}
    )

    assert respuesta.status_code == 409
    assert "cerrado" in respuesta.json()["detail"]
    with Session(engine()) as session:
        mensajes = session.scalars(
            select(HallazgoMensaje).where(HallazgoMensaje.hallazgo_id == hallazgo_id)
        ).all()
    assert mensajes == []


def test_invalid_state_filter_explains_valid_values() -> None:
    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)

    respuesta = client.get("/api/v1/hallazgos?estado=abierto")

    assert respuesta.status_code == 422
    assert "escalado" in respuesta.json()["detail"]


# --- Usuarios ---------------------------------------------------------------


def test_superadmin_creates_user_with_temporary_password_and_audit() -> None:
    empresa_id = crear_empresa()
    client, admin_id = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)
    email = email_unico()

    respuesta = client.post(
        "/api/v1/usuarios",
        json={"email": email, "nombre": "Nueva", "rol": ROL_CONCILIACION, "empresas": [empresa_id]},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["usuario"]["empresas"] == [empresa_id]
    assert cuerpo["usuario"]["debe_cambiar_password"] is True
    login = cliente().post(
        "/api/v1/auth/login",
        json={"email": email, "password": cuerpo["password_temporal"]},
    )
    assert login.json() == {"debe_cambiar_password": True}

    [fila] = _auditoria("usuario.crear", cuerpo["usuario"]["id"])
    assert fila.usuario_id == admin_id
    assert "password" not in str(fila.despues)
    with Session(engine()) as session:
        creado = session.get(Usuario, cuerpo["usuario"]["id"])
        assert creado.creado_por == admin_id


def test_new_coordinator_gets_all_companies_by_default() -> None:
    crear_empresa()
    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)

    respuesta = client.post(
        "/api/v1/usuarios",
        json={"email": email_unico(), "nombre": "Coord", "rol": ROL_COORDINACION_FINANCIERA},
    )

    with Session(engine()) as session:
        from app.core.empresas import Empresa

        todas = sorted(session.scalars(select(Empresa.id)))
    assert respuesta.json()["usuario"]["empresas"] == todas


def test_duplicate_email_and_invalid_role_are_explained() -> None:
    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)
    _, existente = crear_usuario_prueba(ROL_CONCILIACION)

    duplicado = client.post(
        "/api/v1/usuarios",
        json={"email": existente, "nombre": "X", "rol": ROL_CONCILIACION},
    )
    rol_malo = client.post(
        "/api/v1/usuarios",
        json={"email": email_unico(), "nombre": "X", "rol": "SUPERADMIN"},
    )

    assert duplicado.status_code == 409
    assert "Ya existe" in duplicado.json()["detail"]
    assert rol_malo.status_code == 422
    assert "super_administrador" in rol_malo.json()["detail"]


def test_assigning_unknown_company_is_rejected() -> None:
    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)
    usuario_id, _ = crear_usuario_prueba(ROL_CONCILIACION)

    respuesta = client.put(
        f"/api/v1/usuarios/{usuario_id}/empresas", json={"empresas": [999999999]}
    )

    assert respuesta.status_code == 422
    assert "999999999" in respuesta.json()["detail"]


def test_assigning_companies_replaces_the_list_and_is_audited() -> None:
    primera, segunda = crear_empresa(), crear_empresa()
    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)
    usuario_id, _ = crear_usuario_prueba(ROL_CONCILIACION, empresas=(primera,))

    respuesta = client.put(
        f"/api/v1/usuarios/{usuario_id}/empresas", json={"empresas": [segunda]}
    )

    assert respuesta.json()["empresas"] == [segunda]
    with Session(engine()) as session:
        asignadas = session.scalars(
            select(UsuarioEmpresa.empresa_id).where(UsuarioEmpresa.usuario_id == usuario_id)
        ).all()
    assert asignadas == [segunda]
    [fila] = _auditoria("usuario.asignar_empresas", usuario_id)
    assert fila.antes == {"empresas": [primera]}
    assert fila.despues == {"empresas": [segunda]}


def test_edit_user_is_audited_with_before_and_after() -> None:
    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)
    usuario_id, _ = crear_usuario_prueba(ROL_CONCILIACION)

    respuesta = client.patch(
        f"/api/v1/usuarios/{usuario_id}",
        json={"rol": ROL_COORDINACION_FINANCIERA, "activo": False},
    )

    assert respuesta.status_code == 200
    [fila] = _auditoria("usuario.editar", usuario_id)
    assert fila.antes["rol"] == ROL_CONCILIACION
    assert fila.despues["rol"] == ROL_COORDINACION_FINANCIERA
    assert fila.despues["activo"] is False


def test_superadmin_cannot_lock_themselves_out() -> None:
    client, admin_id = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)

    desactivar = client.patch(f"/api/v1/usuarios/{admin_id}", json={"activo": False})
    degradar = client.patch(f"/api/v1/usuarios/{admin_id}", json={"rol": ROL_TI})

    assert desactivar.status_code == 409
    assert degradar.status_code == 409


def test_password_reset_invalidates_old_sessions_and_forces_change() -> None:
    admin, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)
    usuario_id, email = crear_usuario_prueba(ROL_CONCILIACION)
    sesion_vieja = iniciar_sesion(email)

    respuesta = admin.post(f"/api/v1/usuarios/{usuario_id}/restablecer")

    assert respuesta.status_code == 200
    assert sesion_vieja.get("/api/v1/auth/me").status_code == 401
    assert (
        cliente()
        .post("/api/v1/auth/login", json={"email": email, "password": PASSWORD_PRUEBA})
        .status_code
        == 401
    )
    nueva = cliente().post(
        "/api/v1/auth/login",
        json={"email": email, "password": respuesta.json()["password_temporal"]},
    )
    assert nueva.json() == {"debe_cambiar_password": True}
    assert len(_auditoria("usuario.restablecer_password", usuario_id)) == 1


def test_unknown_user_is_not_found() -> None:
    client, _ = cliente_con_rol(ROL_SUPER_ADMINISTRADOR)

    assert client.patch("/api/v1/usuarios/999999999", json={"nombre": "X"}).status_code == 404


def test_password_change_is_audited() -> None:
    usuario_id, email = crear_usuario_prueba(ROL_CONCILIACION, debe_cambiar_password=True)

    iniciar_sesion(email).post(
        "/api/v1/auth/cambiar-password",
        json={"password_actual": PASSWORD_PRUEBA, "password_nueva": "otra-clave-muy-larga"},
    )

    assert len(_auditoria("usuario.cambiar_password", usuario_id)) == 1


# --- Supervisión ------------------------------------------------------------


def test_supervision_shows_only_assigned_companies_to_coordinator() -> None:
    asignada, ajena = crear_empresa(), crear_empresa()
    periodo_asignado = crear_periodo(asignada)
    crear_hallazgo(periodo_asignado, estado="escalado")
    periodo_ajeno = crear_periodo(ajena)
    client, _ = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(asignada,))

    filas = client.get("/api/v1/supervision/conciliaciones").json()

    ids = {fila["periodo_id"] for fila in filas}
    assert periodo_asignado in ids
    assert periodo_ajeno not in ids
    [fila] = [fila for fila in filas if fila["periodo_id"] == periodo_asignado]
    assert fila["hallazgos_abiertos"] == 1
    assert fila["hallazgos_escalados"] == 1
    assert fila["score"] is None


def test_supervision_logins_are_scoped_to_users_of_assigned_companies() -> None:
    asignada, ajena = crear_empresa(), crear_empresa()
    visible_id, visible_email = crear_usuario_prueba(ROL_CONCILIACION, empresas=(asignada,))
    oculto_id, oculto_email = crear_usuario_prueba(ROL_CONCILIACION, empresas=(ajena,))
    iniciar_sesion(visible_email)
    iniciar_sesion(oculto_email)
    client, _ = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(asignada,))

    usuarios = {fila["usuario_id"] for fila in client.get("/api/v1/supervision/ingresos").json()}

    assert visible_id in usuarios
    assert oculto_id not in usuarios


def test_supervision_actions_count_audit_rows_per_user() -> None:
    empresa_id = crear_empresa()
    conciliador, conciliador_id = cliente_con_rol(ROL_CONCILIACION, empresas=(empresa_id,))
    for _ in range(2):
        conciliador.post(
            f"/api/v1/hallazgos/{_hallazgo(empresa_id)}/escalar",
            json={"pregunta": "¿Se cobra?"},
        )
    coordinador, _ = cliente_con_rol(ROL_COORDINACION_FINANCIERA, empresas=(empresa_id,))

    filas = coordinador.get(
        f"/api/v1/supervision/acciones?usuario_id={conciliador_id}"
    ).json()

    assert filas == [
        {
            "usuario_id": conciliador_id,
            "nombre": f"Usuario {ROL_CONCILIACION}",
            "rol": ROL_CONCILIACION,
            "accion": "hallazgo.escalar",
            "cantidad": 2,
        }
    ]
