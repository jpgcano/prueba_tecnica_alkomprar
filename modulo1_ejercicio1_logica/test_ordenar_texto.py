import pytest

from ordenar_texto import ordenar_texto


@pytest.mark.parametrize("entrada, esperado", [
    ("Hola mundo!", "adhlmnoou"),      # ejemplos del enunciado
    ("Prueba", "abepru"),
    (123, "Texto no valido"),
    ("A!b#C", "abc"),
    (None, "Texto no valido"),         # nulo
    ("", "Texto no valido"),           # vacío
    ("   ", "Texto no valido"),        # solo espacios
    ("1234 #!", "Texto no valido"),    # no queda ninguna letra
    (["a", "b"], "Texto no valido"),   # no es una cadena
    ("ñandú", "adn"),                  # ñ y tildes no son letras válidas
    ("zZaA", "aazz"),                  # mayúsculas pasan a minúsculas
])
def test_ordenar_texto(entrada, esperado):
    assert ordenar_texto(entrada) == esperado
