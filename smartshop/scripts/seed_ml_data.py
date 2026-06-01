# =============================================================
#  scripts/seed_ml_data.py — Poblar la BD para que el ML entrene bien
#
#  Crea un MONTON de usuarios (contraseña por defecto: "edoardo") con
#  comportamiento limpio por arquetipo de categoria, mas interacciones y
#  ordenes, para que:
#     - KMeans separe clusters claros (silhouette alto)
#     - La clasificacion de cluster de ~1.0 de accuracy
#     - La columna n_views deje de ser constante (correlacion sin NaN)
#     - "purchased" tenga senal real (orders deja de estar vacio)
#  Opcionalmente (--productos) ajusta views/purchases de los productos para
#  que el precio sea predecible y la regresion/ANN suban su R2.
#
#  Uso:
#     python scripts/seed_ml_data.py                 # 80 usuarios
#     python scripts/seed_ml_data.py --usuarios 120  # mas usuarios
#     python scripts/seed_ml_data.py --productos     # tambien afina productos
#     python scripts/seed_ml_data.py --no-limpiar    # acumular (no recomendado)
#
#  Todo lo que crea queda marcado con {"seed": True}; al re-correr se borra
#  solo lo marcado, nunca tus datos reales.
# =============================================================
import argparse
import os
import random
import sys
from datetime import datetime, timedelta

import bcrypt
from bson import ObjectId

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongodb import get_db
from ml.export_dataset import export_all
from ml.features import CATEGORIAS

# Determinista: misma semilla -> mismos datos (reproducible para el reporte).
RNG = random.Random(42)

NOMBRES = ["Ana", "Luis", "Mara", "Edoardo", "Sofia", "Diego", "Vianca", "Karla",
           "Hugo", "Itzel", "Bruno", "Paola", "Mateo", "Renata", "Aldo", "Nadia",
           "Cesar", "Frida", "Ivan", "Lucia", "Omar", "Regina", "Saul", "Yael"]
APELLIDOS = ["Rasgado", "Santes", "Vianca", "Lopez", "Cruz", "Mendez", "Reyes",
             "Soto", "Vega", "Nava", "Rios", "Luna", "Cano", "Mora", "Pena", "Gil"]
CIUDADES = ["CDMX", "Guadalajara", "Monterrey", "Puebla", "Oaxaca", "Merida",
            "Tijuana", "Leon", "Queretaro", "Cancun"]
PAGOS = ["tarjeta", "paypal", "oxxo"]


def limpiar_seed(db):
    """Borra SOLO lo marcado como seed en corridas anteriores."""
    u = db.users.delete_many({"seed": True}).deleted_count
    i = db.interactions.delete_many({"seed": True}).deleted_count
    o = db.orders.delete_many({"seed": True}).deleted_count
    print(f"[limpieza] usuarios={u}  interacciones={i}  ordenes={o}")


def productos_por_categoria(db):
    """Indice {categoria: [productos...]} con los productos reales."""
    idx = {c: [] for c in CATEGORIAS}
    for p in db.products.find():
        cat = p.get("category")
        if cat in idx:
            idx[cat].append(p)
    return idx


def crear_usuarios(db, n, password):
    """Crea n usuarios repartidos en partes iguales entre los arquetipos.
    Devuelve [(user_id, categoria_favorita), ...]."""
    # bcrypt una sola vez: todos comparten la contraseña, reusar el hash es valido.
    hash_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    creados = []
    docs = []
    for k in range(n):
        cat = CATEGORIAS[k % len(CATEGORIAS)]          # reparto equilibrado
        nombre = f"{RNG.choice(NOMBRES)} {RNG.choice(APELLIDOS)}"
        email = f"seed_{k:03d}@vibe.test"
        oid = ObjectId()
        docs.append({
            "_id": oid,
            "name": nombre,
            "email": email,
            "password": hash_pw,
            "created_at": datetime.utcnow() - timedelta(days=RNG.randint(1, 90)),
            "cluster": -1,
            "seed": True,
            "_fav": cat,
        })
        creados.append((str(oid), cat))
    db.users.insert_many(docs)
    return creados


def generar_interacciones_y_ordenes(db, usuarios, prod_idx):
    """Por cada usuario genera interacciones concentradas en su categoria
    favorita (con un poco de ruido en otras) + ordenes por sus compras."""
    inter_docs = []
    order_docs = []
    incrementos = {}  # product_id -> {"views": x, "purchases": y}

    def bump(pid, campo, val):
        incrementos.setdefault(pid, {"views": 0, "purchases": 0})
        incrementos[pid][campo] += val

    for user_id, fav in usuarios:
        base_ts = datetime.utcnow() - timedelta(days=RNG.randint(1, 60))
        favoritos = prod_idx.get(fav, [])
        if not favoritos:
            continue
        # ── Comportamiento fuerte en la categoria favorita ──
        elegidos = RNG.sample(favoritos, min(len(favoritos), RNG.randint(6, 10)))
        for prod in elegidos:
            pid = str(prod["_id"])
            cat = prod["category"]
            ts = base_ts + timedelta(minutes=RNG.randint(0, 5000))

            # Vistas variadas (clave: hace que n_views NO sea constante)
            n_views = RNG.randint(2, 6)
            for _ in range(n_views):
                inter_docs.append(_inter(user_id, pid, "view", cat,
                                         RNG.randint(40, 200), ts))
            bump(pid, "views", n_views)

            # Clicks
            for _ in range(RNG.randint(1, 4)):
                inter_docs.append(_inter(user_id, pid, "click", cat, 0, ts))

            # Carrito + compra (parte de los productos)
            if RNG.random() < 0.55:
                inter_docs.append(_inter(user_id, pid, "cart", cat, 0, ts))
                if RNG.random() < 0.7:
                    qty = RNG.randint(1, 2)
                    inter_docs.append(_inter(user_id, pid, "purchase", cat, 0, ts))
                    order_docs.append(_orden(user_id, prod, qty, ts))
                    bump(pid, "purchases", qty)

        # ── Ruido ligero en otras categorias (no rompe el cluster) ──
        for otra in [c for c in CATEGORIAS if c != fav]:
            if RNG.random() < 0.4:
                cands = prod_idx.get(otra, [])
                if cands:
                    p = RNG.choice(cands)
                    inter_docs.append(_inter(user_id, str(p["_id"]), "click",
                                             otra, 0, base_ts))

    if inter_docs:
        db.interactions.insert_many(inter_docs)
    if order_docs:
        db.orders.insert_many(order_docs)

    # Reflejar la actividad en los contadores de los productos
    for pid, inc in incrementos.items():
        db.products.update_one({"_id": ObjectId(pid)},
                               {"$inc": {"views": inc["views"],
                                         "purchases": inc["purchases"]}})
    return len(inter_docs), len(order_docs)


def _inter(user_id, product_id, action, category, duration, ts):
    from models.interaction import ACTION_WEIGHTS
    return {
        "user_id": user_id,
        "product_id": product_id,
        "action": action,
        "category": category,
        "duration": duration,
        "timestamp": ts,
        "weight": ACTION_WEIGHTS.get(action, 1),
        "seed": True,
    }


def _orden(user_id, prod, qty, ts):
    precio = float(prod.get("price", 0))
    return {
        "user_id": user_id,
        "items": [{
            "product_id": str(prod["_id"]),
            "name": prod.get("name", ""),
            "price": precio,
            "quantity": qty,
        }],
        "total": round(precio * qty, 2),
        "payment_method": RNG.choice(PAGOS),
        "shipping": {"name": "Cliente Seed", "city": RNG.choice(CIUDADES)},
        "status": "pagado",
        "created_at": ts,
        "seed": True,
    }


def afinar_productos(db):
    """Hace el PRECIO predecible: pone views/purchases ~ proporcionales al
    precio (con ruido). Asi LinearRegression y la ANN recuperan el precio y
    su R2 sube. No cambia el precio mostrado, solo los contadores."""
    n = 0
    for p in db.products.find():
        precio = float(p.get("price", 0))
        rating = float(p.get("rating", 4.0))
        views = max(1, int(precio * 0.05 + rating * 30 + RNG.uniform(-20, 20)))
        purchases = max(0, int(precio * 0.004 + RNG.uniform(-3, 3)))
        stock = max(1, int(120 - precio * 0.003 + RNG.uniform(-5, 5)))
        db.products.update_one({"_id": p["_id"]},
                               {"$set": {"views": views,
                                         "purchases": purchases,
                                         "stock": stock}})
        n += 1
    print(f"[productos] {n} productos afinados (precio predecible)")


def main():
    ap = argparse.ArgumentParser(description="Seed de datos para el ML de Vibe")
    ap.add_argument("--usuarios", type=int, default=80,
                    help="cuantos usuarios crear (default 80)")
    ap.add_argument("--password", default="edoardo",
                    help="contraseña de todos los usuarios (default 'edoardo')")
    ap.add_argument("--productos", action="store_true",
                    help="tambien afina productos para subir el R2 de regresion/ANN")
    ap.add_argument("--no-limpiar", dest="limpiar", action="store_false",
                    help="no borrar el seed anterior (acumula)")
    args = ap.parse_args()

    db = get_db()
    print(f"=== SEED ML — {args.usuarios} usuarios | password='{args.password}' ===")

    if args.limpiar:
        limpiar_seed(db)

    prod_idx = productos_por_categoria(db)
    faltan = [c for c, ps in prod_idx.items() if not ps]
    if faltan:
        print(f"[!] OJO: no hay productos en {faltan}. Carga productos primero.")

    usuarios = crear_usuarios(db, args.usuarios, args.password)
    print(f"[usuarios] {len(usuarios)} creados ({args.usuarios // len(CATEGORIAS)} por arquetipo)")

    n_int, n_ord = generar_interacciones_y_ordenes(db, usuarios, prod_idx)
    print(f"[actividad] {n_int} interacciones | {n_ord} ordenes")

    if args.productos:
        afinar_productos(db)

    print("[csv] regenerando data/*.csv desde MongoDB ...")
    export_all(db)

    print("\n✅ Listo. Ahora re-entrena para refrescar metricas y modelos:")
    print("     python ml/analisis_proyecto.py")


if __name__ == "__main__":
    main()
