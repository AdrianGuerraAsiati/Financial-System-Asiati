from datetime import date
from decimal import Decimal


def estado_factura(monto: Decimal, abonos: list[Decimal], vencimiento: date | None, hoy: date) -> dict:
    pagado = sum(abonos, Decimal('0.00'))
    saldo = monto - pagado
    if saldo < 0:
        raise ValueError('Los pagos exceden la factura')
    estado = 'PAGADA' if saldo == 0 else 'PARCIAL' if pagado else 'PENDIENTE_VALIDACION' if vencimiento is None else 'VENCIDA' if vencimiento < hoy else 'PENDIENTE'
    alerta = None if saldo == 0 else 'REVISAR_VENCIMIENTO' if vencimiento is None else 'VENCIDA' if vencimiento < hoy else None
    return {'estado': estado, 'alerta': alerta, 'pagado': format(pagado, '.2f'), 'saldo': format(saldo, '.2f')}
