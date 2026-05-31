# =============================================================
#  routes/products.py — CRUD y búsqueda de productos
# =============================================================
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from database.mongodb import get_db
from models.product import (get_all_products, get_product_by_id,
                             search_products, increment_views, get_popular_products)
from models.interaction import log_interaction
from realtime import publish_product

products_bp = Blueprint("products", __name__, url_prefix="/api/products")


@products_bp.route("/", methods=["GET"])
def list_products():
    """GET /api/products/?category=Gaming — Lista productos, filtra por categoría."""
    category = request.args.get("category")
    db = get_db()
    products = get_all_products(db, category)
    return jsonify(products), 200


@products_bp.route("/popular", methods=["GET"])
def popular():
    """GET /api/products/popular — Top productos más vistos."""
    db = get_db()
    return jsonify(get_popular_products(db)), 200


@products_bp.route("/search", methods=["GET"])
def search():
    """GET /api/products/search?q=laptop — Búsqueda por texto."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([]), 200
    db = get_db()

    # Registrar búsqueda si hay usuario autenticado
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            log_interaction(db, user_id, "", "search", q[:50])
    except Exception:
        pass

    return jsonify(search_products(db, q)), 200


@products_bp.route("/<product_id>", methods=["GET"])
def product_detail(product_id):
    """GET /api/products/<id> — Detalle de un producto y registra vista."""
    db = get_db()
    product = get_product_by_id(db, product_id)
    if not product:
        return jsonify({"error": "Producto no encontrado"}), 404

    # Incrementar vistas siempre y difundir el nuevo conteo en tiempo real
    increment_views(db, product_id)
    publish_product(db, product_id)

    # Registrar interacción si hay sesión activa
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            log_interaction(db, user_id, product_id, "view", product.get("category", ""))
    except Exception:
        pass

    return jsonify(product), 200
