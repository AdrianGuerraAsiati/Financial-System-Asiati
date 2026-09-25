class PeriodoCerradoError(RuntimeError):
    """La operación requiere un período abierto."""

    pass


class PeriodoAbiertoError(RuntimeError):
    """La operación requiere un período cerrado."""

    pass


class MotivoReaperturaRequeridoError(ValueError):
    """Toda reapertura debe registrar un motivo no vacío."""

    pass
