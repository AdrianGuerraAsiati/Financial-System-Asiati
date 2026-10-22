"""Controles de elevación de la cuenta técnica: sin permisos globales al rol TI."""
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from app.core.usuarios.roles import ROL_SUPER_ADMINISTRADOR, ROL_TI
from app.core.usuarios import promover_sistemas_superadmin_dev as tarea


class FakeSession:
    def __init__(self, usuario):
        self.usuario = usuario
        self.commits = 0

    def scalar(self, _query):
        return self.usuario

    def commit(self):
        self.commits += 1


def preparar(monkeypatch, rol=ROL_TI, activo=True):
    usuario = SimpleNamespace(id=17, email=tarea.CUENTA_AUTORIZADA, rol=rol, activo=activo)
    session = FakeSession(usuario)

    @contextmanager
    def abrir():
        yield session

    eventos = []
    monkeypatch.setattr(tarea, "crear_session", abrir)
    monkeypatch.setattr(tarea, "registrar_auditoria", lambda *_a, **kw: eventos.append(kw))
    return usuario, session, eventos


def test_no_promover_fuera_de_desarrollo(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="solo puede ejecutarse"):
        tarea.main()


def test_promueve_cuenta_tecnica_y_audita(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    usuario, session, eventos = preparar(monkeypatch)
    assert tarea.main() == 0
    assert usuario.rol == ROL_SUPER_ADMINISTRADOR
    assert session.commits == 1
    assert eventos[0]["usuario_id"] is None
    assert eventos[0]["entidad_id"] == usuario.id
    assert eventos[0]["antes"]["rol"] == ROL_TI
    assert eventos[0]["despues"]["rol"] == ROL_SUPER_ADMINISTRADOR


def test_idempotente_si_ya_es_superadmin(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    _, session, eventos = preparar(monkeypatch, ROL_SUPER_ADMINISTRADOR)
    assert tarea.main() == 0
    assert session.commits == 0
    assert eventos == []


def test_rechaza_otros_roles_o_cuenta_inactiva(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    _, session, eventos = preparar(monkeypatch, "conciliacion")
    with pytest.raises(RuntimeError, match="Rol inesperado"):
        tarea.main()
    assert session.commits == 0
    assert eventos == []
    _, session, _ = preparar(monkeypatch, ROL_TI, activo=False)
    with pytest.raises(RuntimeError, match="inactiva"):
        tarea.main()
    assert session.commits == 0


def test_pipeline_nunca_degrada_sistemas_a_ti():
    from pathlib import Path

    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github/workflows/deploy-development.yml"
    ).read_text(encoding="utf-8")
    assert "rol='ti'" not in workflow
    assert '"$sistemas_role" == "ti"' in workflow
    assert "python -m app.core.usuarios.promover_sistemas_superadmin_dev" in workflow
    assert '"$sistemas_role" != "super_administrador"' in workflow
