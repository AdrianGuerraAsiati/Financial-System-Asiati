from pathlib import Path


HTML = Path("app/web/index.html").read_text(encoding="utf-8")
JS = Path("app/web/app.js").read_text(encoding="utf-8")


def test_login_exposes_cognito_confirmation_and_recovery_views() -> None:
    assert 'id="confirm-form"' in HTML
    assert 'id="reset-form"' in HTML
    assert 'id="auth-confirm-open"' in HTML
    assert 'id="auth-reset-open"' in HTML


def test_web_uses_cognito_recovery_api_contract() -> None:
    assert "/api/v1/auth/confirmar-registro" in JS
    assert "/api/v1/auth/reenviar-confirmacion" in JS
    assert "/api/v1/auth/solicitar-restablecimiento" in JS
    assert "/api/v1/auth/confirmar-restablecimiento" in JS
