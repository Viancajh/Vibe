# =============================================================
#  routes/dataset.py — Descarga del dataset en CSV
# =============================================================
from flask import Blueprint, send_file
from database.mongodb import get_db
from ml.export_dataset import export_interactions, export_orders, export_products

dataset_bp = Blueprint("dataset", __name__, url_prefix="/api/dataset")


def _send_csv(export_fn, filename: str):
    db = get_db()
    path, _ = export_fn(db)
    return send_file(
        path,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@dataset_bp.route("/interactions.csv")
def download_interactions():
    """GET /api/dataset/interactions.csv"""
    return _send_csv(export_interactions, "interactions.csv")


@dataset_bp.route("/orders.csv")
def download_orders():
    """GET /api/dataset/orders.csv"""
    return _send_csv(export_orders, "orders.csv")


@dataset_bp.route("/products.csv")
def download_products():
    """GET /api/dataset/products.csv"""
    return _send_csv(export_products, "products.csv")