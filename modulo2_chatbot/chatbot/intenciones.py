"""Etapa 3: decidir qué quiere el usuario (la "intención").

No hay IA: la decisión sale de una tabla de palabras clave y de los
parámetros que se encontraron en el mensaje. Las condiciones se revisan
en orden de prioridad y gana la primera que se cumple.
"""
from __future__ import annotations

import re

from .extractor import Parametros

# Nombres de las intenciones
PRECIO_EAN = "precio_ean"            # consulta 1
PORCENTAJE_EAN = "porcentaje_ean"    # consulta 2
TOP = "top"                          # consulta 3
UMBRAL = "umbral"                    # consulta 4
LUGAR = "lugar"                      # consulta 5
BUSCAR = "buscar"                    # extra: buscar por nombre
DESCUENTOS = "descuentos"            # "qué descuentos hay": muestra el ranking
BARATOS = "baratos"                  # extra: los más baratos o por presupuesto
SIN_DESCUENTO = "sin_descuento"      # extra: productos que no tienen descuento
CATALOGO = "catalogo"                # "qué venden": categorías
QUE_ES_EAN = "que_es_ean"
AYUDA = "ayuda"
SALUDO = "saludo"
DESPEDIDA = "despedida"
EAN_INVALIDO = "ean_invalido"
FALTA_EAN_PRECIO = "falta_ean_precio"
FALTA_EAN_PORCENTAJE = "falta_ean_porcentaje"
FALTA_PORCENTAJE = "falta_porcentaje"
FALTA_LUGAR = "falta_lugar"
FALTA_BUSQUEDA = "falta_busqueda"
DESCONOCIDA = "desconocida"

# Tabla de reglas: grupo -> palabras o frases que lo activan
PALABRAS = {
    "precio": ["precio", "precios", "cuesta", "cuestan", "vale", "valen", "valor", "costo", "cuanto es"],
    "porcentaje": ["porcentaje", "porcentajes", "por ciento", "porciento", "%", "ahorro", "ahorra",
                   "ahorras", "rebaja"],
    "descuento": ["descuento", "descuentos", "oferta", "ofertas", "promocion", "promociones", "rebajas",
                  "rebajado", "rebajados", "promo", "promos"],
    "barato": ["barato", "baratos", "barata", "baratas", "economico", "economicos", "economica",
               "economicas", "menor precio", "precio mas bajo", "presupuesto"],
    "sin_descuento": ["sin descuento", "sin descuentos", "no tienen descuento", "no tiene descuento",
                      "sin oferta", "sin ofertas", "sin rebaja"],
    "catalogo": ["venden", "vende", "catalogo", "categorias", "categoria", "que tienen", "que hay",
                 "que manejan", "que ofrecen"],
    "umbral": ["superior", "superiores", "mayor a", "mayor al", "mayor que", "mayores a", "mayores al",
               "mayores que", "mas de", "mas del", "por encima", "arriba de", "supera", "superan",
               "minimo", "desde", "menos de", "menos del", "menor a", "menor al", "menor que",
               "inferior", "inferiores", "por debajo", "entre"],
    # "hasta" no va en la lista: sola es despedida ("hasta luego"). Con número
    # ("hasta 30%") la detecta el extractor, que es quien lee la cifra.
    "top": ["top", "mayores", "mejores", "mas altos", "mas grandes", "ranking", "mayor descuento",
            "mejor descuento", "maximos", "primeros", "mayor", "mejor"],
    "bottom": ["menores", "peores", "mas bajos", "mas pequenos", "menor descuento", "peor descuento",
               "menor", "peor"],
    "lugar": ["almacen", "almacenes", "alm", "zona", "zonas"],
    "buscar": ["buscar", "busca", "busco", "buscame", "encuentra", "encontrar", "busqueda"],
    "ean": ["ean", "codigo de barras", "codigo"],
    "ayuda": ["ayuda", "ayudame", "menu", "opciones", "que puedes hacer", "como funciona",
              "que sabes hacer", "instrucciones"],
    # Palabras que indican que se habla del último producto consultado
    "seguimiento": ["tiene", "esta", "queda", "ese", "esa", "este", "mismo", "ubicado", "donde",
                    "y", "cual", "cuanto"],
    "mismo_lugar": ["ese", "esa", "este", "mismo", "mas hay"],
    "todos": ["todos", "todo", "general", "cualquiera", "sin filtro", "en general"],
    "saludo": ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey"],
    "despedida": ["gracias", "adios", "chao", "hasta luego", "nos vemos", "listo gracias"],
}


def contiene(texto: str, grupo: str) -> bool:
    """¿El texto tiene alguna palabra del grupo? (como palabra completa)"""
    for palabra in PALABRAS[grupo]:
        if re.search(rf"(?<![a-z0-9]){re.escape(palabra)}(?![a-z0-9])", texto):
            return True
    return False


def tiene_palabras_clave(texto: str) -> bool:
    return any(contiene(texto, g) for g in PALABRAS
               if g not in ("seguimiento", "mismo_lugar", "todos"))


def detectar(texto: str, p: Parametros) -> str:
    """Devuelve la intención del mensaje. `texto` ya viene normalizado."""
    # 1. Un EAN es el dato más específico: el usuario pregunta por ese producto
    if p.ean:
        pide_porcentaje = contiene(texto, "porcentaje") or contiene(texto, "descuento")
        return PORCENTAJE_EAN if pide_porcentaje else PRECIO_EAN
    if p.ean_invalido:
        return EAN_INVALIDO
    # 2. Almacén o zona
    if p.almacen or p.zona is not None:
        return LUGAR
    # 2b. Productos sin descuento, y consultas por precio ("lo más barato", "menos de 1 millón")
    if contiene(texto, "sin_descuento"):
        return SIN_DESCUENTO
    if p.precio_min is not None or p.precio_max is not None or contiene(texto, "barato"):
        return BARATOS
    # 3. Un porcentaje: "superiores al 30%", "menos de 10%", "entre 20 y 30"
    if p.porcentaje is not None or p.porcentaje_max is not None:
        return UMBRAL
    # 4. Ranking: los mayores o los menores
    if contiene(texto, "top") or contiene(texto, "bottom"):
        return TOP
    # 5. Búsqueda por nombre
    if contiene(texto, "buscar"):
        return BUSCAR if termino_busqueda(p.resto) else FALTA_BUSQUEDA
    # 6. Se reconoce el tema pero falta el dato
    if contiene(texto, "umbral"):
        return FALTA_PORCENTAJE
    if contiene(texto, "lugar"):
        return FALTA_LUGAR
    if contiene(texto, "porcentaje"):
        return FALTA_EAN_PORCENTAJE
    if contiene(texto, "precio"):
        return FALTA_EAN_PRECIO
    # 7. Preguntas generales
    if contiene(texto, "ean"):
        return QUE_ES_EAN
    if contiene(texto, "ayuda"):
        return AYUDA
    if contiene(texto, "descuento"):
        return DESCUENTOS
    if contiene(texto, "todos"):      # "todos": quita el filtro y muestra el ranking general
        return DESCUENTOS
    if contiene(texto, "catalogo"):
        return CATALOGO
    if contiene(texto, "saludo"):
        return SALUDO
    if contiene(texto, "despedida"):
        return DESPEDIDA
    return DESCONOCIDA


# Palabras que no describen un producto: se descartan al buscar por nombre.
# Incluye todas las palabras clave de la tabla de reglas.
_VACIAS = set(
    "el la los las un una unos unas de del al a en y o que por para con sin me mi tu su sus lo le se "
    "quiero quisiera necesito deseo producto productos articulo articulos hoy hay tienen tiene tienes "
    "venden vende ver dame dime muestra muestrame mostrar lista listar cual cuales son es esta estan "
    "cuanto cuanta cuantos cuantas como donde todo todos toda todas favor porfa puedes puede saber "
    "conocer consultar consulta info informacion algun alguna alguno tipo tienda si no ok ya muy mas "
    "menos este esta estos estas ese esa esos esas barras numero disponible disponibles "
    "ahora mismo actual actuales vigentes algo estoy estas estamos buscando busque ayudar regalar "
    "comprar compra compro llevar tambien solo solamente nomas unicamente cosa cosas vendes ofrecen "
    "ofrece manejan nada bien buen buena bueno gustaria interesa interesan pesos peso plata vale "
    "ahi aqui alla pues entonces oye mira eso esto aquel misma dia dias he ha han sea ser anda "
    "tendran tendra habra queria tenga tengan vi gracias".split()
)
for _grupo in PALABRAS.values():
    for _frase in _grupo:
        _VACIAS.update(_frase.split())


def termino_busqueda(resto: str) -> str:
    """Las palabras del mensaje que sí describen un producto ("nevera mabe")."""
    return " ".join(w for w in resto.split()
                     if len(w) > 1 and w not in _VACIAS and not w.isdigit())
