# =============================================================
#  routes/ml_lab.py — API del laboratorio ML (lista de cotejo)
# =============================================================
import json
import math
import os
import pickle

import numpy as np
from flask import Blueprint, jsonify, request

ML_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml")
METRICAS_PATH = os.path.join(ML_DIR, "proyecto_metricas.json")

ml_lab_bp = Blueprint("ml_lab", __name__, url_prefix="/api/ml")


def _limpiar_nan(obj):
    """Reemplaza NaN/Infinity por None: JSON.parse del navegador los rechaza.
    Aparecen, p.ej., en la matriz de correlacion cuando una columna es
    constante (varianza cero -> correlacion de Pearson indefinida)."""
    if isinstance(obj, dict):
        return {k: _limpiar_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_limpiar_nan(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def _cargar_pkl(nombre):
    ruta = os.path.join(ML_DIR, nombre)
    if not os.path.exists(ruta):
        return None
    with open(ruta, "rb") as f:
        return pickle.load(f)


@ml_lab_bp.route("/metricas")
def metricas():
    """GET /api/ml/metricas — Resultados del analisis y modelos."""
    if not os.path.exists(METRICAS_PATH):
        return jsonify({
            "error": "Aun no hay metricas. Ejecuta: python ml/analisis_proyecto.py",
        }), 404
    with open(METRICAS_PATH, encoding="utf-8") as f:
        return jsonify(_limpiar_nan(json.load(f))), 200


@ml_lab_bp.route("/graficas")
def graficas():
    """GET /api/ml/graficas — Lista de graficas generadas."""
    base = "/static/images/ml/"
    nombres = [
        "01_normalidad.png", "02_descriptivos.png", "03_outliers.png",
        "04_correlacion.png", "05_anova.png", "06_pca.png", "07_kmeans.png",
    ]
    existentes = [base + n for n in nombres if os.path.exists(
        os.path.join(os.path.dirname(ML_DIR), "static", "images", "ml", n)
    )]
    return jsonify(existentes), 200


@ml_lab_bp.route("/predecir-cluster", methods=["POST"])
def predecir_cluster():
    """
    POST /api/ml/predecir-cluster
    Clasificacion supervisada: predice el cluster del usuario.
    Body: {"Tecnologia": 50, "Gaming": 30, "Ropa": 10, "Hogar": 5}
    """
    datos = _cargar_pkl("cluster_classifier.pkl")
    if not datos:
        return jsonify({"error": "Entrena primero: python ml/analisis_proyecto.py"}), 503

    body = request.json or {}
    cats = datos["categorias"]
    try:
        X = np.array([[float(body.get(c, 0)) for c in cats]])
    except (TypeError, ValueError):
        return jsonify({"error": "Valores numericos invalidos"}), 400

    X_s = datos["scaler"].transform(X)
    cluster = int(datos["model"].predict(X_s)[0])

    return jsonify({
        "cluster_predicho": cluster,
        "mensaje": f"El usuario pertenece al cluster {cluster}",
        "tipo": "Clasificacion supervisada (RandomForest)",
        "entrada": {c: body.get(c, 0) for c in cats},
    }), 200


@ml_lab_bp.route("/predecir-precio", methods=["POST"])
def predecir_precio():
    """
    POST /api/ml/predecir-precio
    Regresion supervisada: predice precio del producto.
    Body: {"rating": 4.5, "views": 200, "purchases": 30, "stock": 20}
    """
    datos = _cargar_pkl("regression_model.pkl")
    if not datos:
        return jsonify({"error": "Entrena primero: python ml/analisis_proyecto.py"}), 503

    body = request.json or {}
    feats = datos["features"]
    try:
        X = np.array([[float(body.get(f, 0)) for f in feats]])
    except (TypeError, ValueError):
        return jsonify({"error": "Valores numericos invalidos"}), 400

    X_s = datos["scaler"].transform(X)
    precio = float(datos["model"].predict(X_s)[0])

    return jsonify({
        "precio_predicho": round(precio, 2),
        "tipo": "Regresion supervisada (LinearRegression)",
        "metricas_modelo": _metricas_regresion(),
        "entrada": {f: body.get(f, 0) for f in feats},
    }), 200


@ml_lab_bp.route("/predecir-precio-ann", methods=["POST"])
def predecir_precio_ann():
    """
    POST /api/ml/predecir-precio-ann
    Red neuronal artificial: predice precio del producto.
    """
    datos = _cargar_pkl("ann_model.pkl")
    if not datos:
        return jsonify({"error": "Entrena primero: python ml/analisis_proyecto.py"}), 503

    body = request.json or {}
    feats = datos["features"]
    try:
        X = np.array([[float(body.get(f, 0)) for f in feats]])
    except (TypeError, ValueError):
        return jsonify({"error": "Valores numericos invalidos"}), 400

    X_s = datos["scaler"].transform(X)
    precio = float(datos["model"].predict(X_s)[0])

    return jsonify({
        "precio_predicho": round(precio, 2),
        "tipo": "Red neuronal artificial (MLPRegressor)",
        "metricas_modelo": _metricas_ann(),
        "entrada": {f: body.get(f, 0) for f in feats},
    }), 200


def _leer_metricas():
    if not os.path.exists(METRICAS_PATH):
        return {}
    with open(METRICAS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _metricas_regresion():
    m = _leer_metricas().get("regresion", {})
    return {"r2": m.get("r2"), "mae": m.get("mae"), "rmse": m.get("rmse")}


def _metricas_ann():
    m = _leer_metricas().get("ann", {})
    return {"r2": m.get("r2"), "mae": m.get("mae"), "mse": m.get("mse")}
