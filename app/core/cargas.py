import hashlib


def calcular_hash_contenido(contenido: bytes) -> str:
    """Devuelve un SHA-256 determinístico para el contenido de una carga."""
    return hashlib.sha256(contenido).hexdigest()
