
// ── Backend remoto (despliegue híbrido Netlify + Render) ──────
// Cuando el frontend se sirve estático en Netlify, window.BACKEND_URL
// (inyectado en base.html) apunta al Flask en Render. Reescribimos las
// llamadas /api/* para que vayan a ese backend. En local queda vacío y
// todo es del mismo origen, sin cambios.
(function () {
    const base = (window.BACKEND_URL || '').replace(/\/$/, '');
    if (!base) return;
    const toRemote = (u) =>
        (typeof u === 'string' && u.startsWith('/api/')) ? base + u : u;

    const realFetch = window.fetch.bind(window);
    window.fetch = (url, opts) => realFetch(toRemote(url), opts);

    if (navigator.sendBeacon) {
        const realBeacon = navigator.sendBeacon.bind(navigator);
        navigator.sendBeacon = (url, data) => realBeacon(toRemote(url), data);
    }
})();

// ── Envío ────────────────────────────────────────────────────
const ENVIO_GRATIS_DESDE = 1500;
const COSTO_ENVIO        = 149;

function calcularEnvio(subtotal) {
    return subtotal >= ENVIO_GRATIS_DESDE ? 0 : COSTO_ENVIO;
}

function formatMoney(n) {
    return `$${Number(n).toFixed(2)}`;
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Fallback de imágenes en cascada: si la URL remota falla, intenta la copia
// local que servimos nosotros (data-local); si esa también falla, placeholder.
function imgFallback(img) {
    const local = img.getAttribute('data-local');
    if (local && !img.dataset.triedLocal) {
        img.dataset.triedLocal = '1';
        img.src = local;
    } else {
        img.onerror = null;
        img.src = '/static/images/placeholder.svg';
    }
}

function goToCategory(cat) {
    const url = cat
        ? `/?category=${encodeURIComponent(cat)}#catalogo`
        : '/?category=#catalogo';
    location.href = url;
}

function addToCartFromBtn(btn) {
    addToCart(btn.dataset.id, btn.dataset.name);
}

function getToken() {
    return localStorage.getItem('token');
}
// Id de invitado: permite tener carrito sin iniciar sesión. Se genera una vez
// por navegador y se manda en cada petición; el backend lo usa si no hay login.
function getGuestId() {
    let id = localStorage.getItem('guest_id');
    if (!id) {
        id = 'guest-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
        localStorage.setItem('guest_id', id);
    }
    return id;
}
async function apiFetch(url, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        'X-Guest-Id': getGuestId(),
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...(options.headers || {})
    };
    return fetch(url, { ...options, headers });
}

function requireLogin() {
    if (!getToken()) {
        location.href = '/login';
        return false;
    }
    return true;
}

let toastTimer = null;

function showToast(msg, duration = 3000) {
    const el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), duration);
}

function initNavbar() {
    const menu = document.getElementById('userMenu');
    if (!menu) return;

    const token = getToken();
    const user  = JSON.parse(localStorage.getItem('user') || '{}');

    if (token && user.name) {
        menu.innerHTML = `
            <div class="nav-account-links">
                <a href="/cuenta#perfil">Perfil</a>
                <a href="/cuenta#tarjetas">Tarjetas</a>
                <a href="/cuenta#pedidos">Pedidos</a>
            </div>
            <a href="/cuenta" class="nav-user-name">${escapeHtml(user.name.split(' ')[0])}</a>
            <button onclick="logout()">Salir</button>`;
    } else {
        menu.innerHTML = `
            <a href="/login">Iniciar sesión</a>
            <a href="/register" style="background:var(--orange);color:white;border-radius:6px">Registrarse</a>`;
    }

    updateCartBadge();
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    showToast('Sesión cerrada');
    setTimeout(() => location.href = '/', 700);
}


async function updateCartBadge() {
    const badge = document.getElementById('cartBadge');
    if (!badge) return;

    try {
        const res  = await apiFetch('/api/cart/');
        const cart = await res.json();
        const count = (cart.items || []).reduce((s, i) => s + i.quantity, 0);
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline' : 'none';
    } catch(e) {
        badge.style.display = 'none';
    }
}

async function addToCart(productId, productName) {
    // Ya no exige login: funciona como invitado (X-Guest-Id) o con sesión.
    try {
        const res  = await apiFetch('/api/cart/add', {
            method : 'POST',
            body   : JSON.stringify({ product_id: productId, quantity: 1 })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(`"${productName}" agregado al carrito`);
            updateCartBadge();
        } else {
            showToast(data.error || data.msg || 'Error al agregar al carrito');
        }
    } catch (e) {
        showToast('Error de conexión con el servidor');
    }
}

function handleSearch(event) {
    event.preventDefault();
    const q = document.getElementById('searchInput').value.trim();
    if (q) {
        location.href = `/search?q=${encodeURIComponent(q)}`;
    }
}
document.addEventListener('DOMContentLoaded', initNavbar);
