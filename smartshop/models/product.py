# =============================================================
#  models/product.py — Modelo de Producto
# =============================================================
from bson import ObjectId
from datetime import datetime

# ── Esquema del documento "products" ──────────────────────────
# {
#   _id         : ObjectId
#   name        : str
#   description : str
#   price       : float
#   category    : str   ("Tecnología" | "Gaming" | "Ropa" | "Hogar")
#   image       : str   (URL o ruta)
#   stock       : int
#   rating      : float
#   views       : int
#   purchases   : int
#   created_at  : datetime
# }

def serialize_product(p: dict) -> dict:
    """Convierte ObjectId a string."""
    if p:
        p["_id"] = str(p["_id"])
    return p


def get_all_products(db, category: str = None, limit: int = 200) -> list:
    query = {"category": category} if category else {}
    products = list(db.products.find(query).limit(limit))
    return [serialize_product(p) for p in products]


def get_product_by_id(db, product_id: str) -> dict | None:
    try:
        p = db.products.find_one({"_id": ObjectId(product_id)})
        return serialize_product(p) if p else None
    except Exception:
        return None


def search_products(db, query: str) -> list:
    """Búsqueda por texto completo (requiere índice de texto)."""
    results = list(db.products.find(
        {"$text": {"$search": query}},
        {"score": {"$meta": "textScore"}}
    ).sort([("score", {"$meta": "textScore"})]).limit(20))
    return [serialize_product(p) for p in results]


def increment_views(db, product_id: str):
    """Incrementa el contador de vistas."""
    try:
        db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$inc": {"views": 1}}
        )
    except Exception:
        pass


def get_popular_products(db, limit: int = 16) -> list:
    """Retorna los productos más vistos."""
    products = list(db.products.find().sort("views", -1).limit(limit))
    return [serialize_product(p) for p in products]


def buy_product(db, product_id: str, quantity: int = 1) -> bool:
    """Registra una compra: descuenta stock e incrementa vendidos.

    Operación atómica: solo procede si hay stock suficiente.
    Devuelve True si se concretó, False si no había stock.
    """
    try:
        result = db.products.update_one(
            {"_id": ObjectId(product_id), "stock": {"$gte": quantity}},
            {"$inc": {"stock": -quantity, "purchases": quantity}},
        )
        return result.modified_count == 1
    except Exception:
        return False
