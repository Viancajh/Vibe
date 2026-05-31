
# =============================================================
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from database.mongodb import get_db
from models.user import create_user, verify_password, get_user_by_id, serialize_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """POST /api/auth/register — Crea una cuenta nueva."""
    data = request.json or {}
    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not all([name, email, password]):
        return jsonify({"error": "Todos los campos son obligatorios"}), 400
    if len(password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400

    db   = get_db()
    user = create_user(db, name, email, password)
    if user is None:
        return jsonify({"error": "El email ya está registrado"}), 409

    token = create_access_token(identity=str(user["_id"]))
    return jsonify({
        "message" : "Cuenta creada exitosamente",
        "token"   : token,
        "user"    : {"name": name, "email": email}
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """POST /api/auth/login — Inicia sesión y retorna JWT."""
    data     = request.json or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    db   = get_db()
    user = verify_password(db, email, password)
    if not user:
        return jsonify({"error": "Credenciales incorrectas"}), 401

    token = create_access_token(identity=str(user["_id"]))
    return jsonify({
        "message" : "Sesión iniciada",
        "token"   : token,
        "user"    : {"name": user["name"], "email": user["email"], "id": str(user["_id"])}
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """GET /api/auth/me — Retorna datos del usuario autenticado."""
    user_id = get_jwt_identity()
    db      = get_db()
    user    = get_user_by_id(db, user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify(serialize_user(user)), 200
