# =============================================================
#  routes/stream.py — Endpoints SSE (Server-Sent Events)
#
#  Canales:
#   GET /api/stream/global          → cambios de cualquier producto
#                                      (para catálogo / página principal)
#   GET /api/stream/product/<id>    → cambios de un producto +
#                                      conteo de espectadores en vivo
#
#  El navegador se conecta con EventSource (HTTP, sin librerías).
# =============================================================
import json
import queue

from flask import Blueprint, Response, stream_with_context

from database.mongodb import get_db
from realtime import broker, product_snapshot

stream_bp = Blueprint("stream", __name__, url_prefix="/api/stream")

# Cada cuánto mandar un "ping" para mantener viva la conexión (segundos).
# Es corto a propósito: el servidor de desarrollo solo detecta que un cliente
# cerró la ventana cuando intenta escribir (el ping) y la conexión falla. Con un
# valor bajo, el descuento de espectadores (viewer_leave) se difunde casi al
# instante a los demás clientes en vez de tardar hasta KEEPALIVE segundos.
KEEPALIVE = 2


def _sse(data: str, event: str = "update") -> str:
    """Formatea un mensaje en el protocolo SSE."""
    return f"event: {event}\ndata: {data}\n\n"


@stream_bp.route("/global", methods=["GET"])
def stream_global():
    """Stream de actualizaciones de TODOS los productos."""
    q = broker.subscribe(["global"])

    @stream_with_context
    def gen():
        try:
            yield _sse(json.dumps({"ok": True}), event="ready")
            while True:
                try:
                    data = q.get(timeout=KEEPALIVE)
                    yield _sse(data)
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            broker.unsubscribe(["global"], q)

    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@stream_bp.route("/product/<product_id>", methods=["GET"])
def stream_product(product_id):
    """Stream de un producto: vistas, stock, vendidos y espectadores en vivo."""
    topic = f"product:{product_id}"
    q = broker.subscribe([topic])

    @stream_with_context
    def gen():
        db = get_db()
        # Al entrar: contamos un espectador y avisamos a todos
        broker.viewer_join(product_id)
        snap = product_snapshot(db, product_id)
        try:
            yield _sse(json.dumps({"ok": True}), event="ready")
            if snap:
                yield _sse(json.dumps(snap))      # estado inicial inmediato
                broker.publish(topic, json.dumps(snap))  # nuevos viewers para el resto
            while True:
                try:
                    data = q.get(timeout=KEEPALIVE)
                    yield _sse(data)
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            broker.unsubscribe([topic], q)
            # Al salir: descontamos espectador y avisamos al resto
            broker.viewer_leave(product_id)
            final = product_snapshot(db, product_id)
            if final:
                broker.publish(topic, json.dumps(final))
                broker.publish("global", json.dumps(final))

    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
