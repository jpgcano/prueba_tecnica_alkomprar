"""Etapa 1: normalizar texto.

Normalizar = dejar el texto en una forma única para poder compararlo.
"Almacén", "almacen" y "ALMACEN" deben verse iguales para las reglas.
"""
from __future__ import annotations

import re
import unicodedata


def limpiar_espacios(texto: str) -> str:
    """Quita espacios sobrantes sin cambiar el contenido.

    - Cambia el espacio "no separable" (\\xa0) por un espacio normal.
    - Deja un solo espacio donde había varios.
    - Quita los espacios del inicio y del final.
    """
    return re.sub(r"\s+", " ", texto.replace("\xa0", " ")).strip()


def quitar_tildes(texto: str) -> str:
    """'electrodomésticos' -> 'electrodomesticos' (también ñ -> n)."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    """Deja el texto listo para aplicar reglas.

    Pasos: minúsculas, sin tildes, sin signos (se conservan % y -),
    y los puntos o comas solo se conservan entre dígitos (30,5).
    """
    t = quitar_tildes(str(texto).lower())
    t = re.sub(r"[^a-z0-9%.,\- ]", " ", t)
    t = re.sub(r"(?<!\d)[.,]|[.,](?!\d)", " ", t)
    return re.sub(r"\s+", " ", t).strip()
