"""Las frases de prueba definidas en el diseño: cada una debe clasificarse bien."""
import pytest

from chatbot import intenciones as i


@pytest.mark.parametrize("frase, intencion", [
    ("precio del 7704353471953", i.PRECIO_EAN),
    ("¿Cuánto vale 7704353471953 en ALM-013?", i.PRECIO_EAN),
    ("qué porcentaje de descuento tiene 7704353471953", i.PORCENTAJE_EAN),
    ("cuánto ahorro con el 770435 3471953", i.PORCENTAJE_EAN),   # EAN con espacio
    ("top 5 descuentos", i.TOP),
    ("los mejores descuentos", i.TOP),
    ("productos con más de 50% de descuento", i.UMBRAL),
    ("descuentos superiores al 30 por ciento", i.UMBRAL),
    ("descuentos en zona 2", i.LUGAR),
    ("ofertas del almacén 7", i.LUGAR),
    ("precio", i.FALTA_EAN_PRECIO),
    ("precio del 1234567890123", i.PRECIO_EAN),                  # EAN que no existe
    ("asdf qwerty", i.DESCONOCIDA),
    ("precio 12345678", i.EAN_INVALIDO),
    ("hola", i.SALUDO),
    ("buscar nevera mabe", i.BUSCAR),
    # lenguaje de un usuario que no conoce el sistema
    ("hola, cuanto cuesta un televisor samsung?", i.BUSCAR),
    ("tienen neveras?", i.BUSCAR),
    ("iphone", i.BUSCAR),
    ("que descuentos tienen?", i.DESCUENTOS),
    ("celulares con descuento", i.DESCUENTOS),
    ("top cinco descuentos", i.TOP),
    ("los 5 peores descuentos", i.TOP),
    ("descuento del 50", i.UMBRAL),
    ("productos con menos de 10% de descuento", i.UMBRAL),
    ("descuentos entre 20 y 30%", i.UMBRAL),
    ("que almacenes hay", i.FALTA_LUGAR),
    ("que es un ean", i.QUE_ES_EAN),
    ("gracias", i.DESPEDIDA),
    ("3", i.TOP),
])
def test_intencion(bot, frase, intencion):
    assert bot.responder(frase).intencion == intencion


def test_precio_por_ean(bot):
    r = bot.responder("precio del 7704353471953")
    tabla = r.tablas[0][1]
    assert len(tabla) == 6
    assert "$ 988.900" in tabla["Precio original"].values


def test_porcentaje_por_ean(bot):
    r = bot.responder("porcentaje de descuento del 7704353471953")
    assert "23,0 %" in r.texto
    assert r.tablas[0][1].iloc[0]["Comercio"] == "Comercio3"


def test_ean_inexistente(bot):
    r = bot.responder("precio del 1234567890123")
    assert "No encontré" in r.texto and not r.tablas


def test_ean_repetido_muestra_ambos(bot):
    r = bot.responder("precio del 7702561874832")
    assert len(r.tablas) == 2 and any("repetido" in a for a in r.avisos)


def test_ean_repetido_filtra_por_almacen(bot):
    r = bot.responder("precio del 7702561874832 en ALM-003")
    assert len(r.tablas) == 1 and "Estufa" in r.texto


def test_precio_no_valido_no_muestra_valor(bot):
    tabla = bot.responder("precio 050875005891").tablas[0][1]
    fila = tabla[tabla["Comercio"] == "Comercio21"].iloc[0]
    assert fila["Precio original"] == fila["Precio con descuento"] == "Precio no válido"


def test_precio_inconsistente(bot):
    tabla = bot.responder("precio del 7706820868877").tablas[0][1]
    fila = tabla[tabla["Comercio"] == "Comercio1"].iloc[0]
    assert fila["Precio original"] == "$ 4.059.900"
    assert fila["Precio con descuento"] == "Precio inconsistente"


def test_top(bot):
    tabla = bot.responder("top 5 descuentos").tablas[0][1]
    assert len(tabla) == 5
    assert tabla["EAN"].is_unique                      # un producto no se repite
    assert tabla.iloc[0]["Descuento"] == "92,3 %"
    assert len(bot.responder("los mejores descuentos").tablas[0][1]) == 10   # por defecto
    assert len(bot.responder("top 500").tablas[0][1]) == 50                  # tope
    assert not bot.responder("top 0").tablas


def test_superiores(bot):
    r = bot.responder("descuentos superiores al 50%")
    assert len(r.descarga) == 835 and len(r.tablas[0][1]) == 20
    assert r.descarga["descuento_pct"].min() >= 50
    assert not bot.responder("superiores a 150%").tablas
    assert "Ningún producto" in bot.responder("mas de 95%").texto


def test_zona_y_almacen(bot):
    r = bot.responder("descuentos en zona 2")
    assert "1.587 productos" in r.texto and len(r.tablas) == 2
    r = bot.responder("ofertas del almacén 13")     # ALM-013 corregido en la limpieza
    assert "Zona\\_3" in r.texto and "322 productos" in r.texto
    assert "no existe" in bot.responder("zona 9").texto
    assert "no existe" in bot.responder("almacen 45").texto


def test_dato_pendiente(bot):
    r = bot.responder("porcentaje")
    assert r.pendiente == i.PORCENTAJE_EAN
    assert bot.responder("7704353471953", r.pendiente).intencion == i.PORCENTAJE_EAN
    r = bot.responder("descuentos superiores a")
    assert bot.responder("70", r.pendiente).intencion == i.UMBRAL


@pytest.mark.parametrize("entrada", [None, "", "   ", 123, "!!!", "%%%"])
def test_entradas_invalidas_no_fallan(bot, entrada):
    assert bot.responder(entrada).texto


@pytest.mark.parametrize("frase", [
    "precio del 7704353471953", "porcentaje de descuento del 7704353471953",
    "top 50", "descuentos superiores al 10%", "descuentos en zona 2", "buscar cable",
])
def test_tablas_sin_celdas_vacias(bot, frase):
    """Ninguna celda debe mostrar 'nan' o 'None' al usuario."""
    for _, tabla in bot.responder(frase).tablas:
        texto = tabla.astype(str)
        assert not texto.isin(["nan", "None", "NaN", "<NA>"]).any().any()
        assert not texto.apply(lambda col: col.str.contains(r"\(nan\)|\(None\)")).any().any()


def test_busqueda_por_nombre_muestra_precios(bot):
    r = bot.responder("cuanto cuesta un televisor samsung")
    tabla = r.tablas[0][1]
    assert {"Precio original", "Precio con descuento", "EAN"} <= set(tabla.columns)
    assert tabla["Precio original"].str.startswith("$").all()
    assert r.pendiente == i.PRECIO_EAN          # si luego escribe el EAN, ve los precios


def test_filtro_por_producto(bot):
    tabla = bot.responder("top 5 celulares").tablas[0][1]
    assert len(tabla) == 5 and tabla["Producto"].str.contains("Celular|iPhone", case=False).all()
    r = bot.responder("top 5 xyzabc")           # filtro sin coincidencias: se avisa
    assert len(r.tablas[0][1]) == 5 and any("xyzabc" in a for a in r.avisos)


def test_rangos_de_porcentaje(bot):
    menos = bot.responder("productos con menos de 10% de descuento").descarga
    assert (menos["descuento_pct"] < 10).all()
    entre = bot.responder("descuentos entre 20 y 30%").descarga
    assert entre["descuento_pct"].between(20, 30).all()
    assert len(menos) + len(entre) < len(bot.datos.ranking)


def test_menores_descuentos(bot):
    r = bot.responder("los 5 peores descuentos")
    assert "menor" in r.texto and len(r.tablas[0][1]) == 5


def test_producto_que_no_existe(bot):
    r = bot.responder("cuánto cuesta un celular nokia")     # no hay Nokia: muestra celulares y avisa
    assert r.tablas and any("nokia" in a for a in r.avisos)
    assert r.tablas[0][1]["Producto"].str.contains("Celular").all()
    r = bot.responder("precio de un unicornio")             # nada coincide: lo dice, no inventa
    assert not r.tablas and "No encontré" in r.texto
    r = bot.responder("top 5 celulares nokia")
    assert len(r.tablas[0][1]) == 5 and any("nokia" in a for a in r.avisos)


@pytest.mark.parametrize("frase, esperado", [
    ("cuánto cuesta un celular sansung", "Celular SAMSUNG"),
    ("cuánto cuesta un nevera", "Nevera"),
    ("cuánto cuesta un nebera", "Nevera"),
    ("televisores lg", "TV LG"),
])
def test_errores_de_escritura_y_sinonimos(bot, frase, esperado):
    tabla = bot.responder(frase).tablas[0][1]
    assert tabla["Producto"].str.startswith(esperado).all()
    assert tabla["Precio original"].str.startswith("$").all()


def test_despedida_no_se_confunde_con_porcentaje(bot):
    # "hasta" sola es despedida; con número sigue siendo un tope de porcentaje
    assert bot.responder("hasta luego").intencion == i.DESPEDIDA
    assert bot.responder("hasta 5%").intencion == i.UMBRAL


def test_mantiene_el_producto_entre_mensajes(bot):
    r = bot.responder("necesito una nevera")
    assert r.termino == "nevera"
    r2 = bot.responder("cual es la mas barata", ultimo_termino=r.termino)
    assert r2.tablas[0][1]["Producto"].str.startswith("Nevera").all()
    assert any("nevera" in a for a in r2.avisos)
    # "todos" quita el filtro
    r3 = bot.responder("todos", ultimo_termino=r.termino)
    assert not r3.termino and not r3.avisos


def test_seguimiento_sobre_el_ultimo_producto(bot):
    r = bot.responder("8806097671091")
    assert r.ean == "8806097671091"
    r2 = bot.responder("y el descuento?", ultimo_ean=r.ean)
    assert r2.intencion == i.PORCENTAJE_EAN and "SAMSUNG" in r2.texto


def test_una_letra_no_es_un_producto(bot):
    r = bot.responder("q descuentos hay hoy")
    assert not r.termino and len(r.tablas[0][1]) == 10
