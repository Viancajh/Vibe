
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongodb import init_db
from models.user import create_user
from models.interaction import log_interaction
import random
from datetime import datetime, timedelta

# ── Datos falsos de productos (~15 por categoría) ───────────────
PRODUCTS = [
    # === TECNOLOGÍA  ===
    {"name": "iPhone 15 Pro 256GB", "description": "Chip A17 Pro, cámara triple 48MP, pantalla Super Retina 6.1', USB-C, iOS 17.", "price": 24999.99, "category": "Tecnología", "image": "https://i5.walmartimages.com/asr/758522f0-e2b6-42c0-9dac-5aa03fc8faa2.a48fae09b9219f033af779042f071732.jpeg?odnHeight=612&odnWidth=612&odnBg=FFFFFF", "stock": 18, "rating": 4.8, "views": 890, "purchases": 124},
    {"name": "Samsung Galaxy S24 Ultra", "description": "Pantalla AMOLED 6.8', S Pen incluido, cámara 200MP, Snapdragon 8 Gen 3, 5G.", "price": 27999.99, "category": "Tecnología", "image": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=500&auto=format&fit=crop", "stock": 14, "rating": 4.9, "views": 760, "purchases": 98},
    {"name": "Xiaomi Redmi Note 13 Pro", "description": "Pantalla AMOLED 6.67', cámara 200MP, carga rápida 67W, 8GB RAM, 256GB.", "price": 6499.99, "category": "Tecnología", "image": "https://http2.mlstatic.com/D_NQ_NP_639426-MLU78441912954_082024-O.webp", "stock": 35, "rating": 4.5, "views": 540, "purchases": 156},
    {"name": "Motorola Edge 40 Neo", "description": "Pantalla pOLED 6.55', MediaTek Dimensity 7030, 68W carga rápida, Android 14.", "price": 5999.99, "category": "Tecnología", "image": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=500&auto=format&fit=crop", "stock": 28, "rating": 4.3, "views": 312, "purchases": 67},
    {"name": "Google Pixel 8", "description": "Cámara con IA Google, Tensor G3, Android puro, actualizaciones garantizadas 7 años.", "price": 15999.99, "category": "Tecnología", "image": "https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=500&auto=format&fit=crop", "stock": 16, "rating": 4.6, "views": 420, "purchases": 54},
    {"name": "OPPO Reno 11 5G", "description": "Diseño ultradelgado, cámara portrait 50MP, batería 4800mAh, carga SUPERVOOC 67W.", "price": 8999.99, "category": "Tecnología", "image": "https://m.media-amazon.com/images/I/81mVDGUp9xL._AC_UF894,1000_QL80_.jpg", "stock": 22, "rating": 4.4, "views": 278, "purchases": 41},
    {"name": "Realme 12 Pro+ 5G", "description": "Zoom periscópico 3x, pantalla curva AMOLED 120Hz, carga 80W, 512GB almacenamiento.", "price": 7499.99, "category": "Tecnología", "image": "https://images.unsplash.com/photo-1585060544812-6b45742d762f?w=500&auto=format&fit=crop", "stock": 30, "rating": 4.2, "views": 245, "purchases": 38},
    {"name": "Huawei Nova 12 SE", "description": "Cámara selfie 60MP, pantalla OLED 6.7', batería 4500mAh, diseño premium.", "price": 6999.99, "category": "Tecnología", "image": "https://images.unsplash.com/photo-1556656793-08538906a9f8?w=500&auto=format&fit=crop", "stock": 20, "rating": 4.1, "views": 198, "purchases": 29},
    {"name": "Laptop ProBook 15", "description": "Laptop 15 pulgadas, Intel i7, 16GB RAM, SSD 512GB. Perfecta para trabajo y estudio.", "price": 16999.99, "category": "Tecnología", "image": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=500&auto=format&fit=crop", "stock": 15, "rating": 4.5, "views": 320, "purchases": 45},
    {"name": "Auriculares Bluetooth X3", "description": "Sonido premium, cancelación de ruido activa, 30h de batería. Conectividad multidevice.", "price": 1899.99, "category": "Tecnología", "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop", "stock": 30, "rating": 4.3, "views": 215, "purchases": 67},
    {"name": "Tablet StudyPad 10", "description": "10.5 pulgadas, 4GB RAM, stylus incluido. Ideal para notas y lectura digital.", "price": 4999.99, "category": "Tecnología", "image": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=500&auto=format&fit=crop", "stock": 12, "rating": 4.1, "views": 178, "purchases": 34},
    {"name": "Smartwatch FitPro 4", "description": "Monitor cardíaco, GPS integrado, resistente al agua 50m, 7 días de batería.", "price": 2999.99, "category": "Tecnología", "image": "https://m.media-amazon.com/images/I/71DX2HuFMkL.jpg", "stock": 25, "rating": 4.4, "views": 290, "purchases": 58},
    {"name": "Monitor UltraWide 34", "description": "Panel IPS 34 pulgadas, 144Hz, resolución 3440x1440. Para gamers y diseñadores.", "price": 8999.99, "category": "Tecnología", "image": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop", "stock": 8, "rating": 4.6, "views": 156, "purchases": 22},
    {"name": "Teclado Mecánico RGB", "description": "Switches Cherry MX Red, retroiluminación RGB per-key, aluminio anodizado.", "price": 1799.99, "category": "Tecnología", "image": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500&auto=format&fit=crop", "stock": 40, "rating": 4.2, "views": 201, "purchases": 41},
    {"name": "Cámara Digital Mirrorless", "description": "24MP, lente intercambiable, video 4K 60fps. Kit con lente 18-55mm.", "price": 18999.99, "category": "Tecnología", "image": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=500&auto=format&fit=crop", "stock": 6, "rating": 4.8, "views": 134, "purchases": 18},

    # === GAMING ===
    {"name": "Control Inalámbrico Pro", "description": "Compatible Xbox/PC, vibración háptica, gatillos adaptables, batería 40h.", "price": 1299.99, "category": "Gaming", "image": "https://resources.claroshop.com/medios-plazavip/t1/171814568015png", "stock": 35, "rating": 4.5, "views": 410, "purchases": 95},
    {"name": "Silla Gamer ErgoMax", "description": "Soporte lumbar ajustable, reposacabezas 3D, reclinable 180°, material transpirable.", "price": 5499.99, "category": "Gaming", "image": "https://ferrini.com.mx/cdn/shop/files/11_56f2a756-7155-4a5f-b22e-08edfb64bea8.png?v=1745973926", "stock": 10, "rating": 4.3, "views": 267, "purchases": 31},
    {"name": "Headset Gaming Surround 7.1", "description": "Sonido 7.1 virtual, micrófono retráctil con cancelación de ruido, USB/Jack 3.5mm.", "price": 1499.99, "category": "Gaming", "image": "https://images.unsplash.com/photo-1599669454699-248893623440?w=500&auto=format&fit=crop", "stock": 22, "rating": 4.1, "views": 189, "purchases": 44},
    {"name": "Mouse Gaming 16000 DPI", "description": "16000 DPI ajustable, 8 botones programables, polling rate 1000Hz, RGB.", "price": 899.99, "category": "Gaming", "image": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=500&auto=format&fit=crop", "stock": 50, "rating": 4.4, "views": 335, "purchases": 78},
    {"name": "Consola PortaGame X", "description": "Pantalla OLED 7 pulgadas, 256GB, compatible con TV, batería 9 horas.", "price": 8999.99, "category": "Gaming", "image": "https://images.unsplash.com/photo-1486401899868-0e435ed85128?w=500&auto=format&fit=crop", "stock": 18, "rating": 4.9, "views": 520, "purchases": 102},
    {"name": "Alfombrilla Gaming XL", "description": "900x400mm, superficie de control preciso, base antideslizante, costuras reforzadas.", "price": 399.99, "category": "Gaming", "image": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=500&auto=format&fit=crop", "stock": 60, "rating": 4.0, "views": 145, "purchases": 55},
    {"name": "Teclado Gaming 60%", "description": "Formato compacto, switches hot-swap, RGB por tecla, ideal para FPS.", "price": 1699.99, "category": "Gaming", "image": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500&auto=format&fit=crop", "stock": 32, "rating": 4.5, "views": 220, "purchases": 48},
    {"name": "Webcam Streaming 4K", "description": "Resolución 4K 30fps, autofoco, micrófono dual, compatible OBS y Discord.", "price": 2199.99, "category": "Gaming", "image": "https://http2.mlstatic.com/D_NQ_NP_986998-MLA99499696460_112025-O.webp", "stock": 24, "rating": 4.3, "views": 167, "purchases": 33},
    {"name": "Volante Racing Pro", "description": "Force feedback, pedales incluidos, compatible PC y consolas, ángulo 900°.", "price": 4599.99, "category": "Gaming", "image": "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=500&auto=format&fit=crop", "stock": 8, "rating": 4.6, "views": 198, "purchases": 19},
    {"name": "Micrófono Condenser RGB", "description": "Captación cardioide, filtro antipop, salida USB-C, ideal para streamers.", "price": 1899.99, "category": "Gaming", "image": "https://coolboxmx.vtexassets.com/arquivos/ids/164370-800-800?v=638791214336500000&width=800&height=800&aspect=true", "stock": 26, "rating": 4.4, "views": 143, "purchases": 27},
    {"name": "Soporte Monitor Dual", "description": "Brazo articulado para 2 monitores hasta 27', ajuste de altura e inclinación.", "price": 1299.99, "category": "Gaming", "image": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop", "stock": 19, "rating": 4.2, "views": 112, "purchases": 21},
    {"name": "Lentes VR Quest 3", "description": "Realidad virtual standalone, resolución 2064x2208 por ojo, controles incluidos.", "price": 9999.99, "category": "Gaming", "image": "https://lookaside.fbsbx.com/elementpath/media/?media_id=157327897433582&version=1778040807&transcode_extension=webp", "stock": 11, "rating": 4.7, "views": 380, "purchases": 42},
    {"name": "Kit Luces LED RGB", "description": "Tiras LED sincronizables con juegos, app móvil, 16 millones de colores.", "price": 599.99, "category": "Gaming", "image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=500&auto=format&fit=crop", "stock": 45, "rating": 4.0, "views": 156, "purchases": 63},
    {"name": "Mando Arcade Fight Stick", "description": "Palancas Sanwa, 8 botones, compatible PC/PS/Switch, diseño torneo.", "price": 2499.99, "category": "Gaming", "image": "https://i5.walmartimages.com/asr/3c2e22da-111f-4ca3-89d9-849bbf09fdc0.d0926d1e5573eafc61df55ba8d4e42d8.jpeg?odnHeight=612&odnWidth=612&odnBg=FFFFFF", "stock": 14, "rating": 4.5, "views": 98, "purchases": 15},
    {"name": "Escritorio Gaming Ajustable", "description": "Superficie 140cm, altura eléctrica ajustable, soporte para cableado.", "price": 6999.99, "category": "Gaming", "image": "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=500&auto=format&fit=crop", "stock": 9, "rating": 4.4, "views": 234, "purchases": 26},

    # === ROPA  ===
    {"name": "Hoodie Oversized Urban", "description": "100% algodón premium, corte oversized, múltiples colores, unisex.", "price": 699.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=500&auto=format&fit=crop", "stock": 80, "rating": 4.2, "views": 230, "purchases": 87},
    {"name": "Zapatillas RunFast Pro", "description": "Suela amortiguadora, transpirable, peso ultraligero. Running y uso casual.", "price": 1499.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500&auto=format&fit=crop", "stock": 45, "rating": 4.6, "views": 398, "purchases": 113},
    {"name": "Jeans Slim Fit Classic", "description": "Denim premium elastizado, corte slim, azul y negro. Tallas S-XXL.", "price": 899.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=500&auto=format&fit=crop", "stock": 70, "rating": 4.1, "views": 175, "purchases": 62},
    {"name": "Chaqueta Impermeable", "description": "Material técnico impermeable, capucha ajustable, 3 bolsillos.", "price": 1299.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1544022613-e87ca75a784a?w=500&auto=format&fit=crop", "stock": 30, "rating": 4.3, "views": 142, "purchases": 38},
    {"name": "Camiseta Dry-Fit Sport", "description": "Secado rápido, protección UV, ligera, perfecta para gym.", "price": 449.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500&auto=format&fit=crop", "stock": 100, "rating": 4.0, "views": 198, "purchases": 91},
    {"name": "Sudadera Zip-Up Premium", "description": "Felpa french terry, cierre YKK, bolsillos laterales, fit regular.", "price": 799.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=500&auto=format&fit=crop", "stock": 55, "rating": 4.3, "views": 167, "purchases": 44},
    {"name": "Pantalón Cargo Street", "description": "6 bolsillos funcionales, tela resistente, estilo urbano unisex.", "price": 749.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=500&auto=format&fit=crop", "stock": 42, "rating": 4.1, "views": 134, "purchases": 36},
    {"name": "Vestido Casual Midi", "description": "Tela fluida, corte A-line, ideal para día o noche.", "price": 899.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=500&auto=format&fit=crop", "stock": 38, "rating": 4.4, "views": 189, "purchases": 52},
    {"name": "Gorra Snapback Vibe", "description": "Bordado frontal, visera plana, ajuste snapback, algodón.", "price": 349.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=500&auto=format&fit=crop", "stock": 90, "rating": 4.0, "views": 210, "purchases": 78},
    {"name": "Mochila Urbana 25L", "description": "Compartimento laptop 15', resistente al agua, puerto USB.", "price": 999.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500&auto=format&fit=crop", "stock": 48, "rating": 4.5, "views": 276, "purchases": 64},
    {"name": "Sandalias Slide Comfort", "description": "Suela EVA ultracómoda, diseño minimalista, unisex.", "price": 499.99, "category": "Ropa", "image": "https://http2.mlstatic.com/D_NQ_NP_699365-MLM109382414821_032026-O.webp", "stock": 65, "rating": 4.2, "views": 145, "purchases": 49},
    {"name": "Blazer Slim Fit", "description": "Corte entallado, ideal oficina o eventos, mezcla poliéster.", "price": 1599.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=500&auto=format&fit=crop", "stock": 22, "rating": 4.3, "views": 98, "purchases": 18},
    {"name": "Leggings Yoga Pro", "description": "Alta compresión, cintura alta, tela squat-proof, secado rápido.", "price": 549.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=500&auto=format&fit=crop", "stock": 75, "rating": 4.6, "views": 312, "purchases": 95},
    {"name": "Playera Polo Clásica", "description": "Piqué de algodón, cuello ribeteado, botones grabados.", "price": 599.99, "category": "Ropa", "image": "https://images.unsplash.com/photo-1586363104862-3a5e2ab60d99?w=500&auto=format&fit=crop", "stock": 58, "rating": 4.1, "views": 123, "purchases": 41},
    {"name": "Botas Chelsea Cuero", "description": "Cuero sintético premium, suela antideslizante, estilo atemporal.", "price": 1899.99, "category": "Ropa", "image": "https://brantano.com.mx/cdn/shop/files/JR11118VINO_4.jpg?v=1760052417&width=2000", "stock": 20, "rating": 4.5, "views": 156, "purchases": 28},

    # === HOGAR  ===
    {"name": "Cafetera Espresso Auto", "description": "Molinillo integrado, 19 bares, pantalla táctil, depósito 2L.", "price": 4999.99, "category": "Hogar", "image": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=500&auto=format&fit=crop", "stock": 15, "rating": 4.7, "views": 310, "purchases": 49},
    {"name": "Foco LED Inteligente", "description": "Compatible Alexa/Google, 16M colores, regulable, bajo consumo.", "price": 299.99, "category": "Hogar", "image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=500&auto=format&fit=crop", "stock": 55, "rating": 4.2, "views": 164, "purchases": 72},
    {"name": "Robot Aspirador Smart", "description": "Mapeo inteligente, app móvil, autonomía 120min, autovaciado.", "price": 6499.99, "category": "Hogar", "image": "https://http2.mlstatic.com/D_Q_NP_2X_668420-MLM109872410484_042026-P.webp", "stock": 12, "rating": 4.5, "views": 287, "purchases": 35},
    {"name": "Set Utensilios Cocina 20pz", "description": "Acero inoxidable, diseño ergonómico, aptos para lavavajillas.", "price": 899.99, "category": "Hogar", "image": "https://images.unsplash.com/photo-1556910103-1c02745aae4d?w=500&auto=format&fit=crop", "stock": 28, "rating": 4.1, "views": 121, "purchases": 43},
    {"name": "Cojines Decorativos Pack x3", "description": "45x45cm, relleno alta densidad, fundas lavables, varios diseños.", "price": 599.99, "category": "Hogar", "image": "https://ss157.liverpool.com.mx/xl/1141067504.jpg", "stock": 40, "rating": 3.9, "views": 89, "purchases": 27},
    {"name": "Lámpara de Mesa Minimal", "description": "LED regulable, puerto USB de carga, base de madera, luz cálida.", "price": 449.99, "category": "Hogar", "image": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=500&auto=format&fit=crop", "stock": 36, "rating": 4.3, "views": 145, "purchases": 38},
    {"name": "Organizador de Closet", "description": "6 estantes modulares, tubo de acero, fundas de tela resistente.", "price": 799.99, "category": "Hogar", "image": "https://resources.claroshop.com/medios-plazavip/s2/10205/1449288/5ee424510d6eb-mkz-closetgris-1600x1600.jpg?scale=500&qlty=75", "stock": 25, "rating": 4.0, "views": 98, "purchases": 22},
    {"name": "Ventilador Torre Silencioso", "description": "3 velocidades, control remoto, oscilación 90°, bajo ruido.", "price": 1299.99, "category": "Hogar", "image": "https://http2.mlstatic.com/D_NQ_NP_999085-MLA99961006005_112025-O.webp", "stock": 18, "rating": 4.2, "views": 167, "purchases": 31},
    {"name": "Juego de Sábanas Queen", "description": "Microfibra suave, 4 piezas, incluye fundas, varios colores.", "price": 699.99, "category": "Hogar", "image": "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=500&auto=format&fit=crop", "stock": 50, "rating": 4.4, "views": 203, "purchases": 56},
    {"name": "Purificador de Aire HEPA", "description": "Filtro HEPA H13, cubre 30m², modo silencioso, indicador de calidad.", "price": 3499.99, "category": "Hogar", "image": "https://m.media-amazon.com/images/I/71tKyP04wsL._AC_UF894,1000_QL80_.jpg", "stock": 14, "rating": 4.6, "views": 178, "purchases": 24},
    {"name": "Batería de Cocina Antiadherente", "description": "5 piezas, recubrimiento cerámico, apta inducción, mangos ergonómicos.", "price": 1899.99, "category": "Hogar", "image": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=500&auto=format&fit=crop", "stock": 22, "rating": 4.5, "views": 156, "purchases": 33},
    {"name": "Espejo Decorativo Redondo", "description": "Marco dorado 60cm, estilo moderno, listo para colgar.", "price": 999.99, "category": "Hogar", "image": "https://images.unsplash.com/photo-1618220179428-22790b461013?w=500&auto=format&fit=crop", "stock": 16, "rating": 4.3, "views": 112, "purchases": 19},
    {"name": "Maceta Cerámica Set x3", "description": "Drenaje incluido, diseño minimalista, ideal plantas de interior.", "price": 399.99, "category": "Hogar", "image": "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=500&auto=format&fit=crop", "stock": 44, "rating": 4.1, "views": 134, "purchases": 47},
    {"name": "Freidora de Aire 5.5L", "description": "8 programas, pantalla digital, cocción sin aceite, bandeja extraíble.", "price": 2199.99, "category": "Hogar", "image": "https://http2.mlstatic.com/D_NQ_NP_978381-MLA84550112986_052025-O.webp", "stock": 20, "rating": 4.7, "views": 345, "purchases": 68},
    {"name": "Reloj de Pared Moderno", "description": "Mecanismo silencioso, números 3D, diámetro 35cm, pilas incluidas.", "price": 349.99, "category": "Hogar", "image": "https://i.pinimg.com/originals/ca/47/dd/ca47ddab1db42b20ca3b1ab3a0114de8.jpg", "stock": 52, "rating": 4.0, "views": 87, "purchases": 29},
]

# ── Usuarios de prueba ─────────────────────────────────────────
TEST_USERS = [
    ("Ana García",      "ana@test.com",     "pass123"),
    ("Carlos López",    "carlos@test.com",  "pass123"),
    ("María Rodríguez", "maria@test.com",   "pass123"),
    ("Pedro Sánchez",   "pedro@test.com",   "pass123"),
    ("Laura Martínez",  "laura@test.com",   "pass123"),
]


def seed():
    db = init_db()

    # Limpiar colecciones
    db.products.drop()
    db.users.drop()
    db.interactions.drop()
    db.carts.drop()
    db.orders.drop()
    print("   Colecciones limpias")

    # Insertar productos
    db.products.insert_many(PRODUCTS)
    print(f"  {len(PRODUCTS)} productos insertados")

    # Crear índice de texto
    db.products.create_index([("name", "text"), ("description", "text")])

    # Insertar usuarios
    user_ids = []
    for name, email, pwd in TEST_USERS:
        user = create_user(db, name, email, pwd)
        user_ids.append(str(user["_id"]))
    print(f"  {len(user_ids)} usuarios creados")

    # Generar interacciones sintéticas realistas
    products = list(db.products.find())
    categories = ["Tecnología", "Gaming", "Ropa", "Hogar"]

    # Perfiles de usuario (qué categorías prefieren)
    preferences = [
        ["Tecnología", "Gaming"],    # Ana
        ["Gaming", "Tecnología"],    # Carlos
        ["Ropa", "Hogar"],           # María
        ["Hogar", "Ropa"],           # Pedro
        ["Tecnología", "Ropa"],      # Laura
    ]

    interactions_count = 0
    for idx, user_id in enumerate(user_ids):
        pref_cats = preferences[idx % len(preferences)]

        # Filtrar productos de categorías preferidas
        preferred_products = [p for p in products if p["category"] in pref_cats]
        other_products     = [p for p in products if p["category"] not in pref_cats]

        # Ver muchos productos preferidos
        for p in random.sample(preferred_products, min(12, len(preferred_products))):
            pid = str(p["_id"])
            # View
            log_interaction(db, user_id, pid, "view", p["category"], random.randint(10, 120))
            interactions_count += 1
            # Click con 80% de probabilidad
            if random.random() > 0.2:
                log_interaction(db, user_id, pid, "click", p["category"])
                interactions_count += 1
            # Cart con 40% de probabilidad
            if random.random() > 0.6:
                log_interaction(db, user_id, pid, "cart", p["category"])
                interactions_count += 1
            # Purchase con 20% de probabilidad
            if random.random() > 0.8:
                log_interaction(db, user_id, pid, "purchase", p["category"])
                interactions_count += 1

        # Ver pocos productos de otras categorías
        for p in random.sample(other_products, min(5, len(other_products))):
            pid = str(p["_id"])
            log_interaction(db, user_id, pid, "view", p["category"], random.randint(5, 30))
            interactions_count += 1

    print(f" {interactions_count} interacciones generadas")

    _ml = os.path.dirname(os.path.abspath(__file__))
    if _ml not in sys.path:
        sys.path.insert(0, _ml)
    from export_dataset import export_all
    print("\n  Generando archivos CSV del dataset…")
    export_all(db)

    print("\n  Base de datos lista para usar!")
    print("\n  Solo productos (sin borrar usuarios): python ml/seed_products.py")


if __name__ == "__main__":
    seed()
