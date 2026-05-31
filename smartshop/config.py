# =============================================================
#  config.py — Configuración global del proyecto Vibe
#  Lee variables de entorno del archivo .env
# =============================================================
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── Seguridad ──────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "smartshop-secret-2024")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-smartshop")

    # ── MongoDB ────────────────────────────────────────────────
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/smartshop")
    DB_NAME   = "smartshop"

    # ── JWT ────────────────────────────────────────────────────
    from datetime import timedelta
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # ── Entorno ────────────────────────────────────────────────
    DEBUG = os.getenv("DEBUG", "True") == "True"
