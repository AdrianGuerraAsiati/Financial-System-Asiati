from app.core.usuarios.errors import EmailInvalidoError, RolUsuarioInvalidoError
from app.core.usuarios.model import Usuario, UsuarioEmpresa
from app.core.usuarios.roles import (
    ROLES,
    ROLES_PRIMERA_VERSION,
    ROLES_VEN_TODAS_LAS_EMPRESAS,
    ROL_ANALISTA_TESORERIA,
    ROL_CONCILIACION,
    ROL_COORDINACION_FINANCIERA,
    ROL_SUPER_ADMINISTRADOR,
    ROL_TI,
)
from app.core.usuarios.service import crear_usuario, normalizar_email, validar_rol

__all__ = [
    "EmailInvalidoError",
    "ROLES",
    "ROLES_PRIMERA_VERSION",
    "ROLES_VEN_TODAS_LAS_EMPRESAS",
    "ROL_ANALISTA_TESORERIA",
    "ROL_CONCILIACION",
    "ROL_COORDINACION_FINANCIERA",
    "ROL_SUPER_ADMINISTRADOR",
    "ROL_TI",
    "RolUsuarioInvalidoError",
    "Usuario",
    "UsuarioEmpresa",
    "crear_usuario",
    "normalizar_email",
    "validar_rol",
]
