from fastapi.testclient import TestClient

from app.main import app


def test_cartera_view_exposes_auditable_snapshot_controls() -> None:
    html = TestClient(app).get("/")
    js = TestClient(app).get("/static/app.js")

    assert html.status_code == 200
    assert 'id="cartera-snapshots"' in html.text
    assert 'id="cartera-guardar-snapshot"' in html.text
    assert 'id="cartera-snapshots-lista"' in html.text

    assert js.status_code == 200
    assert "/api/v1/cartera/snapshots" in js.text
    assert "cargarSnapshotsCartera" in js.text
    assert "guardarSnapshotCartera" in js.text
