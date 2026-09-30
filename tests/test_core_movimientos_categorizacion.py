import json
from pathlib import Path

from app.core.movimientos import (
    DIMENSIONES_CATEGORIZACION,
    categorizar,
    normalizar_descripcion,
    reglas_desde_catalogo_wallets,
)


RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = (
    RAIZ
    / "docs"
    / "motores"
    / "conciliacion_wallets"
    / "catalogo_conceptos_wallets.json"
)


def _regla(**cambios):
    base = {
        "id": 1,
        "motor_slug": "prueba",
        "patron": "PAGO POR",
        "tipo_match": "EMPIEZA_CON",
        "prioridad": 10,
        "condiciones": {},
        "tipo": "INGRESO",
        "unidad_negocio": "DROPSHIPPING",
        "categoria": "VENTA",
        "empresa": None,
        "tercero": None,
        "modalidad": "WALLET",
        "fijo_variable": "VARIABLE",
        "ciudad": None,
        "requiere_revision": False,
        "activa": True,
    }
    base.update(cambios)
    return base


def test_contract_has_exactly_seven_categorization_dimensions():
    assert DIMENSIONES_CATEGORIZACION == (
        "tipo",
        "unidad_negocio",
        "categoria",
        "empresa",
        "tercero",
        "modalidad",
        "fijo_variable",
    )


def test_normalization_removes_accents_collapses_spaces_and_uppercases():
    assert normalizar_descripcion("  comisión   Bogotá  ") == "COMISION BOGOTA"


def test_first_matching_rule_by_priority_wins():
    reglas = [
        _regla(id=2, prioridad=20, categoria="GENERAL"),
        _regla(id=1, prioridad=5, patron="PAGO POR ORDEN", categoria="ORDEN"),
    ]

    resultado = categorizar("Pago por orden 123", reglas)

    assert resultado.estado == "AUTO"
    assert resultado.regla_id == 1
    assert resultado.categoria == "ORDEN"


def test_review_rule_proposes_dimensions_but_does_not_close_category():
    resultado = categorizar(
        "Ret. admin: ajuste manual",
        [
            _regla(
                patron="RET. ADMIN:",
                tipo="EGRESO",
                categoria=None,
                requiere_revision=True,
            )
        ],
        contexto={"empresa": "ASIATI"},
    )

    assert resultado.estado == "REVISAR"
    assert resultado.tipo == "EGRESO"
    assert resultado.empresa == "ASIATI"
    assert resultado.categoria is None


def test_unmatched_movement_is_pending_without_invented_dimensions():
    resultado = categorizar("concepto desconocido", [_regla()])

    assert resultado.estado == "PENDIENTE"
    assert resultado.regla is None
    assert all(
        getattr(resultado, campo) is None for campo in DIMENSIONES_CATEGORIZACION
    )


def test_conditions_use_raw_source_type_contains_and_amount_range():
    regla = _regla(
        condiciones={
            "tipo_fuente": "SALIDA",
            "contiene": "ORDEN",
            "monto_min": "100",
            "monto_max": "200",
        },
        tipo="EGRESO",
    )

    assert (
        categorizar(
            "Pago por orden 123",
            [regla],
            tipo_fuente="SALIDA",
            monto="150",
        ).estado
        == "AUTO"
    )
    assert (
        categorizar(
            "Pago por orden 123",
            [regla],
            tipo_fuente="ENTRADA",
            monto="150",
        ).estado
        == "PENDIENTE"
    )


def test_wallet_catalog_is_adapted_without_redefining_its_business_rules():
    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    reglas = reglas_desde_catalogo_wallets(catalogo)

    assert len(reglas) == len(catalogo["conceptos"])
    assert reglas[0].prioridad == 1
    assert reglas[0].condiciones["tipo_fuente"] == catalogo["conceptos"][0]["tipo"]
    assert reglas[0].modalidad == "WALLET"
    assert reglas[0].fijo_variable == "VARIABLE"


def test_wallet_transfer_uses_catalog_output_and_contextual_dimensions():
    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    reglas = reglas_desde_catalogo_wallets(catalogo)
    resultado = categorizar(
        "SALIDA POR TRANSFERENCIA DE WALLET AL USUARIO prov@x.co",
        reglas,
        tipo_fuente="SALIDA",
        contexto={"empresa": "ASIATI", "tercero": "prov@x.co"},
    )

    assert resultado.estado == "REVISAR"
    assert resultado.tipo == "EGRESO"
    assert resultado.empresa == "ASIATI"
    assert resultado.tercero == "prov@x.co"
