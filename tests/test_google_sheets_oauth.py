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
