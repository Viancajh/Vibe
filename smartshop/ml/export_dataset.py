# =============================================================
#  ml/export_dataset.py — Exportar datos de MongoDB a CSV
#  Uso: python ml/export_dataset.py
# =============================================================
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongodb import init_db

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def export_interactions(db, path: str | None = None) -> tuple[str, int]:
    """Exporta interacciones usuario–producto para ML."""
    path = path or os.path.join(DATA_DIR, "interactions.csv")
    _ensure_dir()

    rows = db.interactions.find().sort("timestamp", 1)
    fieldnames = [
        "interaction_id", "user_id", "product_id", "action",
        "category", "duration_sec", "weight", "timestamp",
    ]

    count = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for doc in rows:
            writer.writerow({
                "interaction_id": str(doc["_id"]),
                "user_id": doc.get("user_id", ""),
                "product_id": doc.get("product_id", ""),
                "action": doc.get("action", ""),
                "category": doc.get("category", ""),
                "duration_sec": doc.get("duration", 0),
                "weight": doc.get("weight", 1),
                "timestamp": doc.get("timestamp", "").isoformat()
                if doc.get("timestamp") else "",
            })
            count += 1

    return path, count


def export_orders(db, path: str | None = None) -> tuple[str, int]:
    """Exporta pedidos (una fila por ítem del carrito)."""
    path = path or os.path.join(DATA_DIR, "orders.csv")
    _ensure_dir()

    fieldnames = [
        "order_id", "user_id", "product_id", "product_name",
        "quantity", "unit_price", "line_total", "order_total",
        "payment_method", "shipping_name", "shipping_city",
        "status", "created_at",
    ]

    count = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for order in db.orders.find().sort("created_at", 1):
            shipping = order.get("shipping") or {}
            items = order.get("items") or []
            order_total = order.get("total", 0)
            created = order.get("created_at")
            created_str = created.isoformat() if created else ""

            for item in items:
                qty = item.get("quantity", 1)
                price = item.get("price", 0)
                writer.writerow({
                    "order_id": str(order["_id"]),
                    "user_id": order.get("user_id", ""),
                    "product_id": item.get("product_id", ""),
                    "product_name": item.get("name", ""),
                    "quantity": qty,
                    "unit_price": price,
                    "line_total": round(price * qty, 2),
                    "order_total": order_total,
                    "payment_method": order.get("payment_method", ""),
                    "shipping_name": shipping.get("name", ""),
                    "shipping_city": shipping.get("city", ""),
                    "status": order.get("status", ""),
                    "created_at": created_str,
                })
                count += 1

    return path, count


def export_products(db, path: str | None = None) -> tuple[str, int]:
    """Catálogo de productos para el dataset."""
    path = path or os.path.join(DATA_DIR, "products.csv")
    _ensure_dir()

    fieldnames = [
        "product_id", "name", "category", "price",
        "stock", "rating", "views", "purchases",
    ]

    count = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in db.products.find():
            writer.writerow({
                "product_id": str(p["_id"]),
                "name": p.get("name", ""),
                "category": p.get("category", ""),
                "price": p.get("price", 0),
                "stock": p.get("stock", 0),
                "rating": p.get("rating", 0),
                "views": p.get("views", 0),
                "purchases": p.get("purchases", 0),
            })
            count += 1

    return path, count


def export_all(db=None):
    db = db if db is not None else init_db()
    paths = []
    for name, fn in [
        ("interacciones", export_interactions),
        ("pedidos", export_orders),
        ("productos", export_products),
    ]:
        path, n = fn(db)
        paths.append((name, path, n))
        print(f"  {name}: {n} filas -> {path}")
    print(f"\n  Archivos en: {DATA_DIR}")
    return paths


if __name__ == "__main__":
    print("Exportando dataset CSV...\n")
    export_all()
