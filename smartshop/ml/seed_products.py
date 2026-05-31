# =============================================================
#  ml/seed_products.py — Actualizar SOLO productos (sin borrar usuarios)
#  Ejecutar: python ml/seed_products.py
# =============================================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongodb import init_db
from ml.seed_data import PRODUCTS


def seed_products_only():
    db = init_db()
    db.products.drop()
    db.products.insert_many(PRODUCTS)
    db.products.create_index([("name", "text"), ("description", "text")])
    print(f"[OK] {len(PRODUCTS)} productos cargados (usuarios y pedidos intactos)")
    for cat in ("Tecnología", "Gaming", "Ropa", "Hogar"):
        n = db.products.count_documents({"category": cat})
        print(f"     {cat}: {n}")


if __name__ == "__main__":
    seed_products_only()
