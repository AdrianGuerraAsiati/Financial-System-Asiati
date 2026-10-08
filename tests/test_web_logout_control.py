"""Contract tests for the visible, functional logout control in the web shell."""

from fastapi.testclient import TestClient

from app.main import app


def test_web_shell_shows_explicit_logout_control() -> None:
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert response.text.count('id="logout"') == 1
    assert 'class="secondary-button logout-button"' in response.text
    assert "Cerrar sesión" in response.text
    assert 'id="logout-error"' in response.text
    assert 'role="alert"' in response.text


def test_logout_control_calls_backend_and_does_not_fake_success() -> None:
    client = TestClient(app)
    response = client.get("/static/app.js")

    assert response.status_code == 200
    script = response.text
    assert 'logoutButton.addEventListener("click", async () => {' in script
    assert 'fetch("/api/v1/auth/logout", {' in script
    assert 'credentials: "same-origin"' in script
    assert "if (!response.ok)" in script
    assert "logoutError.hidden = false;" in script
    assert "window.ASIATI_SESION = null;" in script
    assert 'window.location.replace("/");' in script


def test_logout_control_has_responsive_styles() -> None:
    response = TestClient(app).get("/static/styles.css")

    assert response.status_code == 200
    assert ".logout-button {" in response.text
    assert ".logout-button:hover:not(:disabled)" in response.text
    assert ".session-error {" in response.text
