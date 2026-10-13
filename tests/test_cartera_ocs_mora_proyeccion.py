from datetime import date
from decimal import Decimal

from app.motores.cartera_ocs.mora import normalizar_fila_mora
from app.motores.cartera_ocs.proyeccion import (
    normalizar_fila_proyeccion,
    parsear_fecha_proyeccion,
)


def test_normaliza_fila_de_mora_con_los_encabezados_actuales() -> None:
    registro = normalizar_fila_mora(
        {
            "Cliente": "Cliente A",
            "Empresa / Subtítulo": "Empresa A",
            "Monto en mora (USD)": "USD 4.300,00",
            "Observación más reciente": "Pendiente compromiso de pago",
            "CARTERA": "mora",
        }
    )

    assert registro is not None
    assert registro.cliente == "Cliente A"
    assert registro.empresa == "Empresa A"
    assert registro.monto == Decimal("4300.00")
    assert registro.observacion == "Pendiente compromiso de pago"
    assert registro.estado == "MORA"


def test_mora_descarta_filas_sin_cliente() -> None:
    assert normalizar_fila_mora(
        {
            "Cliente": "",
            "Monto en mora (USD)": 100,
            "CARTERA": "MORA",
        }
    ) is None


def test_parsea_los_tres_formatos_de_fecha_usados_por_proyecciones() -> None:
    assert parsear_fecha_proyeccion("2026-10-15") == date(2026, 10, 15)
    assert parsear_fecha_proyeccion("15/10/2026") == date(2026, 10, 15)
    assert parsear_fecha_proyeccion("Date(2026,9,15)") == date(2026, 10, 15)


def test_normaliza_proyeccion_con_fallbacks_del_tablero_actual() -> None:
    registro = normalizar_fila_proyeccion(
        {
            "NOMBRE": "",
            "CLIENTE": "Cliente Alterno",
            "DESCRIPCION": "Producto A",
            "SKU": "SKU-01",
            "NUMERO OC": "OC-123",
            "PAIS ORIGEN": "",
            "ESTADO": "En camino",
            "DOCUMENTO DE TRANSPORTE": "DOC-9",
            "NEGOCIACION": "Crédito",
            "DIAS": "30",
            "VALOR OCI (DDP)": "10.000,00",
            "FECHA DE PAGO ESPERADA": "2026-10-15",
            "MONTO ESPERADO": "4.300,00",
            "COMERCIAL": "",
        }
    )

    assert registro is not None
    assert registro.cliente == "Cliente Alterno"
    assert registro.contacto == "Cliente Alterno"
    assert registro.pais == "Sin país"
    assert registro.comercial == "SIN ASIGNAR"
    assert registro.fecha == date(2026, 10, 15)
    assert registro.monto == Decimal("4300.00")
    assert registro.mes == "2026-10"


def test_proyeccion_descarta_filas_sin_fecha_o_sin_monto_positivo() -> None:
    assert normalizar_fila_proyeccion(
        {
            "NOMBRE": "Cliente A",
            "FECHA DE PAGO ESPERADA": "",
            "MONTO ESPERADO": 100,
        }
    ) is None

    assert normalizar_fila_proyeccion(
        {
            "NOMBRE": "Cliente A",
            "FECHA DE PAGO ESPERADA": "2026-10-15",
            "MONTO ESPERADO": 0,
        }
    ) is None


def test_proyeccion_lee_valor_oci_calculado_de_la_hoja_real() -> None:
    registro = normalizar_fila_proyeccion(
        {
            "NUMERO OC": "OC-SINTETICA",
            "NOMBRE": "Cliente Sintetico",
            "FECHA DE PAGO ESPERADA": "2026-10-15",
            "MONTO ESPERADO": "700,00",
            "VALOR OCI": "1.000,00",
            "VALOR OCI (DDP)": "900,00",
        }
    )

    assert registro is not None
    # El valor corregido prevalece sobre el DDP original importado.
    assert registro.valor_oc == Decimal("1000.00")
    assert registro.monto == Decimal("700.00")


def test_proyeccion_acepta_encabezado_legacy_si_valor_oci_esta_vacio() -> None:
    registro = normalizar_fila_proyeccion(
        {
            "NOMBRE": "Cliente Sintetico",
            "FECHA DE PAGO ESPERADA": "2026-10-15",
            "MONTO ESPERADO": "600,00",
            "VALOR OCI": "",
            "VALOR OCI (DDP)": "1.200,00",
        }
    )

    assert registro is not None
    assert registro.valor_oc == Decimal("1200.00")


def test_proyeccion_no_sustituye_cero_calculado_con_ddp_original() -> None:
    registro = normalizar_fila_proyeccion(
        {
            "NOMBRE": "Cliente Sintetico",
            "FECHA DE PAGO ESPERADA": "2026-10-15",
            "MONTO ESPERADO": "600,00",
            "VALOR OCI": 0,
            "VALOR OCI (DDP)": "1.200,00",
        }
    )

    assert registro is not None
    assert registro.valor_oc == Decimal("0")
