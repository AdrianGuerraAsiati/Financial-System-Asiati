from datetime import timedelta

import httpx
import pytest

from app.core.auth.cognito import ClienteCognito, CognitoUsuarioNoConfirmado
from app.core.auth.config import ConfiguracionAuth, PROVEEDOR_AUTH_COGNITO


EMAIL = "usuario@asiati.test"
CLAVE = "a" * 16


def _config() -> ConfiguracionAuth:
    return ConfiguracionAuth(
        jwt_secret="x" * 40,
        max_intentos_fallidos=5,
        ventana_intentos=timedelta(minutes=15),
        duracion_sesion=timedelta(hours=8),
        cookie_secure=True,
        proveedor=PROVEEDOR_AUTH_COGNITO,
        cognito_region="us-east-2",
        cognito_client_id="client-test",
        cognito_client_secret="s" * 32,
    )


def test_cognito_login_uses_password_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    llamadas = []

    def post(url, *, headers, json, timeout):
        llamadas.append((headers, json))
        return httpx.Response(
            200,
            json={"AuthenticationResult": {"AccessToken": "token-test"}},
        )

    monkeypatch.setattr(httpx, "post", post)

    resultado = ClienteCognito(_config()).autenticar(EMAIL, CLAVE)

    assert resultado.requiere_nueva_password is False
    assert resultado.access_token == "token-test"
    headers, payload = llamadas[0]
    assert headers["X-Amz-Target"].endswith(".InitiateAuth")
    assert payload["AuthFlow"] == "USER_PASSWORD_AUTH"
    assert payload["AuthParameters"]["USERNAME"] == EMAIL
    assert payload["AuthParameters"]["SECRET_HASH"]


def test_cognito_force_change_password_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: httpx.Response(
            200,
            json={"ChallengeName": "NEW_PASSWORD_REQUIRED", "Session": "session-test"},
        ),
    )

    resultado = ClienteCognito(_config()).autenticar(EMAIL, CLAVE)

    assert resultado.requiere_nueva_password is True


def test_cognito_change_password_completes_challenge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operaciones = []

    def post(url, *, headers, json, timeout):
        operacion = headers["X-Amz-Target"].rsplit(".", 1)[-1]
        operaciones.append((operacion, json))
        if operacion == "InitiateAuth":
            return httpx.Response(
                200,
                json={"ChallengeName": "NEW_PASSWORD_REQUIRED", "Session": "session-test"},
            )
        return httpx.Response(
            200,
            json={"AuthenticationResult": {"AccessToken": "token-new"}},
        )

    monkeypatch.setattr(httpx, "post", post)

    ClienteCognito(_config()).cambiar_password(EMAIL, CLAVE, "b" * 16)

    assert [op for op, _ in operaciones] == [
        "InitiateAuth",
        "RespondToAuthChallenge",
    ]
    assert operaciones[1][1]["ChallengeResponses"]["SECRET_HASH"]


def test_cognito_unconfirmed_user_has_distinct_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: httpx.Response(
            400,
            json={"__type": "UserNotConfirmedException", "message": "pending"},
        ),
    )

    with pytest.raises(CognitoUsuarioNoConfirmado):
        ClienteCognito(_config()).autenticar(EMAIL, CLAVE)
