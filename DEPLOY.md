# 🚀 Despliegue de Vibe (Netlify + Render + MongoDB Atlas)

Vibe es un **servidor Flask con tiempo real (SSE)**, así que no puede vivir
entero en Netlify (Netlify no corre Python ni conexiones persistentes).
La arquitectura es **híbrida**:

```
   Netlify (frontend estático)            Render (backend Flask + SSE)
   ├─ HTML / CSS / JS / imágenes          ├─ API REST  (/api/*)
   └─ llama al backend por ──────────────►├─ SSE tiempo real (/api/stream/*)
      window.BACKEND_URL                   └─ MongoDB Atlas (base de datos)
```

Todo lo necesario ya está en el repo (`render.yaml`, `netlify.toml`,
`scripts/build_static.py`). Solo hay que crear 3 cuentas gratis y conectar las
piezas. Tiempo aproximado: **20-30 min**.

---

## 1) Base de datos — MongoDB Atlas (gratis)

1. Crea cuenta en https://www.mongodb.com/cloud/atlas y un clúster **M0 (free)**.
2. **Database Access** → crea un usuario con contraseña (anota ambos).
3. **Network Access** → *Add IP* → **`0.0.0.0/0`** (permitir desde cualquier lado;
   Render no tiene IP fija en el plan free).
4. **Connect → Drivers** → copia la cadena, queda así:
   ```
   mongodb+srv://USUARIO:PASSWORD@cluster0.xxxx.mongodb.net/smartshop?retryWrites=true&w=majority
   ```
   ⚠️ Agrega `/smartshop` antes del `?` para usar nuestra base.

### Poblar Atlas con los datos (desde tu compu, una sola vez)
```bash
cd smartshop
# Linux/Mac:
MONGO_URI="<tu-cadena-de-atlas>" venv/bin/python ml/seed_data.py
# Windows (PowerShell):
$env:MONGO_URI="<tu-cadena-de-atlas>"; venv\Scripts\python ml/seed_data.py
```
Esto crea productos (con `image_local`), usuarios e interacciones en Atlas.

---

## 2) Backend — Render (gratis)

1. Crea cuenta en https://render.com y conéctala a tu GitHub.
2. **New → Blueprint** → elige el repo `Viancajh/Vibe`. Render detecta
   `render.yaml` y crea el servicio **vibe-backend** automáticamente.
3. En **Environment**, completa las variables marcadas como "pega aquí":
   - `MONGO_URI` → tu cadena de Atlas (con `/smartshop`).
   - `CORS_ORIGINS` → de momento déjalo en blanco o pon `*`; lo ajustas en el paso 4.
   - (`SECRET_KEY` y `JWT_SECRET_KEY` se generan solas.)
4. **Create** y espera el build (~3-5 min). Al terminar tendrás una URL tipo:
   ```
   https://vibe-backend.onrender.com
   ```
   Pruébala: abre `https://vibe-backend.onrender.com/api/products/` → debe
   devolver JSON con productos.

> ⚠️ **Plan free de Render**: el servicio se "duerme" tras 15 min sin uso; la
> primera petición luego tarda ~30-60 s en despertar. Normal para demos.

---

## 3) Frontend — Netlify (gratis)

1. Crea cuenta en https://netlify.com y conéctala a GitHub.
2. **Add new site → Import an existing project** → elige `Viancajh/Vibe`.
   Netlify lee `netlify.toml` (base `smartshop`, build con Jinja, publica
   `netlify_dist`). No cambies nada de eso.
3. **Site settings → Environment variables** → agrega:
   ```
   BACKEND_URL = https://vibe-backend.onrender.com   (tu URL real de Render)
   ```
4. **Deploys → Trigger deploy** (para que tome la variable). Tendrás una URL tipo:
   ```
   https://vibe-tienda.netlify.app
   ```

---

## 4) Conectar las piezas (CORS)

En **Render → vibe-backend → Environment**, pon tu URL de Netlify en:
```
CORS_ORIGINS = https://vibe-tienda.netlify.app
```
Guarda (Render redepliega solo). Esto permite que el frontend de Netlify llame
al backend y reciba el SSE.

---

## ✅ Verificación

1. Abre tu sitio Netlify. Deben cargar productos e imágenes.
2. Entra a un producto → debe verse el **banner en vivo** y "Tú estás viendo
   esto ahora". Abre el mismo producto en 2 pestañas → "2 personas viendo".
3. Regístrate / inicia sesión → agrega al carrito → checkout.

Si algo falla, abre la consola del navegador (F12). Errores de **CORS** =
revisa el paso 4. Errores **502/timeout** al primer intento = Render despertando.

---

## 🔁 Cada vez que hagan cambios
- **Backend** (Python): `git push` → Render redepliega solo.
- **Frontend** (HTML/CSS/JS): `git push` → Netlify rebuild solo.
- **Datos** (Atlas): corre el seed/migración apuntando `MONGO_URI` a Atlas.

## 🛠️ Probar el build estático en local
```bash
cd smartshop
venv/bin/python scripts/build_static.py https://vibe-backend.onrender.com
# Sirve la carpeta generada:
cd netlify_dist && python -m http.server 8888
# Abre http://localhost:8888
```
