from app.core.cargas import calcular_hash_contenido


def test_same_file_content_produces_same_hash() -> None:
    contenido = b"wallet,order,amount\nA,1001,25000\n"

    assert calcular_hash_contenido(contenido) == calcular_hash_contenido(contenido)


def test_different_file_content_produces_different_hash() -> None:
    original = b"wallet,order,amount\nA,1001,25000\n"
    cambiado = b"wallet,order,amount\nA,1001,26000\n"

    assert calcular_hash_contenido(original) != calcular_hash_contenido(cambiado)
