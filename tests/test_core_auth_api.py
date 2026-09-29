import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.model import Ingreso
from app.core.permisos import permisos_efectivos
from app.core.usuarios import (
    ROLES,
    ROL_CONCILIACION,
    ROL_SUPER_ADMINISTRADOR,
    Usuario,
)
from tests.apoyo_auth import (
    PASSWORD_PRUEBA,
    SECRETO_PRUEBA,
    cliente,
    crear_empresa,
    crear_usuario_prueba,
    engine,
    iniciar_sesion,
)


@pytest.fixture(autouse=True)
def entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", SECRETO_PRUEBA)
    monkeypatch.setenv("LOGIN_MAX_INTENTOS_FALLIDOS", "5")
    monkeypatch.setenv("LOGIN_VENTANA_MINUTOS", "15")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")


def _ingresos(email: str) -> list[Ingreso]:
    with Session(engine()) as session:
        return list(
            session.scalars(
                select(Ingreso)
                .where(Ingreso.email_intentado == email)
                .order_by(Ingreso.id)
            )
        )


def test_successful_login_sets_secure_cookie_and_records_the_login() -> None:
    usuario_id, email = crear_usuario_prueba(ROL_CONCILIACION)

    respuesta = cliente().post(
        "/api/v1/auth/login",
        json={"email": email.upper(), "password": PASSWORD_PRUEBA},
        headers={"User-Agent": "prueba-navegador"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"debe_cambiar_password": False}
    cookie = respuesta.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=strict" in cookie

    [ingreso] = _ingresos(email)
    assert ingreso.exito is True
    assert ingreso.usuario_id == usuario_id
    assert ingreso.user_agent == "prueba-navegador"
    with Session(engine()) as session:
        assert session.get(Usuario, usuario_id).ultimo_ingreso_at is not None


def test_wrong_password_is_rejected_and_recorded() -> None:
    _, email = crear_usuario_prueba(ROL_CONCILIACION)

    respuesta = cliente().post(
        "/api/v1/auth/login", json={"email": email, "password": "equivocada-123"}
    )

    assert respuesta.status_code == 401
    assert "restablezca" in respuesta.json()["detail"]
    assert [i.exito for i in _ingresos(email)] == [False]


def test_unknown_email_gets_the_same_answer_and_is_recorded() -> None:
    email = "nadie-registrado@asiati.test"
    respuesta = cliente().post(
        "/api/v1/auth/login", json={"email": email, "password": "cualquier-cosa"}
    )

    assert respuesta.status_code == 401
    assert _ingresos(email)[-1].usuario_id is None


def test_inactive_user_cannot_log_in() -> None:
    _, email = crear_usuario_prueba(ROL_CONCILIACION, activo=False)

    respuesta = cliente().post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD_PRUEBA}
    )

    assert respuesta.status_code == 401


def test_login_is_blocked_after_too_many_failures_even_with_right_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGIN_MAX_INTENTOS_FALLIDOS", "3")
    _, email = crear_usuario_prueba(ROL_CONCILIACION)
    client = cliente()
    for _ in range(3):
        client.post("/api/v1/auth/login", json={"email": email, "password": "mala-clave-1"})

    respuesta = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD_PRUEBA}
    )

    assert respuesta.status_code == 429
    assert "minutos" in respuesta.json()["detail"]
    assert _ingresos(email)[-1].exito is False


def test_requests_without_session_are_rejected() -> None:
    respuesta = cliente().get("/api/v1/auth/me")

    assert respuesta.status_code == 401
    assert "Inicia sesión" in respuesta.json()["detail"]


@pytest.mark.parametrize("rol", ROLES)
def test_me_returns_role_effective_permissions_and_companies(rol: str) -> None:
    empresa_id = crear_empresa()
    _, email = crear_usuario_prueba(rol, empresas=(empresa_id,))

    respuesta = iniciar_sesion(email).get("/api/v1/auth/me")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["usuario"]["email"] == email
    assert cuerpo["usuario"]["rol"] == rol
    assert cuerpo["permisos"] == {
        permiso: alcance.value for permiso, alcance in permisos_efectivos(rol).items()
    }
    assert empresa_id in [empresa["id"] for empresa in cuerpo["empresas"]]


def test_conciliator_me_lists_only_assigned_companies() -> None:
    asignada = crear_empresa()
    otra = crear_empresa()
    _, email = crear_usuario_prueba(ROL_CONCILIACION, empresas=(asignada,))

    empresas = iniciar_sesion(email).get("/api/v1/auth/me").json()["empresas"]

    assert [empresa["id"] for empresa in empresas] == [asignada]
    assert otra not in [empresa["id"] for empresa in empresas]


def test_superadmin_me_lists_all_companies() -> None:
    otra = crear_empresa()
    _, email = crear_usuario_prueba(ROL_SUPER_ADMINISTRADOR)

    empresas = iniciar_sesion(email).get("/api/v1/auth/me").json()["empresas"]

    assert otra in [empresa["id"] for empresa in empresas]


def test_first_login_forces_password_change_before_anything_else() -> None:
    _, email = crear_usuario_prueba(
        ROL_SUPER_ADMINISTRADOR, debe_cambiar_password=True
    )
    client = cliente()
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD_PRUEBA}
    )
    assert login.json() == {"debe_cambiar_password": True}

    bloqueado = client.get("/api/v1/usuarios")
    assert bloqueado.status_code == 403
    assert "cambiar tu contraseña" in bloqueado.json()["detail"]
    assert client.get("/api/v1/auth/me").status_code == 200

    cambio = client.post(
        "/api/v1/auth/cambiar-password",
        json={"password_actual": PASSWORD_PRUEBA, "password_nueva": "otra-clave-muy-larga"},
    )
    assert cambio.status_code == 200
    assert client.get("/api/v1/usuarios").status_code == 200


def test_password_change_requires_current_password_and_minimum_length() -> None:
    _, email = crear_usuario_prueba(ROL_CONCILIACION, debe_cambiar_password=True)
    client = iniciar_sesion(email)

    incorrecta = client.post(
        "/api/v1/auth/cambiar-password",
        json={"password_actual": "no-es-esta-clave", "password_nueva": "otra-clave-muy-larga"},
    )
    corta = client.post(
        "/api/v1/auth/cambiar-password",
        json={"password_actual": PASSWORD_PRUEBA, "password_nueva": "corta"},
    )

    assert incorrecta.status_code == 400
    assert corta.status_code == 422
    assert "12" in corta.json()["detail"]


def test_logout_clears_the_session_cookie() -> None:
    _, email = crear_usuario_prueba(ROL_CONCILIACION)
    client = iniciar_sesion(email)

    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_deactivated_user_loses_an_open_session() -> None:
    usuario_id, email = crear_usuario_prueba(ROL_CONCILIACION)
    client = iniciar_sesion(email)
    with Session(engine()) as session:
        session.get(Usuario, usuario_id).activo = False
        session.commit()

    assert client.get("/api/v1/auth/me").status_code == 401
