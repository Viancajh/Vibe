# =============================================================
#  routes/recommendations.py — Recomendaciones con ML
# =============================================================
import os
import pickle

import numpy as np
from bson import ObjectId
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from database.mongodb import get_db
from ml.features import FEATURE_COLUMNS, fila_para_random_forest
from models.interaction import get_favorite_categories, get_purchased_products, get_viewed_products
from models.product import get_popular_products, serialize_product

recommendations_bp = Blueprint("recommendations", __name__, url_prefix="/api/recommendations")

ML_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml")


def _productos_por_ids(db, ids):
    out = []
    for pid in ids:
        try:
            p = db.products.find_one({"_id": ObjectId(pid)})
            if p:
                out.append(serialize_product(p))
        except Exception:
            pass
    return out


@recommendations_bp.route("/for-you", methods=["GET"])
@jwt_required()
def for_you():
    """Recomendaciones por categorias favoritas (reglas, sin modelo)."""
    user_id = get_jwt_identity()
    db = get_db()

    vistos = set(get_viewed_products(db, user_id))
    comprados = set(get_purchased_products(db, user_id))
    fav_cats = get_favorite_categories(db, user_id)
    resultado = []

    if fav_cats:
        candidatos = list(db.products.aggregate([
            {"$match": {"category": {"$in": fav_cats}}},
            {"$sort": {"purchases": -1, "views": -1}},
            {"$limit": 12},
        ]))
        for p in candidatos:
            pid = str(p["_id"])
            if pid not in vistos and pid not in comprados:
                resultado.append(serialize_product(p))
            if len(resultado) >= 8:
                break

    if len(resultado) < 8:
        vistos_ids = {p["_id"] for p in resultado}
        for p in get_popular_products(db, 12):
            if p["_id"] not in vistos_ids and p["_id"] not in vistos:
                resultado.append(p)
            if len(resultado) >= 8:
                break

    return jsonify(resultado[:8]), 200


@recommendations_bp.route("/similar-users", methods=["GET"])
@jwt_required()
def similar_users():
    """Usa KMeans (no supervisado): productos que compraron usuarios del mismo cluster."""
    user_id = get_jwt_identity()
    db = get_db()
    ruta = os.path.join(ML_DIR, "kmeans_model.pkl")

    if not os.path.exists(ruta):
        return jsonify(get_popular_products(db, 6)), 200

    try:
        with open(ruta, "rb") as f:
            datos = pickle.load(f)
        clusters = datos["user_clusters"]

        if user_id not in clusters:
            return jsonify(get_popular_products(db, 6)), 200

        mi_cluster = clusters[user_id]
        parecidos = [
            uid for uid, c in clusters.items()
            if c == mi_cluster and uid != user_id
        ][:10]

        productos_ids = set()
        for uid in parecidos:
            for doc in db.interactions.find({"user_id": uid, "action": "purchase"}):
                productos_ids.add(doc["product_id"])

        mis_compras = set(get_purchased_products(db, user_id))
        recomendar = list(productos_ids - mis_compras)[:8]
        productos = _productos_por_ids(db, recomendar)

        if len(productos) < 4:
            vistos = {p["_id"] for p in productos}
            for p in get_popular_products(db, 8):
                if p["_id"] not in vistos:
                    productos.append(p)
                if len(productos) >= 6:
                    break

        return jsonify(productos[:6]), 200
    except Exception as e:
        print(f"similar-users: {e}")
        return jsonify(get_popular_products(db, 6)), 200


@recommendations_bp.route("/purchase-probability/<product_id>", methods=["GET"])
@jwt_required()
def purchase_probability(product_id):
    """Usa RandomForest (supervisado): probabilidad de que el usuario compre."""
    user_id = get_jwt_identity()
    db = get_db()
    ruta = os.path.join(ML_DIR, "rf_model.pkl")

    if not os.path.exists(ruta):
        return jsonify({"probability": 0.5, "label": "Modelo no entrenado aun"}), 200

    try:
        with open(ruta, "rb") as f:
            datos = pickle.load(f)
        modelo = datos["model"]

        producto = db.products.find_one({"_id": ObjectId(product_id)})
        if not producto:
            return jsonify({"probability": 0}), 404

        ints = list(db.interactions.find({"user_id": user_id, "product_id": product_id}))
        fila = fila_para_random_forest(ints, producto)
        X = np.array([[fila[c] for c in FEATURE_COLUMNS]])
        prob = float(modelo.predict_proba(X)[0][1])

        if prob > 0.7:
            etiqueta = "Alta probabilidad"
        elif prob > 0.4:
            etiqueta = "Probabilidad media"
        else:
            etiqueta = "Baja probabilidad"

        return jsonify({"probability": round(prob, 2), "label": etiqueta}), 200
    except Exception as e:
        print(f"purchase-probability: {e}")
        return jsonify({"probability": 0.5}), 200
