# =============================================================
#  routes/interactions.py — Registra interacciones del usuario
#  El frontend llama estos endpoints automáticamente (tracker.js)
# =============================================================
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.mongodb import get_db
from models.interaction import (log_interaction, get_user_interactions,
                                  get_favorite_categories, get_viewed_products)

interactions_bp = Blueprint("interactions", __name__, url_prefix="/api/interactions")


@interactions_bp.route("/track", methods=["POST"])
@jwt_required()
def track():
    """
    POST /api/interactions/track
    Body: { product_id, action, category, duration }
    Acciones válidas: click | view | cart | purchase | search
    """
    user_id = get_jwt_identity()
    data = request.json or {}

    product_id = data.get("product_id", "")
    action     = data.get("action", "click")
    category   = data.get("category", "")
    duration   = int(data.get("duration", 0))

    db = get_db()
    log_interaction(db, user_id, product_id, action, category, duration)
    return jsonify({"ok": True}), 201


@interactions_bp.route("/history", methods=["GET"])
@jwt_required()
def history():
    """GET /api/interactions/history — Historial de interacciones del usuario."""
    user_id = get_jwt_identity()
    db = get_db()
    interactions = get_user_interactions(db, user_id, limit=50)
    return jsonify(interactions), 200


@interactions_bp.route("/favorites", methods=["GET"])
@jwt_required()
def favorites():
    """GET /api/interactions/favorites — Categorías favoritas del usuario."""
    user_id = get_jwt_identity()
    db = get_db()
    cats = get_favorite_categories(db, user_id)
    return jsonify({"favorite_categories": cats}), 200


@interactions_bp.route("/viewed", methods=["GET"])
@jwt_required()
def viewed():
    """GET /api/interactions/viewed — Productos vistos recientemente."""
    user_id = get_jwt_identity()
    db = get_db()
    product_ids = get_viewed_products(db, user_id, limit=10)

    # Obtener datos completos de esos productos
    from bson import ObjectId
    from models.product import serialize_product
    products = []
    for pid in product_ids:
        try:
            p = db.products.find_one({"_id": ObjectId(pid)})
            if p:
                products.append(serialize_product(p))
        except Exception:
            pass
    return jsonify(products), 200
