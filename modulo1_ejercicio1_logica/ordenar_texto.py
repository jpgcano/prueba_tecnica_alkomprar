"""Módulo 1 - Ejercicio 1: limpiar y ordenar las letras de un texto.

Ejecutar:  python ejercicio1/ordenar_texto.py
"""

MENSAJE_ERROR = "Texto no valido"


def ordenar_texto(texto):
    """Devuelve las letras del texto (a-z) en minúscula y en orden alfabético.

    Pasos:
    1. Validar que sea una cadena de texto y que no esté vacía.
    2. Quedarse solo con las letras de la a a la z (sin tildes ni ñ);
       así se eliminan espacios, números y caracteres especiales.
    3. Pasar cada letra a minúscula.
    4. Si no quedó ninguna letra, el texto no es válido.
    5. Ordenar de la a a la z y unir en una sola cadena.
    """
    if not isinstance(texto, str) or texto == "":
        return MENSAJE_ERROR
    letras = [c.lower() for c in texto if c.isascii() and c.isalpha()]
    if not letras:
        return MENSAJE_ERROR
    return "".join(sorted(letras))


if __name__ == "__main__":
    ejemplos = ["Hola mundo!", "Prueba", 123, "A!b#C", None, "", "   ", "1234 #!", "Añó Ñandú"]
    for ejemplo in ejemplos:
        print(f"{ejemplo!r:15} -> {ordenar_texto(ejemplo)!r}")
