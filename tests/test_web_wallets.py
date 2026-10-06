from fastapi.testclient import TestClient

from app.main import app


def test_shell_exposes_wallets_view_and_controls() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert 'id="nav-wallets"' in response.text
    assert 'id="vista-wallets"' in response.text
    assert 'id="wallets-form"' in response.text
    assert 'id="wallets-periodo"' in response.text
    assert 'id="wallets-tipo"' in response.text
    assert 'id="wallets-c0-panel"' in response.text
    assert 'id="wallets-hallazgos-panel"' in response.text
    assert 'id="wallets-hallazgo-dialog"' in response.text
    assert '/static/wallets.js' in response.text


def test_wallets_javascript_uses_core_and_motor_contracts() -> None:
    response = TestClient(app).get("/static/wallets.js")

    assert response.status_code == 200
    for path in (
        "/api/v1/periodos?empresa_id=",
        "/api/v1/fuentes?empresa_id=",
        "/api/v1/wallets/catalogo?empresa_id=",
        "/api/v1/wallets/wiilog/conciliar",
        "/api/v1/wallets/tiendas/conciliar",
        "/api/v1/wallets/pagos/conciliar",
        "/api/v1/hallazgos/",
    ):
        assert path in response.text

    assert 'sessionStorage.setItem' in response.text
    assert 'conciliacion.ejecutar' in response.text
    assert 'hallazgos.gestionar' in response.text
    assert 'hallazgos.escalar' in response.text
    assert 'hallazgos.responder_escalado' in response.text
    assert 'Conciliando…' in response.text
    assert 'CUADRA' in response.text
    assert 'NO CUADRA' in response.text
    assert "Promise.allSettled" in response.text


def test_wallets_styles_keep_text_labels_when_printed() -> None:
    response = TestClient(app).get("/static/styles.css")

    assert response.status_code == 200
    assert "@media print" in response.text
    assert "#vista-wallets .wallet-pill" in response.text


def test_wallets_javascript_formats_c0_and_explains_breaks() -> None:
    response = TestClient(app).get("/static/wallets.js")

    assert response.status_code == 200
    assert "formatearDecimal(" in response.text
    assert '"-$ "' in response.text
    assert "El saldo no cuadra en " in response.text
    assert (
        "El archivo puede estar incompleto: descárgalo de nuevo de Dropi "
        "y vuelve a conciliar."
    ) in response.text


def test_wallets_javascript_labels_and_defaults() -> None:
    response = TestClient(app).get("/static/wallets.js")

    assert response.status_code == 200
    assert 'CRITICO: "CRÍTICO"' in response.text
    assert "preseleccionarUnica(" in response.text
    assert "corte_ordenes_usado" in response.text


def test_shell_has_cut_off_line_in_c0_panel() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert 'id="wallets-c0-corte"' in response.text
