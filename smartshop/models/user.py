# =============================================================
#  models/user.py — Modelo de Usuario
#  Define la estructura del documento en MongoDB
# =============================================================
from datetime import datetime
import bcrypt
from bson import ObjectId

# ── Esquema del documento "users" ──────────────────────────────
# {
#   _id         : ObjectId  (auto)
#   name        : str
#   email       : str       (único)
#   password    : str       (hash bcrypt)
#   created_at  : datetime
#   cluster     : int       (asignado por KMeans, -1 = sin asignar)
# }

def create_user(db, name: str, email: str, password: str) -> dict:
    """Crea un nuevo usuario con contraseña hasheada."""
    # Verificar que el email no exista
    if db.users.find_one({"email": email}):
        return None  # email duplicado

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    user = {
        "name"       : name,
        "email"      : email,
        "password"   : hashed.decode(),   # guardamos como string
        "created_at" : datetime.utcnow(),
        "cluster"    : -1,                # sin cluster aún
    }
    result = db.users.insert_one(user)
    user["_id"] = str(result.inserted_id)
    return user


def verify_password(db, email: str, password: str) -> dict | None:
    """Verifica credenciales y retorna el usuario o None."""
    user = db.users.find_one({"email": email})
    if not user:
        return None
    ok = bcrypt.checkpw(password.encode(), user["password"].encode())
    return user if ok else None


def get_user_by_id(db, user_id: str) -> dict | None:
    """Busca un usuario por su ObjectId."""
    try:
        return db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None


def serialize_user(user: dict) -> dict:
    """Convierte ObjectId a string para JSON (sin exponer contraseña)."""
    if not user:
        return {}
    out = {
        "_id": str(user["_id"]),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "notifications": user.get("notifications", True),
        "offers": user.get("offers", True),
        "cluster": user.get("cluster", -1),
    }
    if user.get("created_at"):
        out["created_at"] = user["created_at"].isoformat()
    return out


def update_user_profile(db, user_id: str, name: str = None, email: str = None,
                        phone: str = None, notifications: bool = None,
                        offers: bool = None) -> dict | str | None:
    """Actualiza datos del perfil. Retorna usuario, 'email_taken' o None."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        return None

    updates = {}
    if name is not None:
        name = name.strip()
        if name:
            updates["name"] = name
    if email is not None:
        email = email.strip().lower()
        if email:
            if db.users.find_one({"email": email, "_id": {"$ne": oid}}):
                return "email_taken"
            updates["email"] = email
    if phone is not None:
        updates["phone"] = phone.strip()
    if notifications is not None:
        updates["notifications"] = bool(notifications)
    if offers is not None:
        updates["offers"] = bool(offers)

    if not updates:
        return get_user_by_id(db, user_id)

    db.users.update_one({"_id": oid}, {"$set": updates})
    return get_user_by_id(db, user_id)


def change_user_password(db, user_id: str, current_password: str, new_password: str) -> str | None:
    """Cambia la contraseña. Retorna mensaje de error o None si ok."""
    user = get_user_by_id(db, user_id)
    if not user:
        return "Usuario no encontrado"
    if not bcrypt.checkpw(current_password.encode(), user["password"].encode()):
        return "Contraseña actual incorrecta"
    if len(new_password) < 6:
        return "La nueva contraseña debe tener al menos 6 caracteres"
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"password": hashed.decode()}})
    return None
