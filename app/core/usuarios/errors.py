class RolUsuarioInvalidoError(ValueError):
    """Se intenta registrar un usuario con un rol no definido."""


class EmailInvalidoError(ValueError):
    """El correo del usuario no tiene un formato válido."""
