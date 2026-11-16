# Módulo 1, ejercicio 1 — Lógica: limpiar y ordenar un texto

## Qué pide el enunciado

Una función que reciba una cadena de texto y devuelva una nueva cadena con sus caracteres
ordenados alfabéticamente de la A a la Z. Antes de ordenar debe eliminar espacios, números y
caracteres especiales, y pasar todo a minúsculas. Si la cadena es nula, está vacía, no es texto,
o no queda ninguna letra después de limpiar, debe devolver `Texto no valido`.

## La solución

`ordenar_texto(texto)`, en [`ordenar_texto.py`](ordenar_texto.py). Son cinco pasos:

1. Validar que sea una cadena de texto y que no esté vacía.
2. Quedarse solo con las letras de la `a` a la `z` (sin tildes ni `ñ`). Con eso desaparecen de una
   vez los espacios, los números y los caracteres especiales: no hace falta tratarlos por separado.
3. Pasar cada letra a minúscula.
4. Si no quedó ninguna letra, el texto no es válido.
5. Ordenar y unir en una sola cadena.

La decisión que explica el código: en vez de **quitar** lo que sobra, se **conserva** solo lo que
sirve. Una lista de caracteres prohibidos siempre se queda corta; una lista de permitidos, no.

## Casos probados

| Entrada | Salida | Por qué |
|---|---|---|
| `"Hola mundo!"` | `adhlmnoou` | Ejemplo del enunciado |
| `"Prueba"` | `abepru` | Ejemplo del enunciado |
| `123` | `Texto no valido` | No es una cadena de texto |
| `"A!b#C"` | `abc` | Ejemplo del enunciado |
| `None` | `Texto no valido` | Valor nulo |
| `""` | `Texto no valido` | Cadena vacía |
| `"   "` | `Texto no valido` | Solo espacios: no queda ninguna letra |
| `"1234 #!"` | `Texto no valido` | Solo números y símbolos |
| `["a", "b"]` | `Texto no valido` | No es una cadena de texto |
| `"zZaA"` | `aazz` | Las mayúsculas pasan a minúsculas |
| `"ñandú"` | `adn` | La `ñ` y las tildes no son letras válidas |

## Cómo ejecutarlo

Desde la raíz del proyecto:

```bash
python modulo1_ejercicio1_logica/ordenar_texto.py   # imprime los ejemplos de arriba
pytest modulo1_ejercicio1_logica                    # ejecuta las 11 pruebas
```

## Entregable

El enunciado pide una captura de la solución: está en [`captura.png`](captura.png), con el código
y su salida.
