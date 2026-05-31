from pymongo import MongoClient
from config import Config

# Cliente global (se reutiliza en toda la app)
client = None
db     = None

def init_db():
    """Inicializa la conexión a MongoDB y devuelve la base de datos."""
    global client, db
    client = MongoClient(Config.MONGO_URI)
    db     = client[Config.DB_NAME]

    # Crear índices para búsqueda eficiente
    db.products.create_index([("name", "text"), ("description", "text")])
    db.products.create_index("category")
    db.interactions.create_index("user_id")
    db.interactions.create_index("product_id")

    print(f"[OK] MongoDB conectado -> base de datos: {Config.DB_NAME}")
    return db

def get_db():
    """Retorna la instancia de la base de datos (singleton)."""
    global db
    if db is None:
        init_db()
    return db
