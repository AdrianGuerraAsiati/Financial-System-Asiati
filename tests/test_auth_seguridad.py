from datetime import datetime, timedelta, timezone

import pytest

from app.core.auth.config import ConfiguracionAuthError, cargar_configuracion
from app.core.auth.passwords import (
    PasswordDebilError,
    generar_password_temporal,
    hashear_password,
    validar_password_nueva,
    verificar_password,
)
from app.core.auth.tokens import SesionInvalidaError, emitir_token, leer_token


SECRETO = "s" * 40


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setenv("JWT_SECRET", SECRETO)
    monkeypatch.delenv("LOGIN_MAX_INTENTOS_FALLIDOS", raising=False)
    monkeypatch.delenv("LOGIN_VENTANA_MINUTOS", raising=False)
    monkeypatch.delenv("SESION_DURACION_HORAS", raising=False)
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    return monkeypatch


def test_passwords_are_hashed_with_argon2_and_verified() -> None:
    hash_ = hashear_password("una-clave-larga-segura")

    assert hash_.startswith("$argon2")
    assert verificar_password(hash_, "una-clave-larga-segura")
    assert not verificar_password(hash_, "otra-clave-distinta")


def test_temporary_passwords_are_random_and_long_enough() -> None:
    primera = generar_password_temporal()

    assert primera != generar_password_temporal()
    validar_password_nueva(primera)


def test_short_new_password_is_rejected_with_guidance() -> None:
    with pytest.raises(PasswordDebilError, match="al menos 12"):
        validar_password_nueva("corta")


def test_missing_jwt_secret_explains_what_to_do(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ConfiguracionAuthError, match="JWT_SECRET"):
        cargar_configuracion()


def test_short_jwt_secret_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "corto")

    with pytest.raises(ConfiguracionAuthError, match="32"):
        cargar_configuracion()


def test_login_limits_come_from_configuration(entorno: pytest.MonkeyPatch) -> None:
    entorno.setenv("LOGIN_MAX_INTENTOS_FALLIDOS", "3")
    entorno.setenv("LOGIN_VENTANA_MINUTOS", "10")

    configuracion = cargar_configuracion()

    assert configuracion.max_intentos_fallidos == 3
    assert configuracion.ventana_intentos == timedelta(minutes=10)


def test_login_limits_have_documented_defaults(entorno: pytest.MonkeyPatch) -> None:
    configuracion = cargar_configuracion()

    assert configuracion.max_intentos_fallidos == 5
    assert configuracion.ventana_intentos == timedelta(minutes=15)


def test_invalid_limit_value_explains_what_to_do(entorno: pytest.MonkeyPatch) -> None:
    entorno.setenv("LOGIN_MAX_INTENTOS_FALLIDOS", "cinco")

    with pytest.raises(ConfiguracionAuthError, match="LOGIN_MAX_INTENTOS_FALLIDOS"):
        cargar_configuracion()



def test_session_cookie_is_not_secure_by_default_in_development(
    entorno: pytest.MonkeyPatch,
) -> None:
    assert cargar_configuracion().cookie_secure is False


def test_session_cookie_is_secure_by_default_in_production(
    entorno: pytest.MonkeyPatch,
) -> None:
    entorno.setenv("APP_ENV", "production")

    assert cargar_configuracion().cookie_secure is True


def test_session_cookie_secure_can_be_overridden(
    entorno: pytest.MonkeyPatch,
) -> None:
    entorno.setenv("APP_ENV", "production")
    entorno.setenv("SESSION_COOKIE_SECURE", "false")

    assert cargar_configuracion().cookie_secure is False


def test_invalid_session_cookie_secure_value_is_rejected(
    entorno: pytest.MonkeyPatch,
) -> None:
    entorno.setenv("SESSION_COOKIE_SECURE", "quizas")

    with pytest.raises(ConfiguracionAuthError, match="SESSION_COOKIE_SECURE"):
        cargar_configuracion()


def test_token_round_trip_keeps_user_and_password_fingerprint(
    entorno: pytest.MonkeyPatch,
) -> None:
    configuracion = cargar_configuracion()
    token = emitir_token(configuracion, usuario_id=7, password_hash="$argon2id$abc")

    contenido = leer_token(configuracion, token)

    assert contenido.usuario_id == 7
    assert contenido.coincide_con("$argon2id$abc")
    assert not contenido.coincide_con("$argon2id$otro")


def test_expired_token_is_rejected(entorno: pytest.MonkeyPatch) -> None:
    configuracion = cargar_configuracion()
    antes = datetime.now(timezone.utc) - timedelta(days=2)
    token = emitir_token(
        configuracion, usuario_id=7, password_hash="h", ahora=antes
    )

    with pytest.raises(SesionInvalidaError):
        leer_token(configuracion, token)


def test_token_signed_with_other_secret_is_rejected(
    entorno: pytest.MonkeyPatch,
) -> None:
    token = emitir_token(cargar_configuracion(), usuario_id=7, password_hash="h")
    entorno.setenv("JWT_SECRET", "x" * 40)

    with pytest.raises(SesionInvalidaError):
        leer_token(cargar_configuracion(), token)
