"""Etapa 0: leer el Excel y dejar los datos limpios en memoria.

Reglas de integridad:
- El archivo Excel nunca se modifica.
- Cada corrección queda anotada en el registro de correcciones.
- Solo se corrige la forma (espacios, texto que era número). El contenido
  no se inventa: un precio que falta sigue faltando.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .texto import limpiar_espacios, normalizar

NOMBRE_ARCHIVO = "Prueba_Tecnica_Desarrollador_Automatizacionesx.xlsx"


def _buscar_archivo() -> Path:
    """Busca el Excel desde esta carpeta hacia arriba.

    Así funciona igual si el proyecto se ejecuta desde la raíz o desde esta carpeta.
    """
    for carpeta in Path(__file__).resolve().parents:
        if (carpeta / NOMBRE_ARCHIVO).exists():
            return carpeta / NOMBRE_ARCHIVO
    return Path(NOMBRE_ARCHIVO)


ARCHIVO = _buscar_archivo()
HOJA_PRODUCTOS = "Caso_Analisis_1"
HOJA_ZONAS = "Caso_Analisis_2"

# Los cuatro estados posibles de un par de precios (original, con descuento)
CON_DESCUENTO = "con descuento"
SIN_DESCUENTO = "sin descuento"
INCONSISTENTE = "precio inconsistente"   # el descuento es mayor que el original
NO_VALIDO = "precio no válido"           # falta el precio original

COLUMNAS_TEXTO = {
    "Almacen": "almacen",
    "Prove": "proveedor",
    "Dirección": "direccion",
    "Subdirección": "subdireccion",
    "desc.1": "categoria",
    "Producto": "producto",
}


@dataclass
class Datos:
    productos: pd.DataFrame     # una fila por producto
    ofertas: pd.DataFrame       # una fila por producto y comercio (tabla "larga")
    ranking: pd.DataFrame       # una fila por producto: su mejor descuento
    baratos: pd.DataFrame       # una fila por producto: su precio más bajo, de menor a mayor
    zonas: pd.DataFrame         # almacén -> nombre y zona
    correcciones: pd.DataFrame  # qué se corrigió, dónde y por qué

    def resumen(self) -> dict:
        estados = self.ofertas["estado"].value_counts()
        return {
            "productos": len(self.productos),
            "ofertas": len(self.ofertas),
            "productos_con_descuento": len(self.ranking),
            "con_descuento": int(estados.get(CON_DESCUENTO, 0)),
            "sin_descuento": int(estados.get(SIN_DESCUENTO, 0)),
            "inconsistentes": int(estados.get(INCONSISTENTE, 0)),
            "no_validos": int(estados.get(NO_VALIDO, 0)),
            "ean_ambiguos": int(self.productos["ean_ambiguo"].sum()),
            "sin_almacen": int(self.productos["almacen"].isna().sum()),
            "correcciones": len(self.correcciones),
        }


def _a_numero(valor):
    """Convierte una celda de precio en número.

    Devuelve (numero, motivo). `numero` es None cuando no hay un precio usable.
    `motivo` explica la corrección, o es None si la celda ya estaba bien.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None, None
    if isinstance(valor, bool):
        return None, "valor que no es un precio"
    if isinstance(valor, (int, float)):
        return (float(valor), None) if valor > 0 else (None, "precio en 0 tratado como sin dato")
    texto = str(valor).strip()
    try:
        numero = float(texto)
    except ValueError:
        return None, "mensaje de error en lugar de precio"
    if numero > 0:
        return numero, "texto convertido a número"
    return None, "precio en 0 tratado como sin dato"


def _estado(original, descuento):
    """Clasifica un par de precios. Devuelve (estado, porcentaje)."""
    if original is None:
        return NO_VALIDO, None
    if descuento is None or descuento == original:
        return SIN_DESCUENTO, None
    if descuento > original:
        return INCONSISTENTE, None
    return CON_DESCUENTO, (original - descuento) / original * 100


def _limpiar_zonas(hoja: pd.DataFrame, registro: list) -> pd.DataFrame:
    zonas = hoja.copy()
    zonas.columns = ["almacen", "nombre_almacen", "zona"]
    for col in zonas.columns:
        zonas[col] = zonas[col].map(lambda v: limpiar_espacios(str(v)))
    # Un identificador repetido es un error: el número de "ALM-0NN" debe ser
    # el mismo de "Almacen_NN". Solo se corrige si hay repetición (evidencia).
    repetidos = zonas["almacen"].duplicated(keep=False)
    for i in zonas.index[repetidos]:
        numero = re.search(r"(\d+)$", zonas.at[i, "nombre_almacen"])
        if not numero:
            continue
        esperado = f"ALM-{int(numero.group(1)):03d}"
        if esperado != zonas.at[i, "almacen"] and esperado not in set(zonas["almacen"]):
            registro.append({
                "hoja": HOJA_ZONAS, "fila_excel": i + 2, "columna": "Nomenclatura",
                "valor_original": zonas.at[i, "almacen"], "valor_nuevo": esperado,
                "motivo": "nomenclatura repetida; se corrige según el número del nombre del almacén",
            })
            zonas.at[i, "almacen"] = esperado
    zonas["n_zona"] = zonas["zona"].str.extract(r"(\d+)$")[0].astype(int)
    return zonas


def _limpiar_productos(hoja: pd.DataFrame, zonas: pd.DataFrame, registro: list) -> pd.DataFrame:
    p = pd.DataFrame({"id_producto": range(len(hoja)), "fila_excel": hoja.index + 2})

    # EAN: se quitan los espacios internos ("770611 2423869")
    eans = []
    for fila, valor in zip(p["fila_excel"], hoja["EAN"]):
        original = str(valor)
        limpio = re.sub(r"\s+", "", original)
        if limpio != original:
            registro.append({"hoja": HOJA_PRODUCTOS, "fila_excel": fila, "columna": "EAN",
                             "valor_original": original, "valor_nuevo": limpio,
                             "motivo": "espacio dentro del EAN"})
        eans.append(limpio)
    p["ean"] = eans

    # Textos: solo se quitan espacios sobrantes; el contenido queda igual
    for col_excel, col in COLUMNAS_TEXTO.items():
        valores = []
        for fila, valor in zip(p["fila_excel"], hoja[col_excel]):
            if pd.isna(valor):
                valores.append(None)
                continue
            original = str(valor)
            limpio = limpiar_espacios(original)
            if limpio != original:
                registro.append({"hoja": HOJA_PRODUCTOS, "fila_excel": fila, "columna": col_excel,
                                 "valor_original": original, "valor_nuevo": limpio,
                                 "motivo": "espacios sobrantes"})
            valores.append(limpio)
        p[col] = valores

    # Columna solo para buscar: minúsculas y sin tildes. La original se muestra.
    p["producto_busqueda"] = p["producto"].map(normalizar)
    # Texto para buscar por nombre, marca o categoría ("celulares samsung")
    p["texto_busqueda"] = [
        normalizar(" ".join(str(v) for v in fila if v))
        for fila in zip(p["producto"], p["proveedor"], p["direccion"], p["subdireccion"], p["categoria"])
    ]
    # Un EAN que aparece en más de un producto se conserva y se marca
    p["ean_ambiguo"] = p["ean"].duplicated(keep=False)
    # Zona: se une por almacén. Sin almacén -> sin zona.
    p = p.merge(zonas, on="almacen", how="left")
    return p


def _armar_ofertas(hoja: pd.DataFrame, productos: pd.DataFrame, registro: list) -> pd.DataFrame:
    """Pasa de tabla ancha (27 pares de columnas) a larga (una fila por comercio)."""
    comercios = sorted(
        int(c.replace("PrecioOriginal_Comercio", ""))
        for c in hoja.columns if c.startswith("PrecioOriginal_Comercio")
    )
    filas = []
    for c in comercios:
        col_o, col_d, col_v = (f"PrecioOriginal_Comercio{c}", f"PrecioDescuento_Comercio{c}",
                               f"Vendedor_Comercio{c}")
        vendedores = hoja[col_v] if col_v in hoja.columns else [None] * len(hoja)
        for id_producto, fila, crudo_o, crudo_d, vendedor in zip(
                productos["id_producto"], productos["fila_excel"], hoja[col_o], hoja[col_d], vendedores):
            if pd.isna(crudo_o) and pd.isna(crudo_d):
                continue  # este comercio no vende el producto
            original, motivo_o = _a_numero(crudo_o)
            descuento, motivo_d = _a_numero(crudo_d)
            for col, crudo, nuevo, motivo in ((col_o, crudo_o, original, motivo_o),
                                              (col_d, crudo_d, descuento, motivo_d)):
                if motivo:
                    registro.append({"hoja": HOJA_PRODUCTOS, "fila_excel": fila, "columna": col,
                                     "valor_original": crudo, "valor_nuevo": nuevo, "motivo": motivo})
            if original is None and descuento is None:
                continue  # tras limpiar no quedó ningún precio usable
            estado, pct = _estado(original, descuento)
            filas.append({
                "id_producto": id_producto, "comercio": f"Comercio{c}", "n_comercio": c,
                "vendedor": None if pd.isna(vendedor) else limpiar_espacios(str(vendedor)),
                "precio_original": original, "precio_descuento": descuento,
                "pct": pct, "estado": estado,
            })
    return pd.DataFrame(filas)


def _armar_ranking(productos: pd.DataFrame, ofertas: pd.DataFrame) -> pd.DataFrame:
    """Una fila por producto con su mejor descuento, de mayor a menor."""
    validas = ofertas[ofertas["estado"] == CON_DESCUENTO]
    mejores = (validas.sort_values(["pct", "n_comercio"], ascending=[False, True])
               .drop_duplicates("id_producto"))
    ranking = mejores.merge(productos, on="id_producto", how="left")
    return ranking.sort_values(["pct", "id_producto"], ascending=[False, True]).reset_index(drop=True)


def _armar_baratos(productos: pd.DataFrame, ofertas: pd.DataFrame) -> pd.DataFrame:
    """Una fila por producto con su precio final más bajo, de menor a mayor.

    Precio final = el precio con descuento si lo hay; si no, el precio original.
    Un par con "precio no válido" no tiene precio final.
    """
    o = ofertas.copy()
    o["precio_final"] = o["precio_descuento"].where(o["estado"] == CON_DESCUENTO, o["precio_original"])
    o = o[o["estado"] != NO_VALIDO]
    mejores = o.sort_values(["precio_final", "n_comercio"]).drop_duplicates("id_producto")
    baratos = mejores.merge(productos, on="id_producto", how="left")
    return baratos.sort_values(["precio_final", "id_producto"]).reset_index(drop=True)


def cargar_datos(ruta: Path | str = ARCHIVO) -> Datos:
    if not Path(ruta).exists():
        raise FileNotFoundError(
            f"No encontré el archivo de datos «{NOMBRE_ARCHIVO}». "
            "Debe estar en la carpeta raíz del proyecto, junto a requirements.txt.")
    hojas = pd.read_excel(ruta, sheet_name=[HOJA_PRODUCTOS, HOJA_ZONAS], dtype=object)
    registro: list[dict] = []
    zonas = _limpiar_zonas(hojas[HOJA_ZONAS], registro)
    productos = _limpiar_productos(hojas[HOJA_PRODUCTOS], zonas, registro)
    ofertas = _armar_ofertas(hojas[HOJA_PRODUCTOS], productos, registro)
    ranking = _armar_ranking(productos, ofertas)
    correcciones = pd.DataFrame(
        registro, columns=["hoja", "fila_excel", "columna", "valor_original", "valor_nuevo", "motivo"])
    baratos = _armar_baratos(productos, ofertas)
    return Datos(productos, ofertas, ranking, baratos, zonas, correcciones)
