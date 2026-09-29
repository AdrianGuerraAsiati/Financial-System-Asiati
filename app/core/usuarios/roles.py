# Los códigos siguen la convención de la migración 0009 (minúsculas, snake_case).
# Fuente: docs/nucleo/ROLES_Y_PERMISOS.md §1.
ROL_SUPER_ADMINISTRADOR = "super_administrador"
ROL_COORDINACION_FINANCIERA = "coordinacion_financiera"
ROL_CONCILIACION = "conciliacion"
ROL_ANALISTA_TESORERIA = "analista_tesoreria"
ROL_TI = "ti"

# Roles activos desde el primer entregable.
ROLES_PRIMERA_VERSION = (
    ROL_SUPER_ADMINISTRADOR,
    ROL_COORDINACION_FINANCIERA,
    ROL_CONCILIACION,
)

# Todos los roles del modelo: son los valores del CHECK de usuarios.rol.
ROLES = (
    *ROLES_PRIMERA_VERSION,
    ROL_ANALISTA_TESORERIA,
    ROL_TI,
)

# Roles que ven todas las empresas sin asignación (§2).
ROLES_VEN_TODAS_LAS_EMPRESAS = (ROL_SUPER_ADMINISTRADOR, ROL_TI)
