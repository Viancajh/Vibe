# =============================================================
#  utils/images.py — Rutas locales de imágenes de producto
#
#  Una sola fuente de verdad para el "slug" de cada imagen, usada por:
#    - scripts/download_images.py  (nombra los archivos al descargar)
#    - ml/seed_data.py             (rellena image_local al poblar)
#    - migrations/001_add_image_local.py (actualiza la BD existente)
# =============================================================
import re
import unicodedata

# Carpeta física (relativa a smartshop/) y URL pública servida por Flask
PRODUCTS_IMG_DIR = "static/images/products"
PRODUCTS_IMG_URL = "/static/images/products"


def slugify(text: str) -> str:
    """'iPhone 15 Pro 256GB' -> 'iphone-15-pro-256gb' (ASCII, sin acentos)."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "producto"


def local_image_filename(name: str) -> str:
    """Nombre de archivo local (webp) para un producto."""
    return f"{slugify(name)}.webp"


def local_image_url(name: str) -> str:
    """URL pública del fallback local servido por nuestro propio servidor."""
    return f"{PRODUCTS_IMG_URL}/{local_image_filename(name)}"
