import os

from sqlalchemy import create_engine, inspect


def test_auth_tables_exist_after_upgrade() -> None:
    inspector = inspect(create_engine(os.environ["DATABASE_URL"]))
    tablas = set(inspector.get_table_names())

    assert {
        "usuarios",
        "usuario_empresas",
        "ingresos",
        "auditoria",
        "hallazgo_mensajes",
    } <= tablas

    columnas = {c["name"] for c in inspector.get_columns("usuarios")}
    assert {
        "email",
        "password_hash",
        "debe_cambiar_password",
        "ultimo_ingreso_at",
        "creado_por",
        "creado_at",
    } <= columnas

    checks = {c["name"] for c in inspector.get_check_constraints("usuarios")}
    assert "ck_usuarios_rol" in checks
