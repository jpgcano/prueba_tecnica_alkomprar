"""Interfaz web del chatbot (Streamlit).

Este archivo solo dibuja la pantalla. No tiene reglas: todo mensaje,
escrito a mano o enviado con un botón, se le pasa al mismo Bot.

Para abrirla:  streamlit run app.py
"""
import streamlit as st

from chatbot.bot import Bot

st.set_page_config(page_title="Chatbot de descuentos", page_icon="🛒", layout="wide")


@st.cache_resource(show_spinner="Cargando y limpiando los datos…")
def obtener_bot() -> Bot:
    """Lee y limpia el Excel una sola vez; después se reutiliza en cada mensaje."""
    return Bot()


try:
    bot = obtener_bot()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()
estado = st.session_state
estado.setdefault("historial", [])   # mensajes de la conversación
estado.setdefault("pendiente", None)  # consulta que espera un dato
estado.setdefault("ultimo_ean", None)  # último producto consultado
estado.setdefault("ultimo_termino", None)  # último producto del que se habló


def enviar(frase: str) -> None:
    """Único camino de entrada: guarda la frase y la respuesta del bot."""
    estado.historial.append({"rol": "user", "texto": frase})
    respuesta = bot.responder(frase, estado.pendiente, estado.ultimo_ean, estado.ultimo_termino)
    estado.pendiente = respuesta.pendiente
    if respuesta.ean:
        estado.ultimo_ean = respuesta.ean
    estado.ultimo_termino = respuesta.termino or None
    estado.historial.append({"rol": "assistant", "respuesta": respuesta})


# El nombre del producto es largo. Se limita su ancho y se fija el de los precios
# para que se vean sin desplazar la tabla, incluso en una ventana angosta.
ANCHOS = {
    "Producto": st.column_config.TextColumn(width="medium"),
    "Precio": st.column_config.TextColumn(width="small"),
    "Precio original": st.column_config.TextColumn(width="small"),
    "Precio con descuento": st.column_config.TextColumn(width="small"),
    "Descuento": st.column_config.TextColumn(width="small"),
}


def mostrar(respuesta, indice: int, es_ultima: bool) -> None:
    st.markdown(respuesta.texto)
    for aviso in respuesta.avisos:
        st.warning(aviso)
    for titulo, tabla in respuesta.tablas:
        if titulo:
            st.caption(titulo)
        st.dataframe(tabla, hide_index=True, column_config=ANCHOS)
    if respuesta.descarga is not None:
        st.download_button(
            f"Descargar lista completa ({len(respuesta.descarga)} productos, CSV)",
            respuesta.descarga.to_csv(index=False).encode("utf-8-sig"),
            file_name=respuesta.nombre_descarga, mime="text/csv", key=f"csv_{indice}")
    if es_ultima and respuesta.sugerencias:
        columnas = st.columns(min(len(respuesta.sugerencias), 3))
        for j, frase in enumerate(respuesta.sugerencias):
            columnas[j % 3].button(frase, key=f"sug_{indice}_{j}", on_click=enviar, args=(frase,))


# ---------- barra lateral: consultas guiadas ----------
# Cada botón arma una frase estándar y la envía por el mismo camino que el texto libre.
with st.sidebar:
    st.header("Consultas rápidas")

    with st.expander("Precio o descuento de un producto", expanded=True):
        st.text_input("EAN (código de barras)", key="f_ean", placeholder="7704353471953")
        st.button("Ver precios", on_click=lambda: enviar(f"precio del {estado.f_ean}".strip()))
        st.button("Ver porcentaje de descuento",
                  on_click=lambda: enviar(f"porcentaje de descuento del {estado.f_ean}".strip()))

    with st.expander("Mayores descuentos"):
        st.selectbox("Cuántos productos", [5, 10, 20, 50], index=1, key="f_top")
        st.button("Ver ranking", on_click=lambda: enviar(f"top {estado.f_top} descuentos"))

    with st.expander("Descuentos superiores a…"):
        st.slider("Porcentaje mínimo", 0, 95, 50, step=5, key="f_pct")
        st.button("Consultar", on_click=lambda: enviar(f"descuentos superiores al {estado.f_pct}%"))

    with st.expander("Por almacén o zona"):
        zonas = bot.datos.zonas
        opciones = [f"zona {n}" for n in sorted(zonas["n_zona"].unique())] + list(zonas["almacen"])
        st.selectbox("Almacén o zona", opciones, key="f_lugar")
        st.button("Ver descuentos", on_click=lambda: enviar(f"descuentos en {estado.f_lugar}"))

    with st.expander("Buscar producto por nombre"):
        st.text_input("Nombre o parte del nombre", key="f_buscar", placeholder="nevera mabe")
        st.button("Buscar", on_click=lambda: enviar(f"buscar {estado.f_buscar}".strip()))

    st.divider()
    r = bot.datos.resumen()
    st.caption(f"Datos cargados: {r['productos']:,} productos, {r['ofertas']:,} precios en comercios, "
               f"{len(bot.datos.zonas)} almacenes.".replace(",", "."))
    st.button("Borrar conversación", on_click=lambda: estado.update(historial=[], pendiente=None, ultimo_ean=None,
                                                  ultimo_termino=None))


# ---------- conversación ----------
st.title("Chatbot de precios y descuentos")
st.caption("Responde con reglas y palabras clave sobre los datos del Excel. No usa IA generativa.")

mensaje = st.chat_input("Escribe tu consulta. Ejemplo: top 5 descuentos")
if mensaje:
    enviar(mensaje)

with st.chat_message("assistant"):
    mostrar(bot.bienvenida(), -1, es_ultima=not estado.historial)

for indice, item in enumerate(estado.historial):
    with st.chat_message(item["rol"]):
        if item["rol"] == "user":
            st.text(item["texto"])
        else:
            mostrar(item["respuesta"], indice, es_ultima=indice == len(estado.historial) - 1)
