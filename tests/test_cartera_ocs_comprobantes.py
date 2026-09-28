from datetime import date

from app.motores.cartera_ocs.comprobantes import radicar_comprobante
from app.motores.cartera_ocs.financiacion import (
    OperacionFinanciada,
    generar_condicion_pago,
)


def _condicion():
    return generar_condicion_pago(
        OperacionFinanciada(
            oc="OC-123",
            cliente="Cliente A",
            pais="COLOMBIA",
            valor_ddp=10000,
            tipo_negociacion="50% anticipo / 50% pago a 30 días",
            fecha_entrega=date(2026, 9, 10),
            comercial="COMERCIAL A",
        )
    )


def test_radica_comprobante_en_estado_pendiente_y_lo_vincula_a_la_operacion() -> None:
    comprobante = radicar_comprobante(
        condicion=_condicion(),
        nombre_archivo="comprobante-oc-123.pdf",
        contenido=b"contenido del comprobante",
    )

    assert comprobante.oc == "OC-123"
    assert comprobante.cliente == "Cliente A"
    assert comprobante.pais == "COLOMBIA"
    assert comprobante.comercial == "COMERCIAL A"
    assert comprobante.monto_esperado == 5000
    assert comprobante.nombre_archivo == "comprobante-oc-123.pdf"
    assert comprobante.estado_auditoria == "PENDIENTE"


def test_identifica_el_archivo_por_hash_deterministico_del_nucleo() -> None:
    primero = radicar_comprobante(
        condicion=_condicion(),
        nombre_archivo="comprobante.pdf",
        contenido=b"mismo contenido",
    )
    segundo = radicar_comprobante(
        condicion=_condicion(),
        nombre_archivo="otro-nombre.pdf",
        contenido=b"mismo contenido",
    )

    assert primero.contenido_hash == segundo.contenido_hash
    assert len(primero.contenido_hash) == 64


def test_el_comprobante_no_se_aprueba_automaticamente_al_radicarlo() -> None:
    comprobante = radicar_comprobante(
        condicion=_condicion(),
        nombre_archivo="pago.png",
        contenido=b"imagen",
    )

    assert comprobante.estado_auditoria == "PENDIENTE"
