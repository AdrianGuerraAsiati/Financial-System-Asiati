"""Pruebas de contrato OAuth web de Google Sheets, sin credenciales reales."""
from urllib.parse import parse_qs, urlparse
import pytest
from fastapi import HTTPException
from app.integrations.google_sheets.oauth import (
    SHEETS_SCOPE, _config, _fernet, _hash_estado, construir_url_google,
)

def test_consentimiento_solo_lectura_con_pkce_y_estado():
    url = construir_url_google(
        client_id="id-falso",
        redirect_uri="https://financial.asiaticorp.com/api/v1/integrations/google-sheets/oauth/callback",
        state="nonce-aleatorio",
        verifier="verifier-de-prueba",
    )
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.google.com"
    assert params["scope"] == [SHEETS_SCOPE]
    assert params["access_type"] == ["offline"]
    assert params["prompt"] == ["consent"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["state"] == ["nonce-aleatorio"]
    assert "client_secret" not in params
    assert "code_verifier" not in params

def test_estado_hash_no_se_guarda_en_claro():
    assert len(_hash_estado("nonce")) == 64
    assert _hash_estado("nonce") != "nonce"

def test_refresh_token_es_cifrado(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_TOKEN_KEY", "x" * 40)
    f = _fernet()
    token = "token-de-prueba"
    cifrado = f.encrypt(token.encode())
    assert token.encode() not in cifrado
    assert f.decrypt(cifrado).decode() == token

def test_configuracion_incompleta_falla_cerrado(monkeypatch):
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI",
      "https://financial.asiaticorp.com/api/v1/integrations/google-sheets/oauth/callback")
    with pytest.raises(HTTPException) as exc:
        _config()
    assert exc.value.status_code == 503

def test_no_se_permite_callback_inseguro(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI",
      "http://example.org/api/v1/integrations/google-sheets/oauth/callback")
    with pytest.raises(HTTPException):
        _config()

def test_frontend_and_backend_share_independent_connection_permission():
    """Evita que un cambio en JS vuelva a ocultar Conectar a soporte TI."""
    from pathlib import Path
    from app.core.permisos import permisos_efectivos
    from app.core.usuarios.roles import ROL_TI, ROL_SUPER_ADMINISTRADOR
    assert "google_sheets.conectar" in permisos_efectivos(ROL_TI)
    assert "google_sheets.conectar" in permisos_efectivos(ROL_SUPER_ADMINISTRADOR)
    frontend = (Path(__file__).resolve().parents[1] / "app/web/google_sheets_connect.js").read_text()
    from app.integrations.google_sheets import oauth
    assert 'permisos?.["google_sheets.conectar"]' in frontend
    assert '"usuarios.gestionar"' not in frontend
    assert 'administrar = requiere("google_sheets.conectar")' in (Path(oauth.__file__).read_text())


def test_cookie_oauth_es_efimera_y_lax_sin_cambiar_cookie_sesion(monkeypatch):
    """Google navega desde otro sitio: la sesión Strict no se debe flexibilizar."""
    from fastapi import Response
    from app.integrations.google_sheets.oauth import (
        _poner_cookie_retorno, CALLBACK_PATH, COOKIE_RETORNO_GOOGLE,
    )
    monkeypatch.setenv("GOOGLE_OAUTH_TOKEN_KEY", "K" * 48)
    response = Response()
    _poner_cookie_retorno(response, "state-prueba")
    header = response.headers["set-cookie"]
    assert COOKIE_RETORNO_GOOGLE + "=" in header
    assert "Max-Age=600" in header
    assert "SameSite=lax" in header
    assert "Secure" in header
    assert "HttpOnly" in header
    assert "Path=" + CALLBACK_PATH in header
    assert "state-prueba" not in header
    assert "asiati_sesion" not in header


def test_cookie_oauth_firmada_ligada_al_state_y_secreto(monkeypatch):
    from starlette.requests import Request
    from app.integrations.google_sheets.oauth import (
        COOKIE_RETORNO_GOOGLE, _firma_cookie_retorno, _validar_cookie_retorno,
    )
    monkeypatch.setenv("GOOGLE_OAUTH_TOKEN_KEY", "S" * 48)
    firma = _firma_cookie_retorno("abc")
    assert len(firma) == 64
    assert firma != "abc"
    assert _firma_cookie_retorno("abc") == firma
    assert _firma_cookie_retorno("otro") != firma

    scope = {
        "type": "http", "method": "GET", "path": "/oauth/callback",
        "headers": [(b"cookie", (COOKIE_RETORNO_GOOGLE + "=" + firma).encode())],
    }
    _validar_cookie_retorno(Request(scope), "abc")
    with pytest.raises(HTTPException) as exc:
        _validar_cookie_retorno(Request(scope), "estado-falsificado")
    assert exc.value.status_code == 403


def test_callback_rechaza_sin_cookie_temporal_en_vez_de_401(monkeypatch):
    """Regresión: el retorno de Google no debe requerir la cookie Strict."""
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    response = TestClient(app, base_url="https://testserver").get(
        "/api/v1/integrations/google-sheets/oauth/callback?state=abc&code=test",
        follow_redirects=False,
    )
    assert response.status_code == 403
    assert "navegador" in response.json()["detail"]
