# =============================================================
#  migrations/001_add_image_local.py
#
#  Agrega el campo `image_local` (copia local servida por nosotros)
#  a los productos ya existentes en MongoDB, sin borrar nada.
#
#  Requisito previo: haber corrido `python scripts/download_images.py`
#  para que existan los .webp en static/images/products/.
#
#  Ejecutar:  python migrations/001_add_image_local.py
#  Idempotente: se puede correr varias veces sin efectos secundarios.
# =============================================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongodb import init_db
from utils.images import PRODUCTS_IMG_DIR, local_image_filename, local_image_url


def migrate():
    db = init_db()
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    img_dir = os.path.join(base, PRODUCTS_IMG_DIR)

    updated, missing = 0, []
    for prod in db.products.find({}, {"name": 1}):
        name = prod.get("name", "")
        fname = local_image_filename(name)
        if not os.path.exists(os.path.join(img_dir, fname)):
            # No bajamos esa imagen: no fijamos image_local (caerá al placeholder).
            missing.append(name)
            continue
        res = db.products.update_one(
            {"_id": prod["_id"]},
            {"$set": {"image_local": local_image_url(name)}},
        )
        if res.modified_count:
            updated += 1

    total = db.products.count_documents({})
    with_local = db.products.count_documents({"image_local": {"$exists": True}})
    print(f"[OK] image_local actualizado en {updated} productos "
          f"(con copia local: {with_local}/{total})")
    if missing:
        print(f"Sin archivo local ({len(missing)}) -> usan placeholder:")
        for n in missing:
            print(f"   - {n}")


if __name__ == "__main__":
    migrate()
