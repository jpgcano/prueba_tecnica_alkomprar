"""Etapas 4 y 5: validar, consultar los datos y armar la respuesta.

Cada función responde un tipo de consulta. Todas devuelven una `Respuesta`
con la misma forma: una frase, tablas y avisos. La interfaz solo la dibuja.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

import pandas as pd

from .datos import CON_DESCUENTO, INCONSISTENTE, NO_VALIDO, SIN_DESCUENTO, Datos
from .texto import normalizar

TOP_POR_DEFECTO = 10
TOP_MAXIMO = 50
FILAS_UMBRAL = 20
TOP_LUGAR = 5


@dataclass
class Respuesta:
    intencion: str
    texto: str                                    # frase principal (Markdown)
    tablas: list = field(default_factory=list)    # lista de (título, DataFrame)
    avisos: list = field(default_factory=list)    # advertencias para el usuario
    sugerencias: list = field(default_factory=list)  # frases para botones
    descarga: pd.DataFrame | None = None          # tabla completa para bajar en CSV
    nombre_descarga: str = ""
    pendiente: str | None = None                  # consulta que quedó esperando un dato
    ean: str | None = None                        # producto consultado (para "¿y tiene descuento?")
    termino: str = ""                             # producto filtrado (para "¿y la más barata?")


# ---------- formato ----------

def dinero(valor: float) -> str:
    return "$ " + f"{valor:,.0f}".replace(",", ".")


def porcentaje(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",") + " %"


def entero(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def md(texto: str) -> str:
    """Escapa símbolos para que Markdown no los tome como formato."""
    return re.sub(r"([\\*_$\[\]`~|])", r"\\\1", str(texto))


def hay(valor) -> bool:
    """¿La celda tiene un dato? (None y NaN cuentan como vacío)"""
    return valor is not None and not pd.isna(valor)


def _comercio(fila) -> str:
    return f"{fila.comercio} ({fila.vendedor})" if hay(fila.vendedor) else fila.comercio


def _lugar(prod) -> str:
    if not hay(prod.almacen):
        return "sin almacén registrado"
    if not hay(prod.zona):
        return prod.almacen
    return f"{prod.almacen} ({prod.nombre_almacen}, {prod.zona})"


def _tabla_ranking(filas: pd.DataFrame) -> pd.DataFrame:
    # Los precios van junto al producto para que se vean sin desplazar la tabla
    return pd.DataFrame({
        "#": range(1, len(filas) + 1),
        "Producto": filas["producto"].values,
        "Precio original": [dinero(v) for v in filas["precio_original"]],
        "Precio con descuento": [dinero(v) for v in filas["precio_descuento"]],
        "Descuento": [porcentaje(v) for v in filas["pct"]],
        "Comercio": [_comercio(f) for f in filas.itertuples()],
        "EAN": filas["ean"].values,
        "Almacén": [a if hay(a) else "—" for a in filas["almacen"]],
        "Zona": [z if hay(z) else "—" for z in filas["zona"]],
    })


def _tabla_csv(filas: pd.DataFrame) -> pd.DataFrame:
    """La misma información del ranking pero con números, para abrir en Excel."""
    return pd.DataFrame({
        "producto": filas["producto"].values, "ean": filas["ean"].values,
        "descuento_pct": filas["pct"].round(2).values, "comercio": filas["comercio"].values,
        "vendedor": filas["vendedor"].values, "precio_original": filas["precio_original"].values,
        "precio_descuento": filas["precio_descuento"].values,
        "almacen": filas["almacen"].values, "zona": filas["zona"].values,
    })


# ---------- consultas 1 y 2: por EAN ----------

def _tabla_ofertas(ofertas: pd.DataFrame, con_porcentaje: bool) -> pd.DataFrame:
    filas = []
    for o in ofertas.itertuples():
        if o.estado == NO_VALIDO:
            original = con_desc = "Precio no válido"
        elif o.estado == INCONSISTENTE:
            original, con_desc = dinero(o.precio_original), "Precio inconsistente"
        elif o.estado == SIN_DESCUENTO:
            original, con_desc = dinero(o.precio_original), "Sin descuento"
        else:
            original, con_desc = dinero(o.precio_original), dinero(o.precio_descuento)
        fila = {"Comercio": o.comercio, "Vendedor": o.vendedor if hay(o.vendedor) else "—",
                "Precio original": original, "Precio con descuento": con_desc}
        if con_porcentaje:
            fila["Descuento"] = porcentaje(o.pct) if o.estado == CON_DESCUENTO else "—"
        filas.append(fila)
    return pd.DataFrame(filas)


def por_ean(datos: Datos, intencion: str, ean: str, almacen: str | None, con_porcentaje: bool) -> Respuesta:
    prods = datos.productos[datos.productos["ean"] == ean]
    if prods.empty:
        return Respuesta(intencion, f"No encontré ningún producto con el EAN **{ean}**. "
                         "Revisa el código, o busca el producto por nombre: `buscar nevera`.")
    avisos = []
    if almacen:
        en_almacen = prods[prods["almacen"] == almacen]
        if en_almacen.empty:
            avisos.append(f"El EAN {ean} no está en {almacen}. Te muestro dónde sí está.")
        else:
            prods = en_almacen
    if len(prods) > 1:
        avisos.append(
            f"El EAN {ean} está repetido en los datos: corresponde a {len(prods)} productos distintos. "
            f"Te muestro todos. Puedes filtrar agregando el almacén, por ejemplo: "
            f"«precio del {ean} en {prods.iloc[0]['almacen']}».")

    tablas, frases = [], []
    hay_no_valido = hay_inconsistente = False
    for prod in prods.itertuples():
        ofertas = datos.ofertas[datos.ofertas["id_producto"] == prod.id_producto]
        orden = ["pct", "n_comercio"] if con_porcentaje else ["n_comercio"]
        ofertas = ofertas.sort_values(orden, ascending=[False, True] if con_porcentaje else True,
                                      na_position="last")
        hay_no_valido |= (ofertas["estado"] == NO_VALIDO).any()
        hay_inconsistente |= (ofertas["estado"] == INCONSISTENTE).any()
        con_desc = ofertas[ofertas["estado"] == CON_DESCUENTO]
        if con_porcentaje:
            if con_desc.empty:
                detalle = "No tiene descuento en ningún comercio."
            else:
                mejor = con_desc.sort_values("pct", ascending=False).iloc[0]
                detalle = f"Su mejor descuento es **{porcentaje(mejor['pct'])}** en {md(_comercio(mejor))}."
        else:
            n = len(ofertas)
            detalle = (f"Tiene precio en {n} comercio{'s' if n != 1 else ''}; "
                       f"{len(con_desc)} con descuento.")
        frases.append(f"**{md(prod.producto)}**  \nEAN {prod.ean} · {md(_lugar(prod))}  \n{detalle}")
        titulo = f"{prod.producto} — {_lugar(prod)}" if len(prods) > 1 else ""
        tablas.append((titulo, _tabla_ofertas(ofertas, con_porcentaje)))

    if hay_no_valido:
        avisos.append("«Precio no válido»: ese comercio no tiene precio original registrado, "
                      "así que no se muestra ningún valor ni se calcula descuento.")
    if hay_inconsistente:
        avisos.append("«Precio inconsistente»: el precio con descuento registrado es mayor que el "
                      "original. Se muestra solo el precio original.")
    sugerencias = [f"precio del {ean}" if con_porcentaje else f"porcentaje de descuento del {ean}"]
    zona = prods.iloc[0]["n_zona"]
    if not pd.isna(zona):
        sugerencias.append(f"descuentos en zona {int(zona)}")
    return Respuesta(intencion, "\n\n".join(frases), tablas, avisos, sugerencias, ean=ean)


# ---------- filtro por texto (nombre, marca o categoría) ----------

def _raiz(palabra: str) -> str:
    """Quita el plural para comparar: 'celulares' -> 'celular', 'neveras' -> 'nevera'."""
    if len(palabra) > 4 and palabra.endswith("es") and palabra[-3] not in "aeiou":
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


# Otras formas comunes de llamar a un producto -> la palabra que usan los datos
SINONIMOS = {"televisor": "tv", "television": "tv", "tele": "tv", "telefono": "celular",
             "celu": "celular", "movil": "celular", "smartphone": "celular",
             "refrigerador": "nevera", "refrigeradora": "nevera", "laptop": "portatil",
             "auricular": "audifono", "computadora": "computador", "pc": "computador"}


def _clave(palabra: str) -> str:
    """La forma en que se compara una palabra: sin plural y con su sinónimo."""
    raiz = _raiz(palabra)
    return SINONIMOS.get(raiz, raiz)


def ids_por_texto(datos: Datos, termino: str) -> set:
    """Productos cuyo nombre, marca o categoría contiene todas las palabras del término.

    Si algún producto EMPIEZA por la primera palabra ("Celular ..."), se devuelven solo esos:
    así "celulares" trae teléfonos y no los accesorios para celular.
    """
    palabras = [_clave(w) for w in normalizar(termino).split()]
    if not palabras:
        return set()
    productos = datos.productos
    coincide = pd.Series(True, index=productos.index)
    for palabra in palabras:
        patron = r"(?<![a-z0-9])" + re.escape(palabra)   # la palabra debe empezar igual
        coincide &= productos["texto_busqueda"].str.contains(patron, regex=True)
    empieza = coincide & productos["producto_busqueda"].str.startswith(palabras[0])
    if empieza.any():
        coincide = empieza
    return set(productos.loc[coincide, "id_producto"])


_vocabulario: dict = {}


def _corregir(datos: Datos, palabra: str) -> str | None:
    """Corrige un error de escritura: 'sansung' -> 'samsung', 'nebera' -> 'nevera'.

    Compara la palabra con las que existen en los datos y devuelve la más parecida,
    solo si el parecido es alto. Usa difflib, de la librería estándar de Python.
    """
    if len(palabra) < 5:
        return None                      # en palabras cortas el parecido engaña
    inicial = palabra[0]                 # un error de escritura casi nunca cambia la primera letra
    if id(datos) not in _vocabulario:
        palabras = set()
        for texto in datos.productos["texto_busqueda"]:
            palabras.update(_raiz(w) for w in texto.split() if len(w) >= 4 and w.isalpha())
        _vocabulario[id(datos)] = sorted(palabras)
    candidatas = [w for w in _vocabulario[id(datos)] if w[0] == inicial]
    parecidas = difflib.get_close_matches(_raiz(palabra), candidatas, n=1, cutoff=0.82)
    return parecidas[0] if parecidas else None


def coincidencias(datos: Datos, termino: str):
    """Busca el término tolerando errores de escritura y palabras que no existen.

    Devuelve (ids, texto_usado, avisos).
    - "celular sansung": corrige a "celular samsung" y lo avisa.
    - "celular nokia": no hay Nokia, usa "celular" y lo avisa.
    """
    usadas, descartadas, avisos = [], [], []
    for palabra in termino.split():
        if ids_por_texto(datos, palabra):
            usadas.append(palabra)
            continue
        corregida = _corregir(datos, palabra)
        if corregida:
            usadas.append(corregida)
            avisos.append(f"No encontré «{palabra}»; busqué «{corregida}».")
        else:
            descartadas.append(palabra)
    while usadas:
        ids = ids_por_texto(datos, " ".join(usadas))
        if ids:
            if descartadas:
                avisos.append(f"No encontré productos con «{' '.join(descartadas)}». "
                              f"Te muestro los que coinciden con «{' '.join(usadas)}».")
            return ids, " ".join(usadas), avisos
        descartadas.append(usadas.pop())   # las palabras existen, pero no juntas
    return set(), "", [f"No encontré productos que coincidan con «{termino}»."]


def _base(datos: Datos, ids: set | None) -> pd.DataFrame:
    """El ranking completo, o solo los productos del filtro."""
    if ids is None:
        return datos.ranking
    return datos.ranking[datos.ranking["id_producto"].isin(ids)]


def _de(etiqueta: str) -> str:
    return f" que coinciden con «{md(etiqueta)}»" if etiqueta else ""


def _de1(etiqueta: str) -> str:
    return f" que coincida con «{md(etiqueta)}»" if etiqueta else ""


# ---------- consulta 3: top n ----------

def _validar_cantidad(n: float | None, por_defecto: int):
    """Devuelve (cantidad, aviso, error)."""
    if n is None:
        return por_defecto, None, None
    if n != int(n) or n <= 0:
        return None, None, "Indica una cantidad entera mayor que cero, por ejemplo: `top 5 descuentos`."
    if n > TOP_MAXIMO:
        return TOP_MAXIMO, f"Pediste {int(n)}; el máximo por consulta es {TOP_MAXIMO}.", None
    return int(n), None, None


def top(datos: Datos, intencion: str, n: float | None, ids: set | None = None,
        etiqueta: str = "", menores: bool = False) -> Respuesta:
    cantidad, aviso, error = _validar_cantidad(n, TOP_POR_DEFECTO)
    if error:
        return Respuesta(intencion, error)
    base = _base(datos, ids)
    if base.empty:
        return Respuesta(intencion, f"Ningún producto{_de1(etiqueta)} tiene descuento.")
    filas = (base.sort_values("pct") if menores else base).head(cantidad)
    texto = (f"Los **{len(filas)}** productos{_de(etiqueta)} con {'menor' if menores else 'mayor'} "
             "descuento. Cada producto aparece una vez, con su mejor descuento y el comercio que lo ofrece.")
    if menores:
        texto += " Solo se cuentan los productos que tienen algún descuento."
    return Respuesta(intencion, texto, [("", _tabla_ranking(filas))], [aviso] if aviso else [],
                     ["descuentos superiores al 50%", "descuentos en zona 1"])


# ---------- consulta 4: por porcentaje ----------

def _texto_rango(pct_min: float | None, pct_max: float | None) -> str:
    if pct_min is not None and pct_max is not None:
        return f"entre {porcentaje(pct_min)} y {porcentaje(pct_max)}"
    if pct_max is not None:
        return f"inferior al {porcentaje(pct_max)}"
    return f"superior al {porcentaje(pct_min)}"


def _en_rango(filas: pd.DataFrame, pct_min: float | None, pct_max: float | None) -> pd.DataFrame:
    if pct_min is not None and pct_max is not None:      # "entre 20 y 30" incluye los extremos
        return filas[(filas["pct"] >= pct_min) & (filas["pct"] <= pct_max)]
    if pct_max is not None:
        return filas[filas["pct"] < pct_max]
    if pct_min is not None:
        return filas[filas["pct"] > pct_min]
    return filas


def _rango_invalido(pct_min, pct_max) -> bool:
    return any(v is not None and not 0 <= v <= 100 for v in (pct_min, pct_max))


def superiores(datos: Datos, intencion: str, pct_min: float | None, pct_max: float | None,
               n: float | None, ids: set | None = None, etiqueta: str = "") -> Respuesta:
    if _rango_invalido(pct_min, pct_max):
        return Respuesta(intencion, "El porcentaje debe estar entre 0 y 100. "
                         "Ejemplo: `descuentos superiores al 30%`.")
    cantidad, aviso, error = _validar_cantidad(n, FILAS_UMBRAL)
    if error:
        return Respuesta(intencion, error)
    rango = _texto_rango(pct_min, pct_max)
    filas = _en_rango(_base(datos, ids), pct_min, pct_max)
    if filas.empty:
        return Respuesta(intencion, f"Ningún producto{_de1(etiqueta)} tiene un descuento {rango}.",
                         sugerencias=["top 10 descuentos"])
    total = len(filas)
    visibles = filas.head(cantidad)
    texto = (f"**{entero(total)}** producto{'s' if total != 1 else ''}{_de(etiqueta)} "
             f"{'tienen' if total != 1 else 'tiene'} un descuento {rango}.")
    if total > len(visibles):
        texto += f" Te muestro los {len(visibles)} mayores; la lista completa se puede descargar."
    return Respuesta(intencion, texto, [("", _tabla_ranking(visibles))], [aviso] if aviso else [],
                     ["top 10 descuentos"], _tabla_csv(filas), "descuentos_por_porcentaje.csv")


# ---------- consulta 5: por almacén o zona ----------

def _resumen(productos: pd.DataFrame, ranking: pd.DataFrame) -> str:
    total, con = len(productos), len(ranking)
    if con == 0:
        return f"{entero(total)} productos, ninguno con descuento."
    return (f"{entero(total)} productos, {entero(con)} con descuento ({porcentaje(con / total * 100)}). "
            f"Descuento promedio de los que tienen: **{porcentaje(ranking['pct'].mean())}**.")


def tabla_lugares(datos: Datos) -> pd.DataFrame:
    return pd.DataFrame({"Almacén": datos.zonas["almacen"].values,
                         "Nombre": datos.zonas["nombre_almacen"].values,
                         "Zona": datos.zonas["zona"].values})


def por_lugar(datos: Datos, intencion: str, zona: int | None, almacen: str | None,
              n: float | None, pct_min: float | None, pct_max: float | None = None,
              ids: set | None = None, etiqueta: str = "") -> Respuesta:
    zonas = datos.zonas
    numeros_zona = sorted(zonas["n_zona"].unique())
    ayuda_lugar = (f"Los almacenes van de {zonas['almacen'].min()} a {zonas['almacen'].max()} "
                   f"y las zonas de {numeros_zona[0]} a {numeros_zona[-1]}.")
    if almacen and almacen not in set(zonas["almacen"]):
        return Respuesta(intencion, f"El almacén **{almacen}** no existe. {ayuda_lugar}")
    if not almacen and zona not in numeros_zona:
        return Respuesta(intencion, f"La zona **{zona}** no existe. {ayuda_lugar}")
    if _rango_invalido(pct_min, pct_max):
        return Respuesta(intencion, "El porcentaje debe estar entre 0 y 100.")
    cantidad, aviso, error = _validar_cantidad(n, TOP_LUGAR)
    if error:
        return Respuesta(intencion, error)
    avisos = [aviso] if aviso else []

    tablas = []
    if almacen:  # el almacén es más específico que la zona
        fila = zonas[zonas["almacen"] == almacen].iloc[0]
        nombre = f"{almacen} ({fila['nombre_almacen']}, {fila['zona']})"
        if zona is not None and zona != fila["n_zona"]:
            avisos.append(f"{almacen} pertenece a {fila['zona']}, no a la zona {zona}. Te muestro el almacén.")
        prods = datos.productos[datos.productos["almacen"] == almacen]
        sugerencias = [f"descuentos en zona {fila['n_zona']}"]
        archivo = f"descuentos_{almacen}.csv"
    else:
        del_lugar = zonas[zonas["n_zona"] == zona]
        nombre = (f"{del_lugar.iloc[0]['zona']} (almacenes {del_lugar['almacen'].min()} "
                  f"a {del_lugar['almacen'].max()})")
        prods = datos.productos[datos.productos["n_zona"] == zona]
        sugerencias = [f"descuentos en {del_lugar.iloc[0]['almacen']}"]
        archivo = f"descuentos_zona_{zona}.csv"

    ranking = datos.ranking[datos.ranking["id_producto"].isin(prods["id_producto"])]
    texto = f"**{md(nombre)}**: {_resumen(prods, ranking)}"
    filtrado = ranking
    if ids is not None:
        filtrado = filtrado[filtrado["id_producto"].isin(ids)]
        texto += f"\n\nCon descuento{_de(etiqueta)}: **{entero(len(filtrado))}** productos."
    if pct_min is not None or pct_max is not None:
        filtrado = _en_rango(filtrado, pct_min, pct_max)
        texto += (f"\n\nCon descuento {_texto_rango(pct_min, pct_max)}: "
                  f"**{entero(len(filtrado))}** productos.")
    if not filtrado.empty:
        visibles = filtrado.head(cantidad)
        tablas.append((f"Los {len(visibles)} mayores descuentos", _tabla_ranking(visibles)))
    if not almacen:  # desglose de la zona por almacén
        desglose = []
        for a in del_lugar.itertuples():
            p_a = prods[prods["almacen"] == a.almacen]
            r_a = ranking[ranking["almacen"] == a.almacen]
            desglose.append({"Almacén": a.almacen, "Nombre": a.nombre_almacen,
                             "Productos": len(p_a), "Con descuento": len(r_a),
                             "Descuento promedio": porcentaje(r_a["pct"].mean()) if len(r_a) else "—"})
        tablas.append(("Desglose por almacén", pd.DataFrame(desglose)))
    return Respuesta(intencion, texto, tablas, avisos, sugerencias,
                     _tabla_csv(filtrado) if not filtrado.empty else None, archivo)


# ---------- extra: buscar por nombre ----------

def buscar(datos: Datos, intencion: str, termino: str, ids: set | None = None,
           pendiente: str | None = None) -> Respuesta:
    if ids is None:
        ids = ids_por_texto(datos, termino)
    if not ids:
        return Respuesta(intencion, f"No encontré productos con «{md(termino)}». Prueba con menos "
                         "palabras o con la marca.", pendiente=pendiente)
    encontrados = datos.productos[datos.productos["id_producto"].isin(ids)].copy()
    con_descuento = datos.ranking.set_index("id_producto")
    # Para los que no tienen descuento: su precio original más bajo
    con_precio = datos.ofertas[datos.ofertas["precio_original"].notna()]
    sin_descuento = (con_precio.sort_values("precio_original")
                     .drop_duplicates("id_producto").set_index("id_producto"))
    encontrados["pct"] = encontrados["id_producto"].map(con_descuento["pct"])
    encontrados = encontrados.sort_values("pct", ascending=False, na_position="last")
    visibles = encontrados.head(10)
    filas = []
    for prod in visibles.itertuples():
        fila = {"Producto": prod.producto, "Precio original": "—", "Precio con descuento": "—",
                "Descuento": "—", "Comercio": "—", "EAN": prod.ean,
                "Almacén": prod.almacen if hay(prod.almacen) else "—"}
        if prod.id_producto in con_descuento.index:
            o = con_descuento.loc[prod.id_producto]
            fila.update({"Precio original": dinero(o["precio_original"]),
                         "Precio con descuento": dinero(o["precio_descuento"]),
                         "Descuento": porcentaje(o["pct"]), "Comercio": _comercio(o)})
        elif prod.id_producto in sin_descuento.index:
            o = sin_descuento.loc[prod.id_producto]
            fila.update({"Precio original": dinero(o["precio_original"]),
                         "Precio con descuento": "Sin descuento", "Comercio": _comercio(o)})
        filas.append(fila)
    total = len(encontrados)
    texto = f"Encontré **{entero(total)}** producto{'s' if total != 1 else ''} con «{md(termino)}»."
    if total > len(visibles):
        texto += (f" Te muestro los {len(visibles)} con mayor descuento; agrega más palabras "
                  "(marca, tamaño) para afinar.")
    texto += (" Cada uno aparece con su mejor descuento. Para ver sus precios en todos los "
              "comercios, escribe su EAN.")
    ean = visibles.iloc[0]["ean"]
    return Respuesta(intencion, texto, [("", pd.DataFrame(filas))],
                     sugerencias=[f"precio del {ean}", f"top 10 {termino}"], pendiente=pendiente)


# ---------- extras: por precio, sin descuento y categorías ----------

def por_precio(datos: Datos, intencion: str, n: float | None, precio_min: float | None,
               precio_max: float | None, ids: set | None = None, etiqueta: str = "") -> Respuesta:
    """Los productos más baratos, con presupuesto opcional ("celulares de menos de 1 millón")."""
    cantidad, aviso, error = _validar_cantidad(n, TOP_POR_DEFECTO)
    if error:
        return Respuesta(intencion, error)
    filas = datos.baratos
    if ids is not None:
        filas = filas[filas["id_producto"].isin(ids)]
    rango = ""
    if precio_max is not None:
        filas = filas[filas["precio_final"] <= precio_max]
        rango += f" de hasta {dinero(precio_max)}"
    if precio_min is not None:
        filas = filas[filas["precio_final"] >= precio_min]
        rango += f" desde {dinero(precio_min)}"
    rango = md(rango)
    if filas.empty:
        return Respuesta(intencion, f"No encontré productos{_de(etiqueta)}{rango}.")
    visibles = filas.head(cantidad)
    tabla = pd.DataFrame({
        "#": range(1, len(visibles) + 1),
        "Producto": visibles["producto"].values,
        "Precio": [dinero(v) for v in visibles["precio_final"]],
        "Precio original": [dinero(v) for v in visibles["precio_original"]],
        "Descuento": [porcentaje(v) if hay(v) else "Sin descuento" for v in visibles["pct"]],
        "Comercio": [_comercio(f) for f in visibles.itertuples()],
        "EAN": visibles["ean"].values,
        "Almacén": [a if hay(a) else "—" for a in visibles["almacen"]],
    })
    total = len(filas)
    texto = (f"**{entero(total)}** producto{'s' if total != 1 else ''}{_de(etiqueta)}{rango}. "
             f"Te muestro los {len(visibles)} más baratos. «Precio» es el más bajo entre los comercios: "
             "con descuento si lo tiene, o el original si no.")
    return Respuesta(intencion, texto, [("", tabla)], [aviso] if aviso else [],
                     [f"precio del {visibles.iloc[0]['ean']}"])


def sin_descuento(datos: Datos, intencion: str, n: float | None, ids: set | None = None,
                  etiqueta: str = "") -> Respuesta:
    cantidad, aviso, error = _validar_cantidad(n, TOP_POR_DEFECTO)
    if error:
        return Respuesta(intencion, error)
    filas = datos.baratos[~datos.baratos["id_producto"].isin(datos.ranking["id_producto"])]
    if ids is not None:
        filas = filas[filas["id_producto"].isin(ids)]
    if filas.empty:
        return Respuesta(intencion, f"Todos los productos{_de(etiqueta)} tienen algún descuento.")
    visibles = filas.head(cantidad)
    tabla = pd.DataFrame({
        "Producto": visibles["producto"].values,
        "Precio": [dinero(v) for v in visibles["precio_final"]],
        "Comercio": [_comercio(f) for f in visibles.itertuples()],
        "EAN": visibles["ean"].values,
        "Almacén": [a if hay(a) else "—" for a in visibles["almacen"]],
    })
    total = len(filas)
    texto = (f"**{entero(total)}** producto{'s' if total != 1 else ''}{_de(etiqueta)} no "
             f"{'tienen' if total != 1 else 'tiene'} descuento en ningún comercio. "
             f"Te muestro {len(visibles)}, del más barato al más caro.")
    return Respuesta(intencion, texto, [("", tabla)], [aviso] if aviso else [])


def catalogo(datos: Datos, intencion: str) -> Respuesta:
    p = datos.productos
    grupos = p.groupby(p["subdireccion"].map(normalizar))
    tabla = pd.DataFrame({
        "Categoría": grupos["subdireccion"].first().values,
        "Productos": grupos.size().values,
        "Con descuento": grupos["id_producto"].apply(
            lambda ids: ids.isin(datos.ranking["id_producto"]).sum()).values,
    }).sort_values("Productos", ascending=False)
    texto = (f"Hay **{entero(len(p))}** productos en estas categorías. Escribe el nombre de un producto "
             "o una marca para buscarlo, por ejemplo `celular samsung` o `nevera`.")
    return Respuesta(intencion, texto, [("", tabla)],
                     sugerencias=["top 10 descuentos", "celulares baratos", "nevera"])
