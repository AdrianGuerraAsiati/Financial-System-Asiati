from pathlib import Path

import pytest

from app.core.permisos import (
    PERMISOS,
    Alcance,
    RecursoNoVisibleError,
    SinPermisoError,
    permisos_efectivos,
    verificar_acceso,
)
from app.core.usuarios.roles import (
    ROLES,
    ROL_ANALISTA_TESORERIA,
    ROL_CONCILIACION,
    ROL_COORDINACION_FINANCIERA,
    ROL_SUPER_ADMINISTRADOR,
    ROL_TI,
)


DOC = Path(__file__).resolve().parents[1] / "docs" / "nucleo" / "ROLES_Y_PERMISOS.md"

# Orden de las columnas de rol en la tabla de la §3.
COLUMNAS_ROL = (
    ROL_SUPER_ADMINISTRADOR,
    ROL_COORDINACION_FINANCIERA,
    ROL_CONCILIACION,
    ROL_TI,
    ROL_ANALISTA_TESORERIA,
)
CELDAS = {"Sí": Alcance.TODAS, "Asig.": Alcance.ASIGNADAS, "Leer": Alcance.TODAS, "—": None}


def _matriz_del_documento() -> dict[str, dict[str, str]]:
    seccion = DOC.read_text(encoding="utf-8").split("## 3. Matriz de permisos")[1]
    seccion = seccion.split("## 4.")[0]
    matriz: dict[str, dict[str, str]] = {}
    for linea in seccion.splitlines():
        if not linea.startswith("| `"):
            continue
        celdas = [celda.strip() for celda in linea.strip("|").split("|")]
        permiso = celdas[0].strip("`")
        matriz[permiso] = dict(zip(COLUMNAS_ROL, celdas[2:], strict=True))
    return matriz


def test_the_five_roles_match_the_check_constraint_codes() -> None:
    assert ROLES == (
        "super_administrador",
        "coordinacion_financiera",
        "conciliacion",
        "analista_tesoreria",
        "ti",
    )


def test_code_matrix_matches_the_document_matrix_exactly() -> None:
    documento = _matriz_del_documento()

    assert set(documento) == set(PERMISOS)
    for permiso, celdas in documento.items():
        esperado = {
            rol: CELDAS[celda] for rol, celda in celdas.items() if CELDAS[celda]
        }
        assert PERMISOS[permiso] == esperado, permiso


def test_read_only_cells_only_appear_on_read_permissions() -> None:
    for permiso, celdas in _matriz_del_documento().items():
        if "Leer" in celdas.values():
            assert permiso.endswith(".ver"), permiso


def test_treasury_analyst_has_no_permissions_yet() -> None:
    assert permisos_efectivos(ROL_ANALISTA_TESORERIA) == {}


@pytest.mark.parametrize(
    "permiso",
    ["movimientos.categorizar", "hallazgos.gestionar", "parametros.editar", "cartera.comprobantes.subir"],
)
def test_it_support_cannot_change_financial_data(permiso: str) -> None:
    with pytest.raises(SinPermisoError):
        verificar_acceso(ROL_TI, permiso, empresa_id=1, asignadas=frozenset())


def test_assigned_scope_hides_unassigned_company_as_not_found() -> None:
    with pytest.raises(RecursoNoVisibleError):
        verificar_acceso(
            ROL_CONCILIACION,
            "hallazgos.escalar",
            empresa_id=2,
            asignadas=frozenset({1}),
        )


def test_assigned_scope_allows_assigned_company() -> None:
    alcance = verificar_acceso(
        ROL_CONCILIACION,
        "hallazgos.escalar",
        empresa_id=1,
        asignadas=frozenset({1}),
    )

    assert alcance is Alcance.ASIGNADAS


def test_all_scope_ignores_assignments() -> None:
    alcance = verificar_acceso(
        ROL_SUPER_ADMINISTRADOR,
        "hallazgos.escalar",
        empresa_id=99,
        asignadas=frozenset(),
    )

    assert alcance is Alcance.TODAS


def test_unknown_permission_is_a_programming_error() -> None:
    with pytest.raises(KeyError):
        verificar_acceso(
            ROL_SUPER_ADMINISTRADOR,
            "permiso.inexistente",
            empresa_id=None,
            asignadas=frozenset(),
        )
