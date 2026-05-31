# =============================================================
#  routes/account.py — Perfil, tarjetas y pedidos del usuario
# =============================================================
import random
import uuid
from datetime import datetime, timedelta

from bson import ObjectId
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from database.mongodb import get_db
from models.user import get_user_by_id, serialize_user, update_user_profile, change_user_password

account_bp = Blueprint("account", __name__, url_prefix="/api/account")

TRACKING_STEPS = [
    "Pedido confirmado",
    "Preparando envío",
    "En tránsito",
    "Entregado",
]


def _generar_guia():
    return f"VIBE-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(100000, 999999)}"


def _pasos_seguimiento(creado: datetime, status: str) -> list:
    """Genera la línea de tiempo del pedido según antigüedad."""
    horas = (datetime.utcnow() - creado).total_seconds() / 3600
    if status == "entregado" or horas > 72:
        activo = 4
    elif horas > 24:
        activo = 3
    elif horas > 2:
        activo = 2
    else:
        activo = 1

    pasos = []
    for i, label in enumerate(TRACKING_STEPS):
        done = i < activo
        fecha = creado + timedelta(hours=i * 8) if done else None
        pasos.append({
            "label": label,
            "done": done,
            "date": fecha.isoformat() if fecha else None,
        })
    return pasos


def _estado_texto(pasos: list) -> str:
    for p in reversed(pasos):
        if p["done"]:
            return p["label"]
    return "Pedido confirmado"


def _serializar_orden(doc: dict) -> dict:
    creado = doc.get("created_at", datetime.utcnow())
    pasos = doc.get("tracking_steps") or _pasos_seguimiento(creado, doc.get("status", ""))
    return {
        "_id": str(doc["_id"]),
        "items": doc.get("items", []),
        "subtotal": doc.get("subtotal", 0),
        "shipping_cost": doc.get("shipping_cost", 0),
        "total": doc.get("total", 0),
        "payment_method": doc.get("payment_method", ""),
        "shipping": doc.get("shipping", {}),
        "status": doc.get("status", "confirmado"),
        "tracking_number": doc.get("tracking_number", ""),
        "tracking_status": doc.get("tracking_status") or _estado_texto(pasos),
        "tracking_steps": pasos,
        "created_at": creado.isoformat() if creado else "",
    }


@account_bp.route("/profile", methods=["GET"])
@jwt_required()
def perfil():
    user_id = get_jwt_identity()
    db = get_db()
    user = get_user_by_id(db, user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado. Inicia sesión de nuevo."}), 404
    data = serialize_user(user)
    data["member_since"] = user.get("created_at", datetime.utcnow()).isoformat()
    return jsonify(data), 200


@account_bp.route("/profile", methods=["PUT"])
@jwt_required()
def actualizar_perfil():
    user_id = get_jwt_identity()
    data = request.json or {}
    db = get_db()

    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    notifications = data.get("notifications")
    offers = data.get("offers")

    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({"error": "El nombre es obligatorio"}), 400
    if email is not None:
        email = email.strip().lower()
        if not email:
            return jsonify({"error": "El correo es obligatorio"}), 400

    result = update_user_profile(
        db, user_id,
        name=name,
        email=email,
        phone=phone if phone is not None else None,
        notifications=notifications if notifications is not None else None,
        offers=offers if offers is not None else None,
    )
    if result is None:
        return jsonify({"error": "Usuario no encontrado. Inicia sesión de nuevo."}), 404
    if result == "email_taken":
        return jsonify({"error": "Ese correo ya está registrado"}), 409

    out = serialize_user(result)
    out["member_since"] = result.get("created_at", datetime.utcnow()).isoformat()
    return jsonify({"message": "Perfil actualizado", "user": out}), 200


@account_bp.route("/password", methods=["PUT"])
@jwt_required()
def cambiar_password():
    user_id = get_jwt_identity()
    data = request.json or {}
    current = data.get("current_password", "")
    new_pwd = data.get("new_password", "")
    confirm = data.get("confirm_password", "")

    if not current or not new_pwd:
        return jsonify({"error": "Completa todos los campos de contraseña"}), 400
    if new_pwd != confirm:
        return jsonify({"error": "Las contraseñas nuevas no coinciden"}), 400

    db = get_db()
    err = change_user_password(db, user_id, current, new_pwd)
    if err:
        status = 404 if "no encontrado" in err.lower() else 400
        return jsonify({"error": err}), status
    return jsonify({"message": "Contraseña actualizada correctamente"}), 200


@account_bp.route("/orders", methods=["GET"])
@jwt_required()
def listar_pedidos():
    user_id = get_jwt_identity()
    db = get_db()
    docs = list(
        db.orders.find({"user_id": user_id}).sort("created_at", -1).limit(50)
    )
    return jsonify([_serializar_orden(d) for d in docs]), 200


@account_bp.route("/orders/<order_id>", methods=["GET"])
@jwt_required()
def detalle_pedido(order_id):
    user_id = get_jwt_identity()
    db = get_db()
    try:
        doc = db.orders.find_one({"_id": ObjectId(order_id), "user_id": user_id})
    except Exception:
        doc = None
    if not doc:
        return jsonify({"error": "Pedido no encontrado"}), 404
    return jsonify(_serializar_orden(doc)), 200


@account_bp.route("/cards", methods=["GET"])
@jwt_required()
def listar_tarjetas():
    user_id = get_jwt_identity()
    db = get_db()
    user = get_user_by_id(db, user_id)
    if not user:
        return jsonify([]), 200
    cards = user.get("cards", [])
    return jsonify(cards), 200


@account_bp.route("/cards", methods=["POST"])
@jwt_required()
def agregar_tarjeta():
    user_id = get_jwt_identity()
    data = request.json or {}
    number = (data.get("number") or "").replace(" ", "")
    holder = (data.get("holder") or "").strip()
    exp    = (data.get("exp") or "").strip()

    if len(number) < 4 or not holder or not exp:
        return jsonify({"error": "Completa los datos de la tarjeta"}), 400

    brand = "Visa" if number.startswith("4") else "Mastercard" if number.startswith("5") else "Tarjeta"
    card = {
        "id": str(uuid.uuid4())[:8],
        "last4": number[-4:],
        "brand": brand,
        "holder": holder,
        "exp": exp,
        "default": bool(data.get("default", False)),
    }

    db = get_db()
    user = get_user_by_id(db, user_id)
    cards = user.get("cards", []) if user else []
    if card["default"]:
        for c in cards:
            c["default"] = False
    if len(cards) == 0:
        card["default"] = True
    cards.append(card)
    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"cards": cards}})
    return jsonify({"message": "Tarjeta guardada", "card": card}), 201


@account_bp.route("/cards/<card_id>", methods=["DELETE"])
@jwt_required()
def eliminar_tarjeta(card_id):
    user_id = get_jwt_identity()
    db = get_db()
    user = get_user_by_id(db, user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    cards = [c for c in user.get("cards", []) if c.get("id") != card_id]
    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"cards": cards}})
    return jsonify({"message": "Tarjeta eliminada"}), 200
