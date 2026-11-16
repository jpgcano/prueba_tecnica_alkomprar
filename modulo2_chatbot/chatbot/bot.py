"""Une todas las etapas: recibe un texto y devuelve una Respuesta.

Este archivo no sabe nada de la interfaz. Por eso el mismo bot sirve para
la página web, para las pruebas automáticas o para cualquier otro canal.
"""
from __future__ import annotations

from . import consultas as c
from . import intenciones as i
from .consultas import Respuesta
from .datos import Datos, cargar_datos
from .extractor import extraer
from .texto import normalizar

EJEMPLOS = [
    "top 10 descuentos",
    "celulares con descuento",
    "descuentos superiores al 50%",
    "descuentos en zona 2",
    "buscar nevera mabe",
    "precio del 7704353471953",
]

MENU = (
    "Puedes escribir con tus palabras. Esto es lo que sé responder:\n\n"
    "1. **Precio de un producto** por su EAN: `precio del 7704353471953`\n"
    "2. **Porcentaje de descuento** por EAN: `porcentaje de descuento del 7704353471953`\n"
    "3. **Mayores descuentos**: `top 10 descuentos`, `top 5 celulares`\n"
    "4. **Descuentos por porcentaje**: `más de 50%`, `menos de 10%`, `entre 20 y 30%`\n"
    "5. **Descuentos por almacén o zona**: `descuentos en zona 2`, `descuentos en ALM-007`\n"
    "6. **Buscar un producto**: escribe su nombre, por ejemplo `nevera mabe`\n"
    "7. **Por precio**: `celulares baratos`, `tv de menos de 2 millones`\n\n"
    "El EAN es el código de barras del producto (11 a 14 dígitos). "
    "Si no lo sabes, escribe el nombre del producto y te lo muestro."
)

QUE_ES_EAN = (
    "El **EAN** es el código de barras del producto: un número de 11 a 14 dígitos que lo identifica. "
    "Ejemplo: `7704353471953`.\n\nSi no lo conoces, escribe el nombre del producto "
    "(por ejemplo `nevera mabe`) y te muestro su EAN."
)

PIDE_EAN = ("¿De qué producto? Escribe el EAN (código de barras) "
            "o el nombre del producto, por ejemplo `nevera mabe`.")

# Qué consulta queda "esperando" cuando falta un dato, y qué se le pide al usuario
FALTANTES = {
    i.FALTA_EAN_PRECIO: (i.PRECIO_EAN, PIDE_EAN),
    i.FALTA_EAN_PORCENTAJE: (i.PORCENTAJE_EAN, PIDE_EAN),
    i.FALTA_PORCENTAJE: (i.UMBRAL, "¿Qué porcentaje? Escribe un número entre 0 y 100, por ejemplo `50`."),
    i.FALTA_LUGAR: (i.LUGAR, "¿Cuál almacén o zona? Estos son los que existen. "
                    "Escribe por ejemplo `zona 2` o `ALM-007`."),
    i.FALTA_BUSQUEDA: (i.BUSCAR, "¿Qué producto buscas? Escribe parte del nombre o la marca."),
}

# Si el usuario escribe solo el número de una opción del menú
# Consultas que se pueden filtrar por producto ("top 5 celulares")
FILTRABLES = (i.TOP, i.DESCUENTOS, i.UMBRAL, i.BARATOS, i.SIN_DESCUENTO)

OPCIONES_MENU = {"1": i.FALTA_EAN_PRECIO, "2": i.FALTA_EAN_PORCENTAJE, "3": i.TOP,
                 "4": i.FALTA_PORCENTAJE, "5": i.FALTA_LUGAR, "6": i.FALTA_BUSQUEDA}


class Bot:
    def __init__(self, datos: Datos | None = None):
        self.datos = datos if datos is not None else cargar_datos()

    def bienvenida(self) -> Respuesta:
        return Respuesta(i.SALUDO, "Hola. Soy el asistente de precios y descuentos.\n\n" + MENU,
                         sugerencias=EJEMPLOS)

    def responder(self, mensaje, pendiente: str | None = None, ultimo_ean: str | None = None,
                  ultimo_termino: str | None = None) -> Respuesta:
        """Responde manteniendo el producto del que se viene hablando.

        Si el mensaje no nombra ningún producto ("¿cuál es la más barata?") se
        reutiliza el último ("nevera"), salvo que el usuario escriba «todos».
        El mensaje se completa con esa palabra y se resuelve por el camino normal.
        """
        propio = heredado = ""
        if isinstance(mensaje, str) and mensaje.strip():
            texto = normalizar(mensaje)
            p = extraer(texto)
            propio = i.termino_busqueda(p.resto)
            if propio:   # si traía una falta de ortografía, se guarda ya corregido
                propio = c.coincidencias(self.datos, propio)[1] or propio
            if (not propio and ultimo_termino and not i.contiene(texto, "todos")
                    and i.detectar(texto, p) in FILTRABLES):
                heredado = ultimo_termino
                mensaje = f"{mensaje} {ultimo_termino}"
        r = self._resolver(mensaje, pendiente, ultimo_ean)
        if heredado and r.tablas:
            r.avisos = [f"Sigo filtrando por «{heredado}». Escribe «todos» para quitar el filtro."
                        ] + r.avisos
        r.termino = propio or heredado
        return r

    def _resolver(self, mensaje, pendiente: str | None = None,
                  ultimo_ean: str | None = None) -> Respuesta:
        """Interpreta un mensaje y devuelve la respuesta.

        `pendiente` es la consulta que quedó esperando un dato en el mensaje
        anterior (por ejemplo, el bot preguntó "¿de qué producto?").
        `ultimo_ean` es el último producto consultado: permite seguir con
        "¿y tiene descuento?" sin repetir el código.
        """
        if not isinstance(mensaje, str) or not mensaje.strip():
            return Respuesta(i.DESCONOCIDA, "Escribe una consulta.\n\n" + MENU, sugerencias=EJEMPLOS)

        texto = normalizar(mensaje)          # Etapa 1
        p = extraer(texto)                   # Etapa 2
        intencion = i.detectar(texto, p)     # Etapa 3

        # Si el bot estaba esperando un dato y el usuario respondió solo con el dato
        retomada = False
        if pendiente and not i.tiene_palabras_clave(texto):
            if pendiente in (i.PRECIO_EAN, i.PORCENTAJE_EAN) and p.ean:
                intencion, retomada = pendiente, True
            elif pendiente == i.UMBRAL and intencion == i.DESCONOCIDA and p.numero is not None:
                p.porcentaje, p.numero, intencion, retomada = p.numero, None, i.UMBRAL, True
            elif pendiente == i.LUGAR and intencion == i.DESCONOCIDA and p.numero is not None:
                p.zona, p.numero, intencion, retomada = int(p.numero), None, i.LUGAR, True
            elif pendiente == i.BUSCAR and intencion == i.DESCONOCIDA:
                intencion, retomada = i.BUSCAR, True
        # Si escribió solo el número de una opción del menú ("3")
        if not retomada and texto in OPCIONES_MENU:
            intencion, p.numero = OPCIONES_MENU[texto], None

        d = self.datos                       # Etapas 4 y 5
        # Preguntas de seguimiento sobre el último producto consultado
        if ultimo_ean and not p.ean and not i.termino_busqueda(p.resto):
            if intencion in (i.FALTA_EAN_PRECIO, i.FALTA_EAN_PORCENTAJE):
                p.ean = ultimo_ean
                intencion = i.PRECIO_EAN if intencion == i.FALTA_EAN_PRECIO else i.PORCENTAJE_EAN
            elif intencion == i.DESCUENTOS and i.contiene(texto, "seguimiento"):
                p.ean, intencion = ultimo_ean, i.PORCENTAJE_EAN
            elif intencion == i.FALTA_LUGAR and i.contiene(texto, "seguimiento"):
                producto = d.productos[d.productos["ean"] == ultimo_ean].iloc[0]
                if c.hay(producto["almacen"]) and i.contiene(texto, "mismo_lugar"):
                    p.almacen, intencion = producto["almacen"], i.LUGAR   # "qué más hay en ese almacén"
                else:
                    p.ean, intencion = ultimo_ean, i.PRECIO_EAN           # "en qué almacén está"

        # Palabras del mensaje que describen un producto: "celulares", "nevera mabe"
        termino = i.termino_busqueda(p.resto)
        consulta_por_nombre = intencion in (i.BUSCAR, i.FALTA_EAN_PRECIO, i.FALTA_EAN_PORCENTAJE,
                                            i.QUE_ES_EAN, i.DESCONOCIDA, i.SALUDO, i.CATALOGO)
        if termino and consulta_por_nombre and p.numero is not None and p.numero == int(p.numero):
            termino += f" {int(p.numero)}"   # "iphone 16", "tv de 55 pulgadas": el número es del producto
        ids, usado, sin_coincidencias = c.coincidencias(d, termino) if termino else (None, "", [])
        filtro = dict(ids=ids, etiqueta=usado) if ids else {}

        if intencion == i.PRECIO_EAN:
            return c.por_ean(d, intencion, p.ean, p.almacen, con_porcentaje=False)
        if intencion == i.PORCENTAJE_EAN:
            return c.por_ean(d, intencion, p.ean, p.almacen, con_porcentaje=True)
        if intencion == i.BUSCAR:
            r = c.buscar(d, intencion, usado or termino or p.resto, ids or None)
            r.avisos = (sin_coincidencias if ids else []) + r.avisos
            return r

        r = None
        if intencion == i.LUGAR:
            r = c.por_lugar(d, intencion, p.zona, p.almacen, p.numero, p.porcentaje,
                            p.porcentaje_max, **filtro)
        elif intencion == i.UMBRAL:
            r = c.superiores(d, intencion, p.porcentaje, p.porcentaje_max, p.numero, **filtro)
        elif intencion == i.BARATOS:
            r = c.por_precio(d, intencion, p.numero, p.precio_min, p.precio_max, **filtro)
        elif intencion == i.SIN_DESCUENTO:
            r = c.sin_descuento(d, intencion, p.numero, **filtro)
        elif intencion in (i.TOP, i.DESCUENTOS):
            r = c.top(d, intencion, p.numero, menores=i.contiene(texto, "bottom"), **filtro)
        if r is not None:
            if termino and not ids:
                sin_coincidencias[0] += " Te muestro el resultado sin ese filtro."
            r.avisos = sin_coincidencias + r.avisos
            return r

        # El usuario nombró un producto sin EAN ("cuánto vale un televisor samsung", "nevera"):
        # se le muestran los productos que coinciden, con su EAN.
        por_nombre = (i.FALTA_EAN_PRECIO, i.FALTA_EAN_PORCENTAJE, i.QUE_ES_EAN, i.DESCONOCIDA, i.SALUDO,
                      i.CATALOGO)
        if ids and intencion in por_nombre:
            espera = FALTANTES.get(intencion, (None,))[0]
            r = c.buscar(d, i.BUSCAR, usado, ids, pendiente=espera)
            r.avisos = sin_coincidencias + r.avisos
            return r
        # Nombró un producto que no existe en los datos ("precio de un celular nokia")
        if termino and intencion in (i.FALTA_EAN_PRECIO, i.FALTA_EAN_PORCENTAJE):
            return Respuesta(i.BUSCAR, f"No encontré productos con «{termino}» en los datos. "
                             "Prueba con otra marca o con menos palabras, o escribe el EAN.",
                             sugerencias=["top 10 descuentos"], pendiente=FALTANTES[intencion][0])

        if intencion == i.EAN_INVALIDO:
            return Respuesta(intencion, f"**{p.ean_invalido}** no parece un EAN: tiene "
                             f"{len(p.ean_invalido)} dígitos y un EAN tiene entre 11 y 14. Revisa el código.",
                             pendiente=pendiente)
        if intencion in FALTANTES:
            espera, pregunta = FALTANTES[intencion]
            r = Respuesta(intencion, pregunta, pendiente=espera)
            if espera == i.LUGAR:
                r.tablas = [("", c.tabla_lugares(d))]
                r.sugerencias = ["zona 1", "zona 2", "zona 3", "zona 4"]
            return r
        if intencion == i.CATALOGO:
            return c.catalogo(d, intencion)
        if intencion == i.QUE_ES_EAN:
            return Respuesta(intencion, QUE_ES_EAN, sugerencias=["buscar nevera mabe"])
        if intencion == i.SALUDO:
            return self.bienvenida()
        if intencion == i.DESPEDIDA:
            return Respuesta(intencion, "Con gusto. Si necesitas otra consulta, aquí estoy.")
        if intencion == i.AYUDA:
            return Respuesta(intencion, MENU, sugerencias=EJEMPLOS)
        return Respuesta(i.DESCONOCIDA, "No entendí la consulta.\n\n" + MENU, sugerencias=EJEMPLOS)
