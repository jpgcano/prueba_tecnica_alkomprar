"""La limpieza cumple los supuestos documentados."""
from chatbot.datos import CON_DESCUENTO, INCONSISTENTE, NO_VALIDO


def test_no_se_pierden_productos(bot):
    assert len(bot.datos.productos) == 6477


def test_ean_sin_espacios_y_ambiguos_marcados(bot):
    p = bot.datos.productos
    assert not p["ean"].str.contains(" ").any()
    assert p["ean_ambiguo"].sum() == 30          # 15 EAN repetidos, 2 productos cada uno


def test_almacen_13_tiene_zona(bot):
    p = bot.datos.productos
    assert (p[p["almacen"] == "ALM-013"]["zona"] == "Zona_3").all()
    assert p[p["almacen"].isna()]["zona"].isna().all()   # sin almacén -> sin zona


def test_estados_de_precio(bot):
    o = bot.datos.ofertas
    con = o[o["estado"] == CON_DESCUENTO]
    assert (con["precio_descuento"] < con["precio_original"]).all()
    assert con["pct"].between(0, 100, inclusive="neither").all()
    assert o[o["estado"] == NO_VALIDO]["precio_original"].isna().all()
    assert (o["estado"] == INCONSISTENTE).sum() == 4
    assert o[o["estado"] != CON_DESCUENTO]["pct"].isna().all()


def test_ranking_un_producto_una_vez(bot):
    r = bot.datos.ranking
    assert r["id_producto"].is_unique
    assert r["pct"].is_monotonic_decreasing


def test_cada_correccion_queda_registrada(bot):
    c = bot.datos.correcciones
    assert len(c) > 0 and c["motivo"].notna().all()
