# =============================================================
#  realtime.py — Broker de eventos en tiempo real (SSE)
#  Publica cambios de productos (vistas, stock, vendidos y
#  espectadores en vivo) a todos los clientes conectados.
#
#  No usa MongoDB Change Streams (no requiere replica set):
#  cada ruta que modifica un producto llama a publish_product()
#  y el broker reparte el evento a las colas suscritas.
# =============================================================
import json
import queue
import threading
from collections import defaultdict

from bson import ObjectId


class Broker:
    """Pub/sub en memoria por tópicos + conteo de espectadores en vivo."""

    def __init__(self):
        self._subs = defaultdict(set)     # tópico -> set[Queue]
        self._viewers = defaultdict(int)  # product_id -> nº de espectadores activos
        self._lock = threading.Lock()

    # ── Suscripción ───────────────────────────────────────────
    def subscribe(self, topics):
        q = queue.Queue(maxsize=100)
        with self._lock:
            for t in topics:
                self._subs[t].add(q)
        return q

    def unsubscribe(self, topics, q):
        with self._lock:
            for t in topics:
                self._subs[t].discard(q)
                if not self._subs[t]:
                    self._subs.pop(t, None)

    # ── Publicación ───────────────────────────────────────────
    def publish(self, topic, data):
        with self._lock:
            subs = list(self._subs.get(topic, ()))
        for q in subs:
            try:
                q.put_nowait(data)
            except queue.Full:
                pass  # cliente lento: descartamos en vez de bloquear

    # ── Espectadores en vivo ──────────────────────────────────
    def viewer_count(self, product_id):
        with self._lock:
            return self._viewers.get(product_id, 0)

    def viewer_join(self, product_id):
        with self._lock:
            self._viewers[product_id] += 1
            return self._viewers[product_id]

    def viewer_leave(self, product_id):
        with self._lock:
            n = self._viewers.get(product_id, 0) - 1
            if n <= 0:
                self._viewers.pop(product_id, None)
                return 0
            self._viewers[product_id] = n
            return n


# Instancia global compartida por toda la app
broker = Broker()


def product_snapshot(db, product_id):
    """Estado actual de un producto para enviar por SSE (o None)."""
    try:
        p = db.products.find_one(
            {"_id": ObjectId(product_id)},
            {"views": 1, "stock": 1, "purchases": 1},
        )
    except Exception:
        return None
    if not p:
        return None
    return {
        "product_id": product_id,
        "views": p.get("views", 0),
        "stock": p.get("stock", 0),
        "purchases": p.get("purchases", 0),
        "viewers": broker.viewer_count(product_id),
    }


def publish_product(db, product_id):
    """Difunde el estado actual del producto al canal global y al del producto."""
    snap = product_snapshot(db, product_id)
    if snap is None:
        return
    data = json.dumps(snap)
    broker.publish(f"product:{product_id}", data)
    broker.publish("global", data)
