# ⚡ SmartShop — Tienda Online Inteligente con Machine Learning

> **Proyecto universitario** | Flask + MongoDB + scikit-learn  
> Desarrollado en 1 semana por 4 estudiantes

---

## 📁 Estructura del proyecto

```
smartshop/
├── app.py                   ← Punto de entrada Flask (EJECUTAR ESTE)
├── config.py                ← Configuración global
├── requirements.txt         ← Dependencias Python

│
├── database/
│   └── mongodb.py           ← Conexión a MongoDB
│
├── models/                  ← Esquemas/documentos de MongoDB
│   ├── user.py              ← Modelo de usuario
│   ├── product.py           ← Modelo de producto
│   └── interaction.py       ← Modelo de interacciones (ML dataset)
│
├── routes/                  ← Endpoints de la API REST
│   ├── auth.py              ← /api/auth/register, /login, /me
│   ├── products.py          ← /api/products/
│   ├── cart.py              ← /api/cart/
│   ├── interactions.py      ← /api/interactions/track, /history
│   └── recommendations.py  ← /api/recommendations/
│
├── ml/
│   ├── seed_data.py         ← Poblar MongoDB con datos de ejemplo
│   ├── train_model.py       ← Entrenar RandomForest + KMeans
│   ├── rf_model.pkl         ← (generado al entrenar)
│   └── kmeans_model.pkl     ← (generado al entrenar)
│
├── static/
│   ├── css/styles.css       ← Estilos globales
│   ├── js/
│   │   ├── main.js          ← Funciones globales (auth, cart, toast)
│   │   └── tracker.js       ← Registro automático de interacciones
│   └── images/
│       └── placeholder.svg  ← Imagen de respaldo
│
└── templates/               ← Páginas HTML (Jinja2)
    ├── base.html            ← Navbar + Footer (base de todas)
    ├── index.html           ← Página principal con recomendaciones
    ├── login.html           ← Inicio de sesión
    ← register.html          ← Crear cuenta
    ├── product.html         ← Detalle de producto + predicción ML
    ├── cart.html            ← Carrito de compras
    ├── search.html          ← Resultados de búsqueda
    └── profile.html         ← Perfil + insights de ML
```

---

### Aprendizaje Supervisado (RandomForestClassifier)

**¿Qué hace?** Predice si un usuario *probablemente comprará* un producto.

**Características (features):**
| Feature | Descripción |
|---------|-------------|
| n_views | Cuántas veces vio el producto |
| n_clicks | Cuántas veces hizo click |
| n_cart | Si lo agregó al carrito |
| avg_duration | Tiempo promedio viendo el producto |
| price_norm | Precio normalizado (/1000) |
| rating | Calificación del producto |

**Etiqueta (target):** `1` si compró, `0` si no compró.

**¿Dónde se ve?** En la página de cada producto aparece una barra de probabilidad: "Alta probabilidad 🔥 (83%)"

### Aprendizaje No Supervisado (KMeans)

**¿Qué hace?** Agrupa usuarios con comportamientos similares.

**Vector de usuario:** Score acumulado por categoría:
```
[score_Tecnología, score_Gaming, score_Ropa, score_Hogar]
```

**Ejemplo:**
- Cluster 0: Usuarios de Tecnología + Gaming
- Cluster 1: Usuarios de Ropa + Hogar

**¿Dónde se ve?** Sección "Usuarios similares compraron" en la página principal.

---

## 📡 API Endpoints

### Autenticación
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /api/auth/register | Crear cuenta |
| POST | /api/auth/login | Iniciar sesión |
| GET  | /api/auth/me | Datos del usuario actual |

### Productos
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | /api/products/ | Listar productos |
| GET | /api/products/?category=Gaming | Filtrar por categoría |
| GET | /api/products/popular | Más vistos |
| GET | /api/products/search?q=laptop | Búsqueda |
| GET | /api/products/<id> | Detalle |

### Carrito
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET    | /api/cart/ | Ver carrito |
| POST   | /api/cart/add | Agregar producto |
| DELETE | /api/cart/remove/<id> | Eliminar producto |
| POST   | /api/cart/checkout | Confirmar compra |

### Interacciones
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /api/interactions/track | Registrar interacción |
| GET  | /api/interactions/history | Historial del usuario |
| GET  | /api/interactions/favorites | Categorías favoritas |
| GET  | /api/interactions/viewed | Productos vistos |

### Recomendaciones (requieren JWT)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | /api/recommendations/for-you | Personalizadas |
| GET | /api/recommendations/similar-users | KMeans |
| GET | /api/recommendations/purchase-probability/<id> | RandomForest |

---

## 👥 División de trabajo  

| Estudiante | Área |
|-----------|------|
| 1 | Backend: auth, productos, MongoDB (models + database) |
| 2 | Backend: carrito, interacciones, recomendaciones |
| 3 | Frontend: HTML + CSS (base, index, product, cart) |
| 4 | ML: seed_data.py, train_model.py + slides de exposición |

---

## 🔄 Re-entrenar el modelo con nuevos datos

Cada vez que haya más interacciones en MongoDB:

```bash
python ml/train_model.py
```

Flask usa los modelos `.pkl` que existen en disco. Si no existen, las rutas de recomendación devuelven los productos más populares como fallback.

---

## 🐛 Problemas comunes


## 📊 Colecciones en MongoDB

| Colección | Descripción |
|-----------|-------------|
| `users` | Usuarios registrados |
| `products` | Catálogo de productos |
| `interactions` | Dataset dinámico para ML |
| `carts` | Carritos activos |
| `orders` | Historial de compras |
