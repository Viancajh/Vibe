
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
async function apiFetch(url, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
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
    if (!badge || !getToken()) return;

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
    if (!getToken()) {
        showToast('Inicia sesión para agregar al carrito');
        setTimeout(() => location.href = '/login', 1200);
        return;
    }
    try {
        const res  = await apiFetch('/api/cart/add', {
            method : 'POST',
            body   : JSON.stringify({ product_id: productId, quantity: 1 })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(`"${productName}" agregado al carrito`);
            updateCartBadge();
        } else if (res.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            showToast('Sesión expirada. Inicia sesión de nuevo.');
            setTimeout(() => location.href = '/login', 1200);
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
