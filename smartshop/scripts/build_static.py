# =============================================================
#  scripts/build_static.py — Genera el frontend ESTÁTICO para Netlify
#
#  Renderiza las plantillas Jinja (que NO dependen del contexto Flask)
#  a HTML plano y copia la carpeta static/. El resultado va en
#  ../netlify_dist y es lo que se publica en Netlify.
#
#  Las llamadas a /api/* las reenvía Netlify por proxy al backend
#  (ver netlify.toml); el SSE va directo al backend vía BACKEND_URL.
#
#  Uso:
#    python scripts/build_static.py https://vibe-backend.onrender.com
#    (o define la variable de entorno BACKEND_URL)
# =============================================================
import os
import sys
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(BASE, "templates")
STATIC = os.path.join(BASE, "static")
OUT = os.path.join(BASE, "netlify_dist")

# Ruta pública (Netlify)  ->  plantilla Jinja
PAGES = {
    "index.html":                  "index.html",
    "login.html":                  "login.html",
    "register.html":               "register.html",
    "product.html":                "product.html",   # /product/* hace rewrite aquí
    "cart.html":                   "cart.html",
    "checkout.html":               "checkout.html",
    "order-success.html":          "order_success.html",
    "search.html":                 "search.html",
    "cuenta.html":                 "cuenta.html",
    "ml-lab.html":                 "ml_lab.html",
    "politica-envios.html":        "politica_envios.html",
    "politica-devoluciones.html":  "politica_devoluciones.html",
    "metodos-pago.html":           "metodos_pago.html",
}


def main():
    backend_url = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("BACKEND_URL", "")).rstrip("/")
    if not backend_url:
        print("AVISO: sin BACKEND_URL -> el sitio llamará al mismo origen "
              "(funciona solo si Netlify proxea /api correctamente).")

    env = Environment(loader=FileSystemLoader(TEMPLATES),
                      autoescape=select_autoescape(["html"]))

    # Reiniciar carpeta de salida
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    # 1) Renderizar páginas
    for out_name, template_name in PAGES.items():
        html = env.get_template(template_name).render(
            product_id="",            # se lee de la URL en el cliente
            backend_url=backend_url,
        )
        with open(os.path.join(OUT, out_name), "w", encoding="utf-8") as f:
            f.write(html)
    print(f"[OK] {len(PAGES)} páginas renderizadas -> {OUT}")

    # 2) Copiar assets estáticos (css, js, imágenes incl. los .webp locales)
    shutil.copytree(STATIC, os.path.join(OUT, "static"))
    n_webp = len([x for x in os.listdir(os.path.join(STATIC, "images", "products"))
                  if x.endswith(".webp")])
    print(f"[OK] static/ copiado ({n_webp} imágenes webp de producto)")
    print(f"\nListo. Publica la carpeta: {OUT}")
    print(f"BACKEND_URL usado: {backend_url or '(vacío)'}")


if __name__ == "__main__":
    main()
