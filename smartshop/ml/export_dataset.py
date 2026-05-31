# =============================================================
#  ml/export_dataset.py — Exportar datos de MongoDB a CSV
#
#  Dos modos:
#   - export_*()  : regenera el CSV completo desde MongoDB (al descargar/seed).
#   - append_*()  : agrega filas en TIEMPO REAL cuando ocurre un evento
#                   (una interacción o una orden), sin reescribir todo.
#
#  Uso manual: python ml/export_dataset.py
# =============================================================
import csv
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongodb import init_db

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Lock para que los appends concurrentes (servidor con hilos) no se intercalen.
_write_lock = threading.Lock()

# ── Campos de cada CSV (una sola fuente de verdad) ─────────────
INTERACTION_FIELDS = [
    "interaction_id", "user_id", "product_id", "action",
    "category", "duration_sec", "weight", "timestamp",
]
ORDER_FIELDS = [
    "order_id", "user_id", "product_id", "product_name",
    "quantity", "unit_price", "line_total", "order_total",
    "payment_method", "shipping_name", "shipping_city",
    "status", "created_at",
]
PRODUCT_FIELDS = [
    "product_id", "name", "category", "price",
    "stock", "rating", "views", "purchases",
]


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


# ── Constructores de fila (compartidos por export y append) ────
def _interaction_row(doc: dict) -> dict:
    ts = doc.get("timestamp")
    return {
        "interaction_id": str(doc.get("_id", "")),
        "user_id": doc.get("user_id", ""),
        "product_id": doc.get("product_id", ""),
        "action": doc.get("action", ""),
        "category": doc.get("category", ""),
        "duration_sec": doc.get("duration", 0),
        "weight": doc.get("weight", 1),
        "timestamp": ts.isoformat() if ts else "",
    }


def _order_item_rows(order: dict) -> list:
    shipping = order.get("shipping") or {}
    items = order.get("items") or []
    order_total = order.get("total", 0)
    created = order.get("created_at")
    created_str = created.isoformat() if created else ""
    rows = []
    for item in items:
        qty = item.get("quantity", 1)
        price = item.get("price", 0)
        rows.append({
            "order_id": str(order.get("_id", "")),
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
    return rows


def _product_row(p: dict) -> dict:
    return {
        "product_id": str(p.get("_id", "")),
        "name": p.get("name", ""),
        "category": p.get("category", ""),
        "price": p.get("price", 0),
        "stock": p.get("stock", 0),
        "rating": p.get("rating", 0),
        "views": p.get("views", 0),
        "purchases": p.get("purchases", 0),
    }


def _append_rows(path: str, fieldnames: list, rows: list):
    """Agrega filas al CSV; escribe el encabezado si el archivo está vacío.
    Nunca lanza excepción hacia arriba para no romper la petición web."""
    if not rows:
        return
    try:
        with _write_lock:
            _ensure_dir()
            nuevo = (not os.path.exists(path)) or os.path.getsize(path) == 0
            with open(path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if nuevo:
                    writer.writeheader()
                writer.writerows(rows)
    except Exception as e:
        print(f"[WARN] No se pudo agregar al CSV {path}: {e}")


# ── APPEND en tiempo real (se llaman desde la app) ─────────────
def append_interaction(doc: dict, path: str | None = None):
    """Agrega UNA interacción a interactions.csv en cuanto ocurre."""
    path = path or os.path.join(DATA_DIR, "interactions.csv")
    _append_rows(path, INTERACTION_FIELDS, [_interaction_row(doc)])


def append_order(order: dict, path: str | None = None):
    """Agrega las filas (una por ítem) de una orden a orders.csv al comprar."""
    path = path or os.path.join(DATA_DIR, "orders.csv")
    _append_rows(path, ORDER_FIELDS, _order_item_rows(order))


# ── EXPORT completo (regenera desde MongoDB) ───────────────────
def export_interactions(db, path: str | None = None) -> tuple:
    path = path or os.path.join(DATA_DIR, "interactions.csv")
    _ensure_dir()
    count = 0
    with _write_lock, open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INTERACTION_FIELDS)
        writer.writeheader()
        for doc in db.interactions.find().sort("timestamp", 1):
            writer.writerow(_interaction_row(doc))
            count += 1
    return path, count


def export_orders(db, path: str | None = None) -> tuple:
    path = path or os.path.join(DATA_DIR, "orders.csv")
    _ensure_dir()
    count = 0
    with _write_lock, open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ORDER_FIELDS)
        writer.writeheader()
        for order in db.orders.find().sort("created_at", 1):
            rows = _order_item_rows(order)
            writer.writerows(rows)
            count += len(rows)
    return path, count


def export_products(db, path: str | None = None) -> tuple:
    path = path or os.path.join(DATA_DIR, "products.csv")
    _ensure_dir()
    count = 0
    with _write_lock, open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PRODUCT_FIELDS)
        writer.writeheader()
        for p in db.products.find():
            writer.writerow(_product_row(p))
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
