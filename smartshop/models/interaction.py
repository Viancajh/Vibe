# =============================================================
#  models/interaction.py — Modelo de Interacciones
#  Registra TODA la actividad del usuario para el ML
# =============================================================
from datetime import datetime
from bson import ObjectId

# ── Esquema del documento "interactions" ──────────────────────
# {
#   _id         : ObjectId
#   user_id     : str
#   product_id  : str
#   action      : str  ("view" | "click" | "cart" | "purchase" | "search")
#   category    : str
#   duration    : int  (segundos en la página, solo para "view")
#   timestamp   : datetime
# }

# Pesos por acción (usados para calcular score de preferencia)
ACTION_WEIGHTS = {
    "click"    : 1,
    "view"     : 2,
    "cart"     : 5,
    "purchase" : 10,
    "search"   : 1,
}


def log_interaction(db, user_id: str, product_id: str,
                    action: str, category: str = "", duration: int = 0):
    """Guarda una interacción del usuario en MongoDB."""
    doc = {
        "user_id"    : user_id,
        "product_id" : product_id,
        "action"     : action,
        "category"   : category,
        "duration"   : duration,
        "timestamp"  : datetime.utcnow(),
        "weight"     : ACTION_WEIGHTS.get(action, 1),
    }
    db.interactions.insert_one(doc)
    # Alimentar el dataset CSV en tiempo real (no rompe la petición si falla)
    from ml.export_dataset import append_interaction
    append_interaction(doc)
    return doc


def get_user_interactions(db, user_id: str, limit: int = 100) -> list:
    """Retorna las últimas N interacciones de un usuario."""
    docs = list(
        db.interactions
          .find({"user_id": user_id})
          .sort("timestamp", -1)
          .limit(limit)
    )
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


def get_favorite_categories(db, user_id: str) -> list:
    """Calcula las categorías favoritas del usuario por peso acumulado."""
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id"          : "$category",
            "total_weight" : {"$sum": "$weight"}
        }},
        {"$sort": {"total_weight": -1}},
        {"$limit": 3}
    ]
    result = list(db.interactions.aggregate(pipeline))
    return [r["_id"] for r in result if r["_id"]]


def get_viewed_products(db, user_id: str, limit: int = 20) -> list:
    """Retorna IDs de productos que el usuario ha visto."""
    pipeline = [
        {"$match": {"user_id": user_id, "action": {"$in": ["view", "click"]}}},
        {"$group": {"_id": "$product_id"}},
        {"$limit": limit}
    ]
    result = list(db.interactions.aggregate(pipeline))
    return [r["_id"] for r in result]


def get_purchased_products(db, user_id: str) -> list:
    """Retorna IDs de productos comprados por el usuario."""
    docs = db.interactions.find({"user_id": user_id, "action": "purchase"})
    return [d["product_id"] for d in docs]

