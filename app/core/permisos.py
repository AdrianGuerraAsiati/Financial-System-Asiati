"""Matriz de permisos del núcleo (docs/nucleo/ROLES_Y_PERMISOS.md §3).

La matriz vive en código. Un rol o un permiso nuevo se agrega aquí y en el
documento; el test tests/test_permisos_matriz.py exige que coincidan.
"""
from enum import Enum

from app.core.usuarios.roles import (
    ROL_CONCILIACION,
    ROL_COORDINACION_FINANCIERA,
    ROL_SUPER_ADMINISTRADOR,
    ROL_TI,
)


class Alcance(str, Enum):
    TODAS = "TODAS"
    ASIGNADAS = "ASIGNADAS"


class SinPermisoError(Exception):
    """El rol no tiene el permiso pedido."""


class RecursoNoVisibleError(Exception):
    """El recurso es de una empresa no asignada; se responde como inexistente."""


_SA = ROL_SUPER_ADMINISTRADOR
_CO = ROL_COORDINACION_FINANCIERA
_CN = ROL_CONCILIACION
_TODAS = Alcance.TODAS
_ASIG = Alcance.ASIGNADAS

# "Leer" en el documento se representa como TODAS: solo aparece en permisos de
# consulta, que por sí mismos no cambian datos.
PERMISOS: dict[str, dict[str, Alcance]] = {
    "usuarios.gestionar": {_SA: _TODAS},
    "empresas.gestionar": {_SA: _TODAS},
    "parametros.editar": {_SA: _TODAS},
    "parametros.ver": {_SA: _TODAS, _CO: _TODAS, _CN: _ASIG, ROL_TI: _TODAS},
    "cargas.subir": {_SA: _TODAS, _CN: _ASIG},
    "cargas.eliminar": {_SA: _TODAS, _CN: _ASIG},
    "conciliacion.ejecutar": {_SA: _TODAS, _CN: _ASIG},
    "conciliacion.ver": {_SA: _TODAS, _CO: _ASIG, _CN: _ASIG, ROL_TI: _TODAS},
    "cartera.ver": {_SA: _TODAS, _CO: _ASIG, _CN: _ASIG, ROL_TI: _TODAS},
    "cartera.comprobantes.subir": {_SA: _TODAS, _CN: _ASIG},
    "movimientos.categorizar": {_SA: _TODAS, _CO: _ASIG, _CN: _ASIG},
    "reglas.crear": {_SA: _TODAS, _CO: _ASIG, _CN: _ASIG},
    "hallazgos.gestionar": {_SA: _TODAS, _CO: _ASIG, _CN: _ASIG},
    "hallazgos.escalar": {_SA: _TODAS, _CN: _ASIG},
    "hallazgos.responder_escalado": {_SA: _TODAS, _CO: _ASIG},
    "periodos.cerrar": {_SA: _TODAS, _CO: _ASIG},
    "periodos.reabrir": {_SA: _TODAS},
    "supervision.ver": {_SA: _TODAS, _CO: _ASIG},
    "auditoria.ver": {_SA: _TODAS, _CO: _ASIG, ROL_TI: _TODAS},
    "exportar": {_SA: _TODAS, _CO: _ASIG, _CN: _ASIG},
    "sistema.ver": {_SA: _TODAS, ROL_TI: _TODAS},
    "sistema.reprocesar": {_SA: _TODAS, ROL_TI: _TODAS},
}


def permisos_efectivos(rol: str) -> dict[str, Alcance]:
    """Permisos que tiene un rol, con su alcance."""
    return {
        permiso: roles[rol]
        for permiso, roles in PERMISOS.items()
        if rol in roles
    }


def verificar_acceso(
    rol: str,
    permiso: str,
    *,
    empresa_id: int | None,
    asignadas: frozenset[int],
) -> Alcance:
    """Devuelve el alcance del rol para el permiso o levanta el error que aplica.

    Con alcance ASIGNADAS y un recurso de empresa no asignada levanta
    RecursoNoVisibleError, que la API responde como 404.
    """
    alcance = PERMISOS[permiso].get(rol)
    if alcance is None:
        raise SinPermisoError(permiso)
    if (
        alcance is Alcance.ASIGNADAS
        and empresa_id is not None
        and empresa_id not in asignadas
    ):
        raise RecursoNoVisibleError(permiso)
    return alcance
