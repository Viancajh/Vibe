# =============================================================
#  ml/features.py — Variables de entrada compartidas por los modelos
# =============================================================

# Columnas que usa RandomForest (mismo orden siempre)
FEATURE_COLUMNS = [
    "n_views",       # cuantas veces vio el producto
    "n_clicks",      # cuantas veces hizo clic
    "n_cart",        # cuantas veces lo puso en carrito
    "avg_duration",  # segundos promedio en la pagina del producto
    "price_norm",    # precio / 1000 (escala similar a las demas)
    "rating",        # calificacion del producto (1 a 5)
]

CATEGORIAS = ["Tecnología", "Gaming", "Ropa", "Hogar"]


def contar_acciones(interacciones):
    """Resume las interacciones de un usuario con UN producto."""
    n_views = n_clicks = n_cart = 0
    total_dur = 0
    compro = 0

    for i in interacciones:
        accion = i.get("action")
        if accion == "view":
            n_views += 1
            total_dur += i.get("duration", 0)
        elif accion == "click":
            n_clicks += 1
        elif accion == "cart":
            n_cart += 1
        elif accion == "purchase":
            compro = 1

    return {
        "n_views": n_views,
        "n_clicks": n_clicks,
        "n_cart": n_cart,
        "avg_duration": total_dur / max(n_views, 1),
        "purchased": compro,
    }


def fila_para_random_forest(interacciones, producto):
    """Una fila del dataset supervisado: comportamiento + producto + etiqueta."""
    c = contar_acciones(interacciones)
    return {
        **c,
        "price_norm": producto.get("price", 0) / 1000.0,
        "rating": producto.get("rating", 3.0),
    }


def vector_usuario_por_categoria(interacciones, productos_por_id):
    """
    Vector de 4 numeros: interes en cada categoria (para KMeans).
    Sin etiquetas: solo sumamos el peso de cada accion por categoria.
    """
    puntajes = {c: 0.0 for c in CATEGORIAS}
    for i in interacciones:
        prod = productos_por_id.get(i.get("product_id", ""))
        if not prod:
            continue
        cat = prod.get("category", "")
        if cat in puntajes:
            puntajes[cat] += i.get("weight", 1)
    return [puntajes[c] for c in CATEGORIAS]
