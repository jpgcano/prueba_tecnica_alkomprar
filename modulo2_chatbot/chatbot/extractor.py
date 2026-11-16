"""Etapa 2: sacar del mensaje los datos concretos (parámetros).

Se usan expresiones regulares (regex): patrones que encuentran texto con
cierta forma, por ejemplo "13 dígitos seguidos".

El orden importa. Cada dato encontrado se borra del texto antes de buscar
el siguiente, para que un pedazo de EAN no se confunda con una cantidad.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Números escritos con letras: "top cinco" -> "top 5"
NUMEROS = {"dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
           "nueve": 9, "diez": 10, "quince": 15, "veinte": 20, "treinta": 30, "cuarenta": 40,
           "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90, "cien": 100}
RE_NUMERO_EN_LETRAS = re.compile(r"\b(" + "|".join(NUMEROS) + r")\b")

_N = r"(-?\d+(?:[.,]\d+)?)"                       # un número, con o sin decimales
_PCT = r"(?:\s*(?:%|por ciento|porciento))?"       # el signo de porcentaje, opcional

RE_EAN = re.compile(r"(?<!\d)\d{11,14}(?!\d)")
RE_EAN_CON_ESPACIO = re.compile(r"(?<!\d)(\d{5,8}) (\d{5,8})(?!\d)")
RE_NUMERO_LARGO = re.compile(r"(?<!\d)\d{7,}(?!\d)")
RE_ALMACEN = re.compile(r"\b(?:almacenes|almacen|alm)\s*(?:numero|num|no|n)?\s*-?\s*(\d{1,3})\b")
RE_ZONA = re.compile(r"\bzonas?\s*(?:numero|num|no|n)?\s*-?\s*(\d{1,3})\b")
# "entre 20 y 30%": un rango
RE_ENTRE = re.compile(rf"\bentre(?: el| un| los)?\s*{_N}{_PCT}\s*(?:y|a)(?: el| un)?\s*{_N}{_PCT}")
# "menos de 10%", "hasta 30": un tope máximo
RE_MAXIMO = re.compile(
    r"\b(?:no mas de|menos de|menos del|menor(?:es)? (?:a|al|que|de|del)|inferior(?:es)? (?:a|al)|"
    r"por debajo (?:de|del)|hasta|maximo(?: de| del)?)"
    rf"(?: el| un| los)?\s*{_N}{_PCT}(?![\d.,])")
# "30%", "30 por ciento": un mínimo con signo
RE_PORCENTAJE = re.compile(rf"{_N}\s*(?:%|por ciento|porciento)")
# "mas de 30", "superior a 30", "descuento del 50": un mínimo aunque no traiga el signo %
RE_UMBRAL = re.compile(
    r"\b(?:mas de|mas del|mayor(?:es)? (?:a|al|que|de|del)|superior(?:es)? (?:a|al)|"
    r"por encima (?:de|del)|arriba (?:de|del)|supera(?:n)?|minimo(?: de| del)?|desde|"
    r"descuentos? (?:de|del|al)|(?:estan|esta|tienen|tiene|con) (?:al|el))"
    rf"(?: el| un| los)?\s*{_N}(?![\d.,])")
RE_NUMERO = re.compile(r"(?<![\w.,-])(-?\d+(?:[.,]\d+)?)(?![\w.,])")
RE_TOP_PEGADO = re.compile(r"\btop(\d+)\b")                      # "top3" -> "top 3"
# Precios: "1 millon", "500 mil", "800k", "1.500.000", "300000"
RE_PRECIO_UNIDAD = re.compile(rf"{_N}\s*(millones|millon|mil|k)\b")
RE_PRECIO_NUMERO = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d{3})+|\d{4,6})(?![\d.])(?:\s*pesos)?")
RE_PRECIO_LARGO = re.compile(r"(?<![\w.])(\d{7,10})(?![\d.])(\s*pesos)?")
_FRASE_MIN = r"(?:mas de|desde|minimo(?: de)?|por encima de|superior(?:es)? a|mayor(?:es)? (?:a|de|que))"
_FRASE_MAX = (r"(?:no mas de|menos de|hasta|maximo(?: de)?|por debajo de|inferior(?:es)? a|"
              r"menor(?:es)? (?:a|de|que))")
RE_ANTES_MIN = re.compile(_FRASE_MIN + r"(?: los| unos)?\s*$")
RE_ANTES_MAX = re.compile(_FRASE_MAX + r"(?: los| unos)?\s*$")
UNIDADES = {"millones": 1_000_000, "millon": 1_000_000, "mil": 1_000, "k": 1_000}


@dataclass
class Parametros:
    ean: str | None = None             # código de barras válido (11 a 14 dígitos)
    ean_invalido: str | None = None    # número largo que no tiene forma de EAN
    almacen: str | None = None         # siempre con la forma "ALM-007"
    zona: int | None = None
    porcentaje: float | None = None    # descuento mínimo ("más de 30%")
    porcentaje_max: float | None = None  # descuento máximo ("menos de 10%")
    precio_min: float | None = None    # presupuesto: "más de 1 millón"
    precio_max: float | None = None    # presupuesto: "menos de 500 mil"
    numero: float | None = None        # número suelto: la cantidad "n" del top
    resto: str = ""                    # el texto que quedó sin los datos


def _a_float(texto: str) -> float:
    return float(texto.replace(",", "."))


def extraer(texto: str) -> Parametros:
    """Recibe el texto ya normalizado y devuelve los parámetros encontrados."""
    p = Parametros()
    texto = RE_NUMERO_EN_LETRAS.sub(lambda m: str(NUMEROS[m.group(1)]), texto)
    texto = RE_TOP_PEGADO.sub(r"top \1", texto)

    def tomar(patron):
        """Busca el patrón; si aparece, lo borra del texto y lo devuelve."""
        nonlocal texto
        m = patron.search(texto)
        if m:
            texto = texto[:m.start()] + " " + texto[m.end():]
        return m

    # 1. EAN
    m = tomar(RE_EAN)
    if m:
        p.ean = m.group(0)
    else:
        m = RE_EAN_CON_ESPACIO.search(texto)
        if m and 11 <= len(m.group(1) + m.group(2)) <= 14:
            p.ean = m.group(1) + m.group(2)
            texto = texto[:m.start()] + " " + texto[m.end():]
    # 1b. Precio (presupuesto). Va antes del "número largo" para no confundirlo con un EAN.
    valor, m = None, RE_PRECIO_UNIDAD.search(texto)
    if m:
        valor = _a_float(m.group(1)) * UNIDADES[m.group(2)]
    else:
        m = RE_PRECIO_NUMERO.search(texto)
        if m:
            valor = float(m.group(1).replace(".", ""))
        else:
            m = RE_PRECIO_LARGO.search(texto)
            con_contexto = m and (m.group(2) or RE_ANTES_MIN.search(texto[:m.start()])
                                  or RE_ANTES_MAX.search(texto[:m.start()]))
            if con_contexto:
                valor = float(m.group(1))
            else:
                m = None
    if m and valor:
        antes = texto[:m.start()]
        frase = RE_ANTES_MIN.search(antes)
        if frase:
            p.precio_min = valor
        else:
            frase = RE_ANTES_MAX.search(antes)
            p.precio_max = valor
        inicio = frase.start() if frase else m.start()
        texto = texto[:inicio] + " " + texto[m.end():]

    if p.ean is None:
        m = tomar(RE_NUMERO_LARGO)
        if m:
            p.ean_invalido = m.group(0)

    # 2. Almacén y 3. zona
    m = tomar(RE_ALMACEN)
    if m:
        p.almacen = f"ALM-{int(m.group(1)):03d}"
    m = tomar(RE_ZONA)
    if m:
        p.zona = int(m.group(1))

    # 4. Porcentaje: rango, máximo o mínimo (se prueba en ese orden)
    m = tomar(RE_ENTRE)
    if m:
        a, b = _a_float(m.group(1)), _a_float(m.group(2))
        p.porcentaje, p.porcentaje_max = min(a, b), max(a, b)
    else:
        m = tomar(RE_MAXIMO)
        if m:
            p.porcentaje_max = _a_float(m.group(1))
        else:
            m = tomar(RE_PORCENTAJE)
            if m:
                p.porcentaje = _a_float(m.group(1))
            else:
                m = RE_UMBRAL.search(texto)
                if m:
                    p.porcentaje = _a_float(m.group(1))
                    texto = texto[:m.start(1)] + " " + texto[m.end(1):]

    # 5. Número suelto (la "n" de "top 5")
    m = tomar(RE_NUMERO)
    if m:
        p.numero = _a_float(m.group(1))

    p.resto = re.sub(r"\s+", " ", texto).strip()
    return p
