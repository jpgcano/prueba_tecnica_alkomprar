"""Configuración de pytest para todo el proyecto.

Cada módulo de la prueba vive en su propia carpeta. Aquí se agregan esas carpetas
a la ruta de búsqueda de Python para que las pruebas puedan importar su código,
y se carga el chatbot una sola vez para todas las pruebas que lo necesitan.
"""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent
for carpeta in ("modulo1_ejercicio1_logica", "modulo2_chatbot"):
    sys.path.insert(0, str(RAIZ / carpeta))


@pytest.fixture(scope="session")
def bot():
    """El chatbot con los datos ya cargados y limpios (se hace una sola vez)."""
    from chatbot.bot import Bot
    return Bot()
