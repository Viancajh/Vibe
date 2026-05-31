# =============================================================
#  scripts/download_images.py — Descarga y optimiza las imágenes
#  de producto para servirlas nosotros mismos (fallback local).
#
#  Qué hace:
#    1. Lee la lista PRODUCTS del seed.
#    2. Descarga cada imagen remota (con User-Agent de navegador para
#       esquivar el bloqueo de hotlinking de Amazon/MercadoLibre/etc.).
#    3. La redimensiona (máx. 800px de ancho) y la guarda como WebP
#       optimizado en static/images/products/<slug>.webp.
#
#  Ejecutar:  python scripts/download_images.py
# =============================================================
import os
import sys
import io
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image

from ml.seed_data import PRODUCTS
from utils.images import PRODUCTS_IMG_DIR, local_image_filename

MAX_WIDTH = 800          # ancho máximo (px) — suficiente para tarjetas y detalle
WEBP_QUALITY = 80        # 0-100; 80 es un buen balance calidad/peso
TIMEOUT = 25             # segundos por descarga

HEADERS = {
    # UA de navegador real: muchos hosts bloquean el UA por defecto de urllib
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "image/avif,image/webp,image/png,image/*,*/*;q=0.8",
    # Sin Referer a propósito: el hotlink-protection suele rechazar referers ajenos.
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def to_webp(raw: bytes) -> bytes:
    img = Image.open(io.BytesIO(raw))
    # WebP no admite modos raros (P, CMYK, etc.) -> normalizamos a RGB/RGBA
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.mode else "RGB")
    if img.width > MAX_WIDTH:
        ratio = MAX_WIDTH / img.width
        img = img.resize((MAX_WIDTH, int(img.height * ratio)), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="WEBP", quality=WEBP_QUALITY, method=6)
    return out.getvalue()


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(base, PRODUCTS_IMG_DIR)
    os.makedirs(out_dir, exist_ok=True)

    ok, fail, skip = 0, 0, 0
    failures = []
    for i, p in enumerate(PRODUCTS, 1):
        fname = local_image_filename(p["name"])
        dest = os.path.join(out_dir, fname)
        if os.path.exists(dest):
            skip += 1
            print(f"[{i:2}/{len(PRODUCTS)}] = ya existe  {fname}")
            continue
        try:
            raw = fetch(p["image"])
            webp = to_webp(raw)
            with open(dest, "wb") as f:
                f.write(webp)
            kb = len(webp) / 1024
            ok += 1
            print(f"[{i:2}/{len(PRODUCTS)}] OK {fname}  ({kb:.0f} KB)")
        except Exception as e:
            fail += 1
            failures.append((p["name"], str(e)[:80]))
            print(f"[{i:2}/{len(PRODUCTS)}] XX {p['name']}  -> {str(e)[:80]}")

    print(f"\nResumen: {ok} descargadas, {skip} ya existían, {fail} fallaron")
    if failures:
        print("Fallidas (quedan con fallback al placeholder):")
        for name, err in failures:
            print(f"   - {name}: {err}")


if __name__ == "__main__":
    main()
