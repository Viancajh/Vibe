// =============================================================
//  tracker.js — Registro automático de interacciones
//
//  Este script se ejecuta en TODAS las páginas y registra:
//  - Clicks en productos
//  - Tiempo en páginas de producto
//  - Scroll (implica interés)
//
//  Toda interacción se envía a /api/interactions/track
//  El backend la guarda en MongoDB para alimentar el ML
// =============================================================

(function () {
    'use strict';

    // Solo rastrear si el usuario tiene sesión
    if (!localStorage.getItem('token')) return;

    /* ── Registro de click en cards de producto ─────────────── */
    document.addEventListener('click', function (e) {
        // Buscar la card de producto más cercana al elemento clickeado
        const card = e.target.closest('[data-product-id]');
        if (!card) return;

        const productId = card.dataset.productId;
        const category  = card.dataset.category || '';

        trackInteraction('click', category, productId);
    }, { passive: true });

    /* ── Tiempo de visualización (solo en /product/<id>) ─────── */
    // Esta función también está en product.html, aquí es respaldo
    if (window.location.pathname.startsWith('/product/')) {
        const startTime = Date.now();

        window.addEventListener('pagehide', () => {
            const duration = Math.round((Date.now() - startTime) / 1000);
            if (duration < 1) return;

            // Extraer product_id de la URL: /product/<id>
            const parts = window.location.pathname.split('/');
            const pid   = parts[parts.length - 1];
            if (!pid) return;

            // Usar sendBeacon para enviar aunque la página se cierre
            const payload = JSON.stringify({
                product_id : pid,
                action     : 'view',
                category   : '',
                duration
            });
            sendTrackBeacon(payload);
        });
    }

    /* ── Helper: enviar beacon con auth header ──────────────── */
    function sendTrackBeacon(payload) {
        // sendBeacon no permite headers, así que usamos fetch async
        const token = localStorage.getItem('token');
        fetch('/api/interactions/track', {
            method     : 'POST',
            headers    : {
                'Content-Type' : 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body       : payload,
            keepalive  : true   // permite que la petición sobreviva al cierre
        }).catch(() => {});     // silenciar errores
    }

})();

/* ── Función global accesible desde templates ─────────────── */
/**
 * Registra manualmente una interacción.
 * Llamado desde product.html y otros templates.
 */
function trackInteraction(action, category, productId) {
    const token = localStorage.getItem('token');
    if (!token) return;

    // Obtener product_id de la URL si no se pasa explícitamente
    if (!productId && window.location.pathname.startsWith('/product/')) {
        const parts = window.location.pathname.split('/');
        productId   = parts[parts.length - 1] || '';
    }

    fetch('/api/interactions/track', {
        method  : 'POST',
        headers : {
            'Content-Type' : 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body    : JSON.stringify({
            product_id : productId || '',
            action,
            category   : category || '',
            duration   : 0
        }),
        keepalive: true
    }).catch(() => {});
}
