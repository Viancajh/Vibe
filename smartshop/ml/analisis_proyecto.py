# =============================================================
#  ml/analisis_proyecto.py — Lista de cotejo (Aprendizaje Automatizado)
#
#  Ejecutar:  python ml/analisis_proyecto.py
#  Antes:     python ml/seed_data.py
#
#  Cubre los 8 puntos de ML de la lista de cotejo:
#    1. Analisis exploratorio y estadistico (5 tipos)
#    2. Visualizacion con matplotlib (5 graficas)
#    3. Preprocesamiento (estandarizacion, normalizacion, PCA)
#    4. No supervisado: KMeans
#    5. Clasificacion supervisada (cluster del usuario)
#    6. Regresion supervisada (precio del producto)
#    7. Red neuronal artificial (regresion de precio)
#    8. Metricas de desempeno (supervisado + no supervisado)
# =============================================================
import json
import os
import pickle
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from bson import ObjectId
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    silhouette_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler, StandardScaler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongodb import init_db
from ml.features import CATEGORIAS, FEATURE_COLUMNS, fila_para_random_forest, vector_usuario_por_categoria

ML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
GRAF_DIR = os.path.join(os.path.dirname(ML_DIR), "static", "images", "ml")
METRICAS_PATH = os.path.join(ML_DIR, "proyecto_metricas.json")

VARS_EDA = ["n_views", "n_clicks", "n_cart", "avg_duration", "price_norm", "rating"]
REG_FEATURES = ["rating", "views", "purchases", "stock"]


# ── Dataset ──────────────────────────────────────────────────

def cargar_datos_interacciones(db):
    """Dataset usuario-producto (clasificacion: purchased)."""
    interacciones = list(db.interactions.find())
    productos = {str(p["_id"]): p for p in db.products.find()}
    por_par = {}
    for i in interacciones:
        uid, pid = i["user_id"], i.get("product_id")
        if not pid:
            continue
        por_par.setdefault((uid, pid), []).append(i)

    filas = []
    for (uid, pid), lista in por_par.items():
        prod = productos.get(pid)
        if not prod:
            continue
        fila = fila_para_random_forest(lista, prod)
        fila["user_id"] = uid
        filas.append(fila)
    return pd.DataFrame(filas)


def cargar_datos_productos(db):
    """Dataset de productos (regresion: predecir price)."""
    filas = []
    for p in db.products.find():
        filas.append({
            "rating": p.get("rating", 3.0),
            "views": p.get("views", 0),
            "purchases": p.get("purchases", 0),
            "stock": p.get("stock", 0),
            "price": p.get("price", 0),
        })
    return pd.DataFrame(filas)


def vectores_usuarios(db, df_inter):
    productos = {str(p["_id"]): p for p in db.products.find()}
    usuarios = df_inter["user_id"].unique()
    datos = {}
    for uid in usuarios:
        ints = list(db.interactions.find({"user_id": uid}))
        datos[uid] = vector_usuario_por_categoria(ints, productos)
    return datos


# ── 1 y 2: Analisis estadistico + 5 graficas ───────────────

def analisis_estadistico(df, metricas):
    print("\n[1] ANALISIS EXPLORATORIO Y ESTADISTICO")

    # 1) Normalidad (Shapiro-Wilk sobre rating)
    col_norm = "rating"
    muestra = df[col_norm].dropna()
    if len(muestra) >= 3:
        stat, p_val = stats.shapiro(muestra[:5000])
        metricas["normalidad"] = {
            "variable": col_norm,
            "test": "Shapiro-Wilk",
            "estadistico": round(float(stat), 4),
            "p_valor": round(float(p_val), 4),
            "interpretacion": "Datos normales (p>0.05)" if p_val > 0.05 else "No se cumple normalidad (p<=0.05)",
        }
        print(f"    Normalidad ({col_norm}): p={p_val:.4f}")

    # 2) Descriptivos
    desc = df[VARS_EDA].describe().round(3)
    metricas["descriptivos"] = desc.to_dict()
    print("    Descriptivos: media, std, min, max calculados")

    # 3) Outliers (IQR en price_norm)
    q1, q3 = df["price_norm"].quantile(0.25), df["price_norm"].quantile(0.75)
    iqr = q3 - q1
    lim_inf, lim_sup = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = df[(df["price_norm"] < lim_inf) | (df["price_norm"] > lim_sup)]
    metricas["outliers"] = {
        "variable": "price_norm",
        "metodo": "IQR (1.5)",
        "cantidad": int(len(outliers)),
        "limite_inferior": round(float(lim_inf), 3),
        "limite_superior": round(float(lim_sup), 3),
    }
    print(f"    Outliers (price_norm): {len(outliers)}")

    # 4) Correlacion
    corr = df[VARS_EDA + ["purchased"]].corr().round(3)
    metricas["correlacion"] = corr.to_dict()
    print("    Matriz de correlacion calculada")

    # 5) ANOVA: purchased (0 vs 1) vs n_cart
    g0 = df[df["purchased"] == 0]["n_cart"]
    g1 = df[df["purchased"] == 1]["n_cart"]
    if len(g0) > 1 and len(g1) > 1:
        f_stat, p_anova = stats.f_oneway(g0, g1)
        metricas["anova"] = {
            "variable_entrada": "n_cart",
            "variable_objetivo": "purchased",
            "f_estadistico": round(float(f_stat), 4),
            "p_valor": round(float(p_anova), 4),
            "interpretacion": "Hay diferencia entre grupos" if p_anova < 0.05 else "Sin diferencia significativa",
        }
        print(f"    ANOVA (n_cart vs purchased): p={p_anova:.4f}")

    return metricas


def generar_graficas(df, metricas):
    print("\n[2] VISUALIZACION (5 graficas matplotlib)")
    os.makedirs(GRAF_DIR, exist_ok=True)
    rutas = []

    # Grafica 1: Normalidad (histograma rating)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(df["rating"], bins=12, color="#2563eb", edgecolor="white", alpha=0.85)
    ax.set_title("1. Normalidad - Distribucion de rating")
    ax.set_xlabel("Rating")
    ax.set_ylabel("Frecuencia")
    p = metricas.get("normalidad", {}).get("p_valor", "")
    ax.text(0.02, 0.95, f"Shapiro p={p}", transform=ax.transAxes, fontsize=9)
    r1 = os.path.join(GRAF_DIR, "01_normalidad.png")
    fig.savefig(r1, dpi=120, bbox_inches="tight")
    plt.close(fig)
    rutas.append("01_normalidad.png")

    # Grafica 2: Descriptivos (medias)
    fig, ax = plt.subplots(figsize=(8, 4))
    medias = df[VARS_EDA].mean()
    ax.bar(medias.index, medias.values, color="#7c3aed")
    ax.set_title("2. Analisis descriptivo - Medias de variables")
    ax.tick_params(axis="x", rotation=30)
    r2 = os.path.join(GRAF_DIR, "02_descriptivos.png")
    fig.savefig(r2, dpi=120, bbox_inches="tight")
    plt.close(fig)
    rutas.append("02_descriptivos.png")

    # Grafica 3: Outliers (boxplot price_norm)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.boxplot(df["price_norm"].dropna(), vert=True)
    ax.set_title("3. Deteccion de outliers (price_norm)")
    ax.set_ylabel("price_norm")
    r3 = os.path.join(GRAF_DIR, "03_outliers.png")
    fig.savefig(r3, dpi=120, bbox_inches="tight")
    plt.close(fig)
    rutas.append("03_outliers.png")

    # Grafica 4: Correlacion (heatmap)
    fig, ax = plt.subplots(figsize=(7, 5))
    c = df[VARS_EDA + ["purchased"]].corr()
    im = ax.imshow(c.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(c.columns)))
    ax.set_yticks(range(len(c.columns)))
    ax.set_xticklabels(c.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(c.columns, fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046)
    ax.set_title("4. Correlacion entre variables")
    r4 = os.path.join(GRAF_DIR, "04_correlacion.png")
    fig.savefig(r4, dpi=120, bbox_inches="tight")
    plt.close(fig)
    rutas.append("04_correlacion.png")

    # Grafica 5: ANOVA (n_cart por purchased)
    fig, ax = plt.subplots(figsize=(6, 4))
    df.boxplot(column="n_cart", by="purchased", ax=ax)
    ax.set_title("5. ANOVA - n_cart segun compro (0/1)")
    ax.set_xlabel("Purchased")
    fig.suptitle("")
    r5 = os.path.join(GRAF_DIR, "05_anova.png")
    fig.savefig(r5, dpi=120, bbox_inches="tight")
    plt.close(fig)
    rutas.append("05_anova.png")

    metricas["graficas"] = rutas
    for g in rutas:
        print(f"    -> static/images/ml/{g}")
    return metricas


# ── 3: Preprocesamiento + PCA ────────────────────────────────

def preprocesamiento_pca(df, metricas):
    print("\n[3] PREPROCESAMIENTO (estandarizacion, normalizacion, PCA)")

    X = df[VARS_EDA].values
    scaler_std = StandardScaler()
    scaler_mm = MinMaxScaler()
    X_std = scaler_std.fit_transform(X)
    X_mm = scaler_mm.fit_transform(X)

    pca = PCA(n_components=min(3, X.shape[1]))
    X_pca = pca.fit_transform(X_std)
    var_explicada = pca.explained_variance_ratio_

    metricas["preprocesamiento"] = {
        "estandarizacion": "StandardScaler (media=0, std=1)",
        "normalizacion": "MinMaxScaler (rango 0-1)",
        "pca_componentes": len(var_explicada),
        "varianza_explicada": [round(float(v), 4) for v in var_explicada],
        "varianza_total_pct": round(float(sum(var_explicada) * 100), 2),
    }
    print(f"    PCA: {sum(var_explicada)*100:.1f}% varianza en {len(var_explicada)} componentes")

    # Grafica PCA
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(range(1, len(var_explicada) + 1), var_explicada, color="#059669")
    axes[0].set_title("Varianza explicada por componente")
    axes[0].set_xlabel("Componente PCA")
    if X_pca.shape[1] >= 2:
        colores = df["purchased"].map({0: "#94a3b8", 1: "#2563eb"})
        axes[1].scatter(X_pca[:, 0], X_pca[:, 1], c=colores, alpha=0.7, s=40)
        axes[1].set_title("PCA - PC1 vs PC2 (color = purchased)")
        axes[1].set_xlabel("PC1")
        axes[1].set_ylabel("PC2")
    r = os.path.join(GRAF_DIR, "06_pca.png")
    fig.savefig(r, dpi=120, bbox_inches="tight")
    plt.close(fig)
    metricas["graficas"].append("06_pca.png")
    print("    -> static/images/ml/06_pca.png")

    return scaler_std, scaler_mm, pca, metricas


# ── 4: KMeans (no supervisado) ───────────────────────────────

def entrenar_kmeans(vectores, metricas):
    print("\n[4] NO SUPERVISADO - KMeans")

    ids = list(vectores.keys())
    X = np.array([vectores[u] for u in ids])
    scaler = StandardScaler()
    X_norm = scaler.fit_transform(X)

    k = min(4, max(2, len(ids)))
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_norm)

    sil = silhouette_score(X_norm, labels) if len(set(labels)) > 1 else 0.0
    clusters = {uid: int(l) for uid, l in zip(ids, labels)}

    metricas["no_supervisado"] = {
        "algoritmo": "KMeans",
        "n_clusters": k,
        "silhouette": round(float(sil), 4),
        "interpretacion_silhouette": "Cercano a 1 = clusters bien separados",
    }
    print(f"    Clusters: {k} | Silhouette: {sil:.3f}")

    # Grafica clusters (2 primeras categorias)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(X[:, 0], X[:, 1], c=labels, cmap="tab10", s=120, edgecolors="white")
    ax.set_xlabel(CATEGORIAS[0])
    ax.set_ylabel(CATEGORIAS[1])
    ax.set_title("KMeans - Clusters de usuarios")
    r = os.path.join(GRAF_DIR, "07_kmeans.png")
    fig.savefig(r, dpi=120, bbox_inches="tight")
    plt.close(fig)
    metricas["graficas"].append("07_kmeans.png")

    return kmeans, scaler, clusters, metricas


# ── 5: Clasificacion supervisada (predecir cluster) ──────────

def entrenar_clasificacion_cluster(vectores, clusters, metricas):
    print("\n[5] CLASIFICACION SUPERVISADA (predecir cluster del usuario)")

    X = np.array([vectores[uid] for uid in clusters])
    y = np.array([clusters[uid] for uid in clusters])

    if len(set(y)) < 2:
        print("    Muy pocos clusters para clasificar.")
        return None, None, metricas

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42
        )
    clf = RandomForestClassifier(n_estimators=80, random_state=42)
    clf.fit(X_train, y_train)
    pred = clf.predict(X_test)
    acc = accuracy_score(y_test, pred)

    metricas["clasificacion"] = {
        "algoritmo": "RandomForestClassifier",
        "objetivo": "Predecir cluster (basado en KMeans)",
        "accuracy": round(float(acc), 4),
        "reporte": classification_report(y_test, pred, zero_division=0),
    }
    print(f"    Accuracy cluster: {acc:.1%}")

    scaler = StandardScaler()
    scaler.fit(X)
    return clf, scaler, metricas


# ── 6: Regresion supervisada ─────────────────────────────────

def entrenar_regresion(df_prod, metricas):
    print("\n[6] REGRESION SUPERVISADA (predecir precio del producto)")

    X = df_prod[REG_FEATURES].values
    y = df_prod["price"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    reg = LinearRegression()
    reg.fit(X_train_s, y_train)
    pred = reg.predict(X_test_s)

    metricas["regresion"] = {
        "algoritmo": "LinearRegression",
        "r2": round(float(r2_score(y_test, pred)), 4),
        "mae": round(float(mean_absolute_error(y_test, pred)), 2),
        "mse": round(float(mean_squared_error(y_test, pred)), 2),
        "rmse": round(float(np.sqrt(mean_squared_error(y_test, pred))), 2),
    }
    print(f"    R2={metricas['regresion']['r2']} | MAE=${metricas['regresion']['mae']}")

    return reg, scaler, metricas


# ── 7: Red neuronal (regresion) ──────────────────────────────

def entrenar_ann(df_prod, metricas):
    print("\n[7] RED NEURONAL ARTIFICIAL (MLPRegressor - precio)")

    X = df_prod[REG_FEATURES].values
    y = df_prod["price"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    ann = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=800, random_state=42)
    ann.fit(X_train_s, y_train)
    pred = ann.predict(X_test_s)

    metricas["ann"] = {
        "algoritmo": "MLPRegressor",
        "capas": "64, 32",
        "r2": round(float(r2_score(y_test, pred)), 4),
        "mae": round(float(mean_absolute_error(y_test, pred)), 2),
        "mse": round(float(mean_squared_error(y_test, pred)), 2),
    }
    print(f"    R2 ANN={metricas['ann']['r2']} | MAE=${metricas['ann']['mae']}")

    return ann, scaler, metricas


# ── Clasificacion compra (para la tienda) ────────────────────

def entrenar_compra(df):
    X = df[FEATURE_COLUMNS].values
    y = df["purchased"].values
    if y.sum() < 2:
        return None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    rf = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight="balanced", random_state=42)
    rf.fit(X_train, y_train)
    return rf


# ── Guardar todo ─────────────────────────────────────────────

def guardar_todo(kmeans, km_scaler, clusters, clf, clf_scaler, reg, reg_scaler, ann, ann_scaler, rf_compra, metricas):
    print("\n[8] METRICAS Y MODELOS GUARDADOS")

    with open(METRICAS_PATH, "w", encoding="utf-8") as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2)
    print(f"    -> {METRICAS_PATH}")

    if kmeans:
        with open(os.path.join(ML_DIR, "kmeans_model.pkl"), "wb") as f:
            pickle.dump({"model": kmeans, "user_clusters": clusters, "categorias": CATEGORIAS, "scaler": km_scaler}, f)

    if clf:
        with open(os.path.join(ML_DIR, "cluster_classifier.pkl"), "wb") as f:
            pickle.dump({"model": clf, "scaler": clf_scaler, "categorias": CATEGORIAS}, f)

    if reg:
        with open(os.path.join(ML_DIR, "regression_model.pkl"), "wb") as f:
            pickle.dump({"model": reg, "scaler": reg_scaler, "features": REG_FEATURES}, f)

    if ann:
        with open(os.path.join(ML_DIR, "ann_model.pkl"), "wb") as f:
            pickle.dump({"model": ann, "scaler": ann_scaler, "features": REG_FEATURES}, f)

    if rf_compra:
        with open(os.path.join(ML_DIR, "rf_model.pkl"), "wb") as f:
            pickle.dump({"model": rf_compra, "features": FEATURE_COLUMNS}, f)


def ejecutar():
    print("=" * 55)
    print("  Vibe - Analisis completo (lista de cotejo)")
    print("=" * 55)

    db = init_db()
    df = cargar_datos_interacciones(db)
    df_prod = cargar_datos_productos(db)

    if df.empty or df_prod.empty:
        print("Sin datos. Ejecuta: python ml/seed_data.py")
        sys.exit(1)

    metricas = {}
    metricas = analisis_estadistico(df, metricas)
    metricas = generar_graficas(df, metricas)
    _, _, _, metricas = preprocesamiento_pca(df, metricas)

    vectores = vectores_usuarios(db, df)
    kmeans, km_scaler, clusters, metricas = entrenar_kmeans(vectores, metricas)

    for uid, cl in clusters.items():
        try:
            db.users.update_one({"_id": ObjectId(uid)}, {"$set": {"cluster": cl}})
        except Exception:
            pass

    clf, clf_scaler, metricas = entrenar_clasificacion_cluster(vectores, clusters, metricas)
    reg, reg_scaler, metricas = entrenar_regresion(df_prod, metricas)
    ann, ann_scaler, metricas = entrenar_ann(df_prod, metricas)
    rf_compra = entrenar_compra(df)

    guardar_todo(kmeans, km_scaler, clusters, clf, clf_scaler, reg, reg_scaler, ann, ann_scaler, rf_compra, metricas)

    print("\n" + "=" * 55)
    print("  LISTA DE COTEJO - RESUMEN")
    print("=" * 55)
    print("  [x] Analisis estadistico (5 tipos)")
    print("  [x] 5+ graficas matplotlib")
    print("  [x] Estandarizacion, normalizacion, PCA")
    print("  [x] KMeans + metrica Silhouette")
    print("  [x] Clasificacion supervisada (cluster)")
    print("  [x] Regresion supervisada (precio)")
    print("  [x] Red neuronal (MLPRegressor)")
    print("  [x] Metricas supervisado y no supervisado")
    print("\n  Abre en la web: http://localhost:5000/ml-lab")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    ejecutar()
