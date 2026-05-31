# =============================================================
#  routes/cart.py — Carrito de compras
# =============================================================
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from database.mongodb import get_db
from models.product import get_product_by_id
from models.interaction import log_interaction
from routes.account import _generar_guia, _pasos_seguimiento

cart_bp = Blueprint("cart", __name__, url_prefix="/api/cart")

# ── Helpers ────────────────────────────────────────────────────

def _get_or_create_cart(db, user_id: str) -> dict:
    cart = db.carts.find_one({"user_id": user_id})
    if not cart:
        db.carts.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {"user_id": user_id, "items": []}},
            upsert=True,
        )
        cart = db.carts.find_one({"user_id": user_id})
    return cart


def _serialize_cart(cart: dict) -> dict:
    cart["_id"] = str(cart["_id"])
    return cart

# ── Rutas ──────────────────────────────────────────────────────

@cart_bp.route("/", methods=["GET"])
@jwt_required()
def get_cart():
    """GET /api/cart/ — Retorna el carrito del usuario."""
    user_id = get_jwt_identity()
    db = get_db()
    cart = _get_or_create_cart(db, user_id)
    return jsonify(_serialize_cart(cart)), 200


@cart_bp.route("/add", methods=["POST"])
@jwt_required()
def add_to_cart():
    """POST /api/cart/add — Agrega un producto al carrito."""
    user_id = get_jwt_identity()
    data = request.json or {}
    product_id = data.get("product_id")
    quantity   = int(data.get("quantity", 1))

    db = get_db()
    product = get_product_by_id(db, product_id)
    if not product:
        return jsonify({"error": "Producto no encontrado"}), 404

    cart = _get_or_create_cart(db, user_id)
    items = cart.get("items", [])

    # Si ya existe, suma cantidad
    found = False
    for item in items:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            found = True
            break
    if not found:
        items.append({
            "product_id" : product_id,
            "name"       : product["name"],
            "price"      : product["price"],
            "image"      : product.get("image", ""),
            "quantity"   : quantity,
        })

    db.carts.update_one({"user_id": user_id}, {"$set": {"items": items}})

    # Registrar interacción
    log_interaction(db, user_id, product_id, "cart", product.get("category", ""))

    return jsonify({"message": "Producto agregado al carrito", "items_count": len(items)}), 200


@cart_bp.route("/remove/<product_id>", methods=["DELETE"])
@jwt_required()
def remove_from_cart(product_id):
    """DELETE /api/cart/remove/<id> — Elimina un producto del carrito."""
    user_id = get_jwt_identity()
    db = get_db()
    cart = _get_or_create_cart(db, user_id)
    items = [i for i in cart.get("items", []) if i["product_id"] != product_id]
    db.carts.update_one({"user_id": user_id}, {"$set": {"items": items}})
    return jsonify({"message": "Producto eliminado"}), 200


VALID_PAYMENT_METHODS = {"tarjeta", "transferencia", "efectivo"}
ENVIO_GRATIS_DESDE = 1500
COSTO_ENVIO = 149


def _calcular_envio(subtotal: float) -> float:
    return 0.0 if subtotal >= ENVIO_GRATIS_DESDE else float(COSTO_ENVIO)


@cart_bp.route("/checkout", methods=["POST"])
@jwt_required()
def checkout():
    """POST /api/cart/checkout — Simula la compra y vacía el carrito."""
    user_id = get_jwt_identity()
    data = request.json or {}
    db = get_db()
    cart = _get_or_create_cart(db, user_id)
    items = cart.get("items", [])

    if not items:
        return jsonify({"error": "El carrito está vacío"}), 400

    payment_method = data.get("payment_method", "tarjeta")
    if payment_method not in VALID_PAYMENT_METHODS:
        return jsonify({"error": "Método de pago no válido"}), 400

    shipping = data.get("shipping") or {}
    if not shipping.get("name") or not shipping.get("address") or not shipping.get("city"):
        return jsonify({"error": "Completa los datos de envío"}), 400

    subtotal = sum(i["price"] * i["quantity"] for i in items)
    shipping_cost = _calcular_envio(subtotal)
    total = subtotal + shipping_cost

    # Registrar compra e incrementar contador de productos
    for item in items:
        product = get_product_by_id(db, item["product_id"])
        category = product.get("category", "") if product else ""
        log_interaction(db, user_id, item["product_id"], "purchase", category)
        db.products.update_one(
            {"_id": ObjectId(item["product_id"])},
            {"$inc": {"purchases": item["quantity"]}}
        )

    from datetime import datetime
    tracking_number = _generar_guia()
    creado = datetime.utcnow()
    pasos = _pasos_seguimiento(creado, "confirmado")

    # Guardar tarjeta si el usuario lo pidió (solo últimos 4 dígitos)
    card_info = data.get("card") or {}
    if payment_method == "tarjeta" and card_info.get("save") and card_info.get("number"):
        num = card_info["number"].replace(" ", "")
        if len(num) >= 4:
            import uuid
            brand = "Visa" if num.startswith("4") else "Mastercard" if num.startswith("5") else "Tarjeta"
            nueva = {
                "id": str(uuid.uuid4())[:8],
                "last4": num[-4:],
                "brand": brand,
                "holder": card_info.get("holder", shipping.get("name", "")),
                "exp": card_info.get("exp", ""),
                "default": True,
            }
            user = db.users.find_one({"_id": ObjectId(user_id)})
            cards = user.get("cards", []) if user else []
            cards = [c for c in cards if c.get("last4") != nueva["last4"]]
            for c in cards:
                c["default"] = False
            cards.insert(0, nueva)
            db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"cards": cards}})

    order = {
        "user_id"          : user_id,
        "items"            : items,
        "subtotal"         : subtotal,
        "shipping_cost"    : shipping_cost,
        "total"            : total,
        "payment_method"   : payment_method,
        "shipping"         : {
            "name"    : shipping.get("name", ""),
            "address" : shipping.get("address", ""),
            "city"    : shipping.get("city", ""),
            "zip"     : shipping.get("zip", ""),
        },
        "tracking_number"  : tracking_number,
        "tracking_status"  : "Pedido confirmado",
        "tracking_steps"   : pasos,
        "created_at"       : creado,
        "status"           : "confirmado",
    }
    result = db.orders.insert_one(order)

    db.carts.update_one({"user_id": user_id}, {"$set": {"items": []}})

    return jsonify({
        "message"        : "¡Compra realizada con éxito!",
        "subtotal"       : subtotal,
        "shipping_cost"  : shipping_cost,
        "total"          : total,
        "payment_method" : payment_method,
        "order_id"       : str(result.inserted_id),
        "tracking_number": tracking_number,
    }), 200
