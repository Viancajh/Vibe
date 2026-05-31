# =============================================================
#  app.py — Punto de entrada principal de Vibe
#  Ejecutar: python app.py
# =============================================================
import os

from flask import Flask, render_template, send_from_directory, redirect
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from config import Config
from database.mongodb import init_db

# ── Blueprints (módulos de rutas) ─────────────────────────────
from routes.auth            import auth_bp
from routes.products        import products_bp
from routes.cart            import cart_bp
from routes.interactions    import interactions_bp
from routes.recommendations import recommendations_bp
from routes.dataset           import dataset_bp
from routes.ml_lab            import ml_lab_bp
from routes.account           import account_bp
from routes.stream            import stream_bp

# ── Crear app ─────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)

# ── Extensiones ───────────────────────────────────────────────
jwt  = JWTManager(app)

# CORS: en local permite todo; en producción (Netlify) se restringe al
# dominio del frontend con la variable de entorno CORS_ORIGINS
# (separa varios con comas). Necesario porque el SSE va directo al backend.
_cors_env = os.getenv("CORS_ORIGINS", "*").strip()
_origins = "*" if _cors_env == "*" else [o.strip() for o in _cors_env.split(",") if o.strip()]
CORS(app, resources={r"/api/*": {"origins": _origins}}, supports_credentials=True)

# ── Registrar blueprints ──────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(products_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(interactions_bp)
app.register_blueprint(recommendations_bp)
app.register_blueprint(dataset_bp)
app.register_blueprint(ml_lab_bp)
app.register_blueprint(account_bp)
app.register_blueprint(stream_bp)

# ── Rutas de páginas HTML ─────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/product/<product_id>")
def product_page(product_id):
    return render_template("product.html", product_id=product_id)

@app.route("/cart")
def cart_page():
    return render_template("cart.html")

@app.route("/checkout")
def checkout_page():
    return render_template("checkout.html")

@app.route("/order-success")
def order_success_page():
    return render_template("order_success.html")

@app.route("/search")
def search_page():
    return render_template("search.html")

@app.route("/profile")
@app.route("/perfil")
def profile_page():
    return redirect("/cuenta#perfil")

@app.route("/cuenta")
def cuenta_page():
    return render_template("cuenta.html")

@app.route("/ml-lab")
def ml_lab_page():
    return render_template("ml_lab.html")

@app.route("/politica-envios")
def politica_envios():
    return render_template("politica_envios.html")

@app.route("/politica-devoluciones")
def politica_devoluciones():
    return render_template("politica_devoluciones.html")

@app.route("/metodos-pago")
def metodos_pago():
    return render_template("metodos_pago.html")

# ── Inicialización ────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print(" Vibe corriendo en http://localhost:5000")
    # threaded=True es necesario para SSE: cada cliente mantiene una
    # conexión abierta y no debe bloquear al resto de peticiones.
    app.run(debug=Config.DEBUG, port=5000, threaded=True)
