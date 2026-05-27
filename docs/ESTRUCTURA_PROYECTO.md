# 📂 Estructura del Proyecto Ceiba21-Cotizaciones

**Última actualización**: Mayo 2026  
**Versión**: 1.0

---

## 📋 Índice

1. [Descripción General](#-descripción-general)
2. [Árbol de Directorios](#-árbol-de-directorios)
3. [Descripción de Carpetas](#-descripción-de-carpetas)
4. [Archivos Raíz](#-archivos-raíz)
5. [Módulos de Aplicación](#-módulos-de-aplicación)
6. [Stack Tecnológico](#-stack-tecnológico)
7. [Arquitectura de Capas](#-arquitectura-de-capas)
8. [Flujo de Datos](#-flujo-de-datos)

---

## 🎯 Descripción General

**Ceiba21-Cotizaciones** es una plataforma completa de exchange de criptomonedas construida con Flask 3.1, PostgreSQL 17 y Python 3.13. El sistema gestiona cotizaciones de divisas, publica automáticamente en Telegram, y proporciona un dashboard administrativo para operadores.

**Características principales**:
- Sistema de cotizaciones con fórmulas programables
- Publicación automática en Telegram con generación de imágenes
- Dashboard administrativo para gestión de monedas y tasas
- Bot conversacional multicanal (Telegram, Web, WhatsApp)
- Sistema de órdenes y transacciones
- Blacklist y verificación de fraude
- Calculadora PayPal con comisiones
- API REST para consultas externas

---

## 🌲 Árbol de Directorios

```
ceiba21-cotizaciones/
│
├── 🔒 .clineignore              # Archivos bloqueados para Cline AI
├── .clinerules                  # Reglas de codificación para Cline AI
├── .env.example                 # Plantilla de variables de entorno
├── .gitignore                   # Archivos ignorados por Git
├── README.md                    # Documentación principal del proyecto
├── requirements.txt             # Dependencias Python (42 paquetes)
├── start_bot.py                 # Script para iniciar bot de Telegram
├── wsgi.py                      # Entry point para Gunicorn/WSGI
│
├── 📁 app/                      # Aplicación Flask principal
│   ├── __init__.py              # Factory pattern, inicialización de Flask
│   ├── config.py                # Configuración (dev/prod), variables de entorno
│   │
│   ├── 📁 bot/                  # Bot conversacional multicanal
│   │   ├── __init__.py
│   │   ├── conversation_handler.py    # Maneja el flujo de conversación
│   │   ├── message_parser.py          # Parsea intención del usuario
│   │   ├── responses.py               # Genera respuestas del bot
│   │   └── states.py                  # Estados de la conversación
│   │
│   ├── 📁 channels/             # Canales de comunicación
│   │   ├── __init__.py
│   │   ├── base_channel.py            # Interfaz base para canales
│   │   ├── telegram_channel.py        # Integración con Telegram
│   │   ├── webchat_channel.py         # Chat web en navegador
│   │   └── whatsapp_channel.py        # Integración con WhatsApp
│   │
│   ├── 📁 models/               # Modelos SQLAlchemy (capa de datos)
│   │   ├── __init__.py
│   │   ├── base.py                    # Modelo base con timestamps
│   │   ├── blacklist.py               # Reportes y apelaciones de blacklist
│   │   ├── currency.py                # Monedas (VES, USD, BRL, MXN, etc.)
│   │   ├── exchange_rate.py           # Tasas de cambio entre monedas
│   │   ├── message.py                 # Mensajes del bot conversacional
│   │   ├── operator.py                # Operadores del sistema
│   │   ├── order.py                   # Órdenes de compra/venta
│   │   ├── payment_method.py          # Métodos de pago (PayPal, Zelle, etc.)
│   │   ├── quote.py                   # Cotizaciones con fórmulas
│   │   ├── quote_history.py           # Historial de cambios de cotizaciones
│   │   ├── transaction.py             # Transacciones realizadas
│   │   ├── user.py                    # Usuarios del bot
│   │   └── web_user.py                # Usuarios del dashboard web
│   │
│   ├── 📁 routes/               # Controladores Flask (Blueprints)
│   │   ├── __init__.py
│   │   ├── auth.py                    # Autenticación y login
│   │   ├── blacklist.py               # CRUD de blacklist
│   │   ├── bot_control.py             # Control del bot conversacional
│   │   ├── dashboard.py               # Panel administrativo
│   │   ├── main.py                    # Rutas públicas (API)
│   │   ├── operator_dashboard.py      # Dashboard para operadores
│   │   └── public.py                  # Páginas públicas (calculadora, etc.)
│   │
│   ├── 📁 services/             # Lógica de negocio (capa de servicio)
│   │   ├── __init__.py
│   │   ├── accounting_service.py      # Contabilidad automatizada
│   │   ├── api_service.py             # Servicios externos (tasas de cambio)
│   │   ├── auth_service.py            # Autenticación y autorización
│   │   ├── base_service.py            # Servicio base con métodos comunes
│   │   ├── blacklist_service.py       # Lógica de blacklist
│   │   ├── bot_service.py             # Lógica del bot conversacional
│   │   ├── cache_service.py           # Caché con Redis
│   │   ├── calculator_service.py      # Cálculos de comisiones PayPal
│   │   ├── currency_service.py        # Gestión de monedas
│   │   ├── exchange_rate_service.py   # Gestión de tasas de cambio
│   │   ├── fraud_check_service.py     # Verificación de fraude
│   │   ├── image_service.py           # Generación de imágenes
│   │   ├── notification_service.py    # Notificaciones (email, Telegram)
│   │   ├── order_service.py           # Gestión de órdenes
│   │   ├── payment_method_service.py  # Gestión de métodos de pago
│   │   ├── quote_service.py           # Gestión de cotizaciones
│   │   └── user_service.py            # Gestión de usuarios
│   │
│   ├── 📁 static/               # Archivos estáticos
│   │   ├── 📁 css/
│   │   │   └── style.css              # Estilos personalizados
│   │   ├── 📁 img/
│   │   │   ├── favicon-*.png          # Favicons en varios tamaños
│   │   │   ├── favicon.svg            # Favicon vectorial
│   │   │   ├── 📁 logos/              # Logos de monedas y métodos
│   │   │   └── 🔒 📁 telegram_posts/  # Imágenes generadas para Telegram
│   │   ├── 📁 js/
│   │   │   └── bot_control.js         # Control del bot desde dashboard
│   │   └── 🔒 📁 proofs/              # Comprobantes de pago subidos
│   │
│   ├── 📁 telegram/             # Integración con Telegram
│   │   ├── __init__.py
│   │   ├── bot.py                     # Bot publisher (publica cotizaciones)
│   │   ├── bot_conversational.py      # Bot conversacional interactivo
│   │   ├── formatters.py              # Formateo de mensajes Telegram
│   │   └── image_generator.py         # Genera imágenes de cotizaciones
│   │
│   ├── 📁 templates/            # Plantillas Jinja2 (vistas)
│   │   ├── base.html                  # Template base (dashboard)
│   │   ├── public_base.html           # Template base (público)
│   │   │
│   │   ├── 📁 auth/
│   │   │   └── login.html             # Página de login
│   │   │
│   │   ├── 📁 blacklist/
│   │   │   ├── appeals_list.html      # Lista de apelaciones
│   │   │   ├── create_report.html     # Crear reporte de blacklist
│   │   │   ├── dashboard.html         # Dashboard de blacklist
│   │   │   ├── edit_report.html       # Editar reporte
│   │   │   ├── report_detail.html     # Detalle de reporte
│   │   │   ├── search_results.html    # Resultados de búsqueda
│   │   │   └── user_profile.html      # Perfil de usuario reportado
│   │   │
│   │   ├── 📁 dashboard/
│   │   │   ├── currencies.html        # Gestión de monedas
│   │   │   ├── index.html             # Dashboard principal
│   │   │   ├── operators.html         # Gestión de operadores
│   │   │   ├── payment_methods.html   # Gestión de métodos de pago
│   │   │   ├── rates.html             # Gestión de tasas de cambio
│   │   │   └── telegram.html          # Publicación en Telegram
│   │   │
│   │   ├── 📁 operator/
│   │   │   ├── order_detail.html      # Detalle de orden
│   │   │   └── orders.html            # Lista de órdenes del operador
│   │   │
│   │   └── 📁 public/
│   │       ├── calculadora.html       # Calculadora PayPal pública
│   │       ├── condiciones.html       # Términos y condiciones
│   │       ├── cotizaciones.html      # Cotizaciones públicas
│   │       └── home.html              # Página de inicio
│   │
│   ├── 📁 tests/                # Tests con pytest
│   │   ├── __init__.py
│   │   ├── conftest.py                # Configuración de fixtures
│   │   ├── test_models.py             # Tests de modelos
│   │   └── test_routes.py             # Tests de rutas
│   │
│   └── 📁 utils/                # Utilidades
│       ├── __init__.py
│       └── markdown.py                # Conversión de markdown
│
├── 📁 docs/                     # Documentación técnica
│   ├── BLACKLIST_IMPLEMENTATION.md          # Sistema de blacklist
│   ├── CURRENCY_MANAGEMENT.md               # Gestión de monedas
│   ├── DEPLOY_GUIDE.md                      # Guía de despliegue
│   ├── ESTRUCTURA_PROYECTO.md               # Este archivo
│   ├── FASE_4_BOT_CONVERSACIONAL.md         # Bot conversacional
│   ├── FASE_5_DASHBOARD_OPERADORES.md       # Dashboard operadores
│   ├── FASE_6_CONTABILIDAD_AUTOMATICA.md    # Contabilidad
│   ├── PLAN_SISTEMA_ORDENES.md              # Sistema de órdenes
│   ├── PROCESO_FANTASMA_SOLUCION.md         # Solución a bugs
│   ├── PROMPT_ACTUALIZADO_CLINE.md          # Prompts para Cline AI
│   ├── PROMPT_FINAL_CLINE.md                # Prompts finales
│   ├── SOLUCION_BOT_TELEGRAM.md             # Integración Telegram
│   ├── SOLUCION_BRL_MXN.md                  # Soporte BRL/MXN
│   ├── SOLUCION_ESCALABLE_FORMULAS.md       # Fórmulas escalables
│   └── SOLUCION_REAL_BRL_MXN.md             # Implementación BRL/MXN
│
└── 📁 scripts/                  # Scripts de migración y utilidades
    ├── activate_currencies.py               # Activa monedas
    ├── add_audit_fields.py                  # Agrega campos de auditoría
    ├── add_blacklist_fields.py              # Migración blacklist
    ├── add_photo_and_reporter_fields.py     # Migración de campos
    ├── analyze_quote_values.py              # Analiza cotizaciones
    ├── check_currency_status.py             # Verifica estado monedas
    ├── check_order_data.py                  # Verifica datos de órdenes
    ├── convert_logos.py                     # Convierte logos
    ├── create_blacklist_tables.py           # Crea tablas blacklist
    ├── create_tables.py                     # Crea tablas de BD
    ├── fix_brl_mxn_quotes.py                # Corrige cotizaciones BRL/MXN
    ├── fix_currencies.py                    # Corrige datos de monedas
    ├── health_check.py                      # Verifica salud del sistema
    ├── migrate_to_centralized_formulas.py   # Migra a fórmulas centralizadas
    ├── safe_restart.sh                      # Reinicia servicios de forma segura
    ├── seed_data.py                         # Datos de prueba
    ├── seed_operators.py                    # Crea operadores de prueba
    ├── test_bot_structure.py                # Prueba estructura del bot
    └── test_redis.py                        # Prueba conexión Redis
```

---

## 📁 Descripción de Carpetas

### 🔵 `/app` - Aplicación Principal

Contiene toda la lógica de la aplicación Flask. Sigue el patrón Factory con separación estricta de capas.

#### 🤖 `/app/bot` - Bot Conversacional

Sistema de bot multicanal que maneja conversaciones con usuarios. Soporta Telegram, Web y WhatsApp.

- **conversation_handler.py**: Orquesta el flujo de conversación
- **message_parser.py**: Analiza intención del usuario (NLP básico)
- **responses.py**: Genera respuestas contextuales
- **states.py**: Define estados de la máquina de estados

#### 📡 `/app/channels` - Canales de Comunicación

Implementaciones de diferentes canales de comunicación con patrón Strategy.

- **base_channel.py**: Interfaz abstracta para todos los canales
- **telegram_channel.py**: Canal de Telegram
- **webchat_channel.py**: Chat web embebido
- **whatsapp_channel.py**: Canal de WhatsApp

#### 💾 `/app/models` - Modelos de Datos

Modelos SQLAlchemy que representan las tablas de la base de datos PostgreSQL.

| Modelo | Descripción |
|--------|-------------|
| `base.py` | Modelo base con campos `created_at` y `updated_at` |
| `blacklist.py` | Reportes de usuarios fraudulentos y apelaciones |
| `currency.py` | Monedas soportadas (VES, USD, BRL, MXN, COP, etc.) |
| `exchange_rate.py` | Tasas de cambio entre pares de monedas |
| `message.py` | Mensajes enviados/recibidos del bot |
| `operator.py` | Operadores del sistema con credenciales |
| `order.py` | Órdenes de compra/venta de usuarios |
| `payment_method.py` | Métodos de pago (PayPal, Zelle, USDT, etc.) |
| `quote.py` | Cotizaciones con fórmulas programables |
| `quote_history.py` | Historial de cambios de cotizaciones |
| `transaction.py` | Transacciones completadas |
| `user.py` | Usuarios del bot conversacional |
| `web_user.py` | Usuarios administradores del dashboard |

#### 🛣️ `/app/routes` - Controladores (Blueprints)

Blueprints de Flask que manejan las rutas HTTP. **Solo orquestación, sin lógica de negocio**.

| Route | Descripción |
|-------|-------------|
| `auth.py` | Login, logout, autenticación |
| `blacklist.py` | CRUD de reportes de blacklist |
| `bot_control.py` | Control del bot (start/stop) |
| `dashboard.py` | Panel administrativo completo |
| `main.py` | API REST pública |
| `operator_dashboard.py` | Dashboard para operadores |
| `public.py` | Páginas públicas (home, calculadora) |

#### ⚙️ `/app/services` - Lógica de Negocio

**Toda la lógica de negocio va aquí**. Los routes llaman a los services, nunca directamente a los models.

| Servicio | Responsabilidad |
|----------|----------------|
| `accounting_service.py` | Generación de asientos contables |
| `api_service.py` | Consumo de APIs externas (BCV, Binance) |
| `auth_service.py` | Autenticación y autorización |
| `base_service.py` | Clase base con operaciones CRUD comunes |
| `blacklist_service.py` | Lógica de blacklist y apelaciones |
| `bot_service.py` | Lógica del bot conversacional |
| `cache_service.py` | Gestión de caché con Redis |
| `calculator_service.py` | Cálculos de comisiones PayPal |
| `currency_service.py` | Gestión de monedas |
| `exchange_rate_service.py` | Gestión de tasas de cambio |
| `fraud_check_service.py` | Verificación de fraude y riesgo |
| `image_service.py` | Generación de imágenes para Telegram |
| `notification_service.py` | Envío de notificaciones |
| `order_service.py` | Gestión de órdenes |
| `payment_method_service.py` | Gestión de métodos de pago |
| `quote_service.py` | Gestión de cotizaciones y fórmulas |
| `user_service.py` | Gestión de usuarios |

#### 🎨 `/app/static` - Archivos Estáticos

- **css/**: Estilos personalizados (Tailwind vía CDN)
- **img/**: Favicons, logos de monedas/métodos
- **img/telegram_posts/**: Imágenes generadas para publicar en Telegram
- **js/**: JavaScript vanilla para interactividad
- **proofs/**: Comprobantes de pago subidos por usuarios

#### 📱 `/app/telegram` - Integración Telegram

| Archivo | Propósito |
|---------|-----------|
| `bot.py` | Bot publisher (publica cotizaciones) |
| `bot_conversational.py` | Bot interactivo conversacional |
| `formatters.py` | Formateo de mensajes Telegram |
| `image_generator.py` | Genera imágenes con Pillow/CairoSVG |

#### 🖼️ `/app/templates` - Vistas Jinja2

Templates HTML organizados por módulo. **Sin lógica Python, solo presentación**.

- **auth/**: Páginas de autenticación
- **blacklist/**: UI de blacklist
- **dashboard/**: Panel administrativo
- **operator/**: Dashboard de operadores
- **public/**: Páginas públicas

#### ✅ `/app/tests` - Tests

Tests con pytest y pytest-flask.

```bash
# Ejecutar tests
python -m pytest app/tests/ -v
```

#### 🔧 `/app/utils` - Utilidades

Funciones helper reutilizables (conversión de markdown, etc.)

### 📚 `/docs` - Documentación

Documentación técnica del proyecto en formato Markdown.

### 🔨 `/scripts` - Scripts de Migración

Scripts Python para migraciones de base de datos, seeds, y utilidades de mantenimiento.

---

## 📄 Archivos Raíz

| Archivo | Descripción |
|---------|-------------|
| `.clineignore` | 🔒 Archivos bloqueados para Cline AI (venv, BD, logs) |
| `.clinerules` | Reglas de codificación para Cline AI |
| `.env.example` | Plantilla de variables de entorno |
| `.gitignore` | Archivos ignorados por Git |
| `README.md` | Documentación principal del proyecto |
| `requirements.txt` | Dependencias Python (42 paquetes) |
| `start_bot.py` | Script para iniciar bot de Telegram |
| `wsgi.py` | Entry point WSGI para Gunicorn |

---

## 🧩 Módulos de Aplicación

### Inicialización de Flask

**Archivo**: `app/__init__.py`

Utiliza el patrón Factory para crear la aplicación Flask:

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    login_manager.init_app(app)
    
    # Registrar blueprints
    from app.routes.main import main_bp
    from app.routes.dashboard import dashboard_bp
    # ...
    
    return app
```

### Configuración

**Archivo**: `app/config.py`

```python
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    # ...
```

---

## 🛠️ Stack Tecnológico

### Backend

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Python** | 3.13 | Lenguaje principal |
| **Flask** | 3.1.2 | Framework web |
| **SQLAlchemy** | 2.0.44 | ORM |
| **PostgreSQL** | 17 | Base de datos |
| **Redis** | 5.0.1 | Caché y sesiones |
| **Gunicorn** | 23.0.0 | WSGI server |
| **Flask-Login** | 0.6.3 | Autenticación |
| **Flask-Caching** | 2.1.0 | Sistema de caché |

### Telegram

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **python-telegram-bot** | 22.5 | SDK de Telegram |
| **Pillow** | 12.0.0 | Generación de imágenes |
| **CairoSVG** | 2.8.2 | Renderizado SVG |

### Frontend

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **Tailwind CSS** | 3.x (CDN) | Framework CSS |
| **Vanilla JS** | ES6+ | Interactividad |
| **Jinja2** | 3.1.6 | Motor de templates |

### Testing

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **pytest** | 9.0.3 | Framework de tests |
| **pytest-flask** | 1.3.0 | Tests de Flask |

### Infraestructura

| Tecnología | Uso |
|------------|-----|
| **Raspberry Pi 5** | Hardware (4 cores, 8GB RAM, 2TB NVMe) |
| **Debian 13 Trixie** | Sistema operativo |
| **Cloudflare Tunnel** | Túnel seguro sin exponer puertos |
| **Nginx** | Proxy reverso |
| **Systemd** | Gestión de servicios |
| **Netdata** | Monitoreo del sistema |

---

## 🏗️ Arquitectura de Capas

El proyecto sigue una arquitectura de **3 capas estrictas**:

```
┌─────────────────────────────────────────┐
│          TEMPLATES (Views)              │
│  Jinja2 - Solo presentación HTML       │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│          ROUTES (Controllers)           │
│  Blueprints - Solo orquestación         │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│          SERVICES (Business Logic)      │
│  Toda la lógica de negocio aquí        │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│          MODELS (Data Layer)            │
│  SQLAlchemy - Lógica de datos           │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│          DATABASE (PostgreSQL 17)       │
│  ceiba21_dev / ceiba21_prod            │
└─────────────────────────────────────────┘
```

### Reglas de Arquitectura

1. ✅ **Templates** pueden usar helpers de Jinja2, pero **sin lógica Python**
2. ✅ **Routes** solo orquestan: reciben request, llaman a services, retornan response
3. ✅ **Services** contienen **toda** la lógica de negocio
4. ✅ **Models** solo definen estructura de datos y relaciones
5. ❌ **Routes nunca llaman directamente a Models** (siempre vía Services)
6. ❌ **Templates nunca ejecutan lógica de negocio**

---

## 🔄 Flujo de Datos

### Ejemplo: Publicar Cotización en Telegram

```
1. Usuario hace clic en "Publicar" (Template)
         ↓
2. POST /dashboard/telegram/publish (Route)
         ↓
3. telegram_service.publish_quotes() (Service)
         ↓
4. quote_service.get_active_quotes() (Service → Model)
         ↓
5. image_service.generate_quote_image() (Service)
         ↓
6. telegram/bot.py publica en canal (External API)
         ↓
7. Retorna JSON {success: true} (Route → Template)
```

### Ejemplo: Calcular Comisión PayPal

```
1. Usuario ingresa monto en calculadora (Template)
         ↓
2. AJAX POST /api/calculate (Route)
         ↓
3. calculator_service.calculate_paypal() (Service)
         ↓
4. quote_service.get_quote('USD', 'VES', 'PayPal') (Service → Model)
         ↓
5. Aplica fórmula: (monto * tasa) + comisión (Service)
         ↓
6. Retorna JSON con resultado (Route → Template)
         ↓
7. JavaScript actualiza DOM (Template)
```

### Ejemplo: Verificar Blacklist

```
1. Usuario inicia orden (Bot/Template)
         ↓
2. order_service.create_order() (Service)
         ↓
3. fraud_check_service.check_user() (Service)
         ↓
4. blacklist_service.is_blacklisted(user_id) (Service → Model)
         ↓
5. Si está en blacklist → rechazar orden (Service)
         ↓
6. Si no → continuar con orden (Service)
         ↓
7. notification_service.notify_operator() (Service → External)
```

---

## 🔐 Variables de Entorno

**Archivo**: `.env` (creado desde `.env.example`)

```env
# Flask
SECRET_KEY=clave-secreta-segura
FLASK_ENV=development|production

# Database
DATABASE_URL=postgresql://user:pass@localhost/ceiba21_dev

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHANNEL_ID=@ceiba21

# Redis
REDIS_URL=redis://localhost:6379/0

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=hashed_password_aqui
```

---

## 📊 Base de Datos

### Tablas Principales

| Tabla | Descripción |
|-------|-------------|
| `currencies` | Monedas (VES, USD, BRL, MXN, etc.) |
| `payment_methods` | Métodos de pago (PayPal, Zelle, etc.) |
| `quotes` | Cotizaciones con fórmulas |
| `quote_history` | Historial de cambios |
| `exchange_rates` | Tasas entre pares de monedas |
| `orders` | Órdenes de compra/venta |
| `transactions` | Transacciones completadas |
| `users` | Usuarios del bot |
| `web_users` | Usuarios del dashboard |
| `operators` | Operadores del sistema |
| `blacklist_reports` | Reportes de usuarios fraudulentos |
| `blacklist_appeals` | Apelaciones a reportes |
| `messages` | Mensajes del bot conversacional |

### Diagrama de Relaciones (Simplificado)

```
Currency ──┬── Quote ── PaymentMethod
           │
           └── ExchangeRate ── Currency
           
User ── Order ── Operator ── Transaction

User ── BlacklistReport ── BlacklistAppeal

User ── Message ── (Bot conversation history)
```

---

## 🚀 Comandos Útiles

### Desarrollo Local

```bash
# Activar entorno virtual
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
flask run
# o
python wsgi.py

# Ejecutar tests
python -m pytest app/tests/ -v

# Crear migraciones
python scripts/create_tables.py

# Seed de datos
python scripts/seed_data.py
```

### Producción

```bash
# Iniciar servicio
sudo systemctl start ceiba21

# Ver logs
sudo journalctl -u ceiba21 -f

# Reiniciar de forma segura
./scripts/safe_restart.sh
```

---

## 📝 Convenciones de Código

Según `.clinerules`:

1. ✅ **Python 3.13** con Type Hints en todas las funciones
2. ✅ **PEP 8**: snake_case para funciones/variables, PascalCase para clases
3. ✅ **Docstrings** en formato Google para funciones públicas
4. ✅ Separar funciones que superen 60 líneas en módulos independientes
5. ❌ **Nunca** `except: pass` — capturar excepciones específicas
6. ❌ **Nunca** mezclar lógica de negocio en routes

---

## 🎯 Próximos Pasos

Ver `README.md` sección "Roadmap" para features planeadas:

- ⬜ Dashboard web para alertas
- ⬜ Integrar alertas con Telegram
- ⬜ API REST documentada con Swagger
- ⬜ Gráficos de histórico
- ⬜ Sistema de caché con Redis
- ⬜ Multi-idioma (inglés, portugués)

---

## 📞 Soporte

- **Web**: https://ceiba21.com
- **Email**: info@ceiba21.com
- **Telegram**: @ceiba21_oficial

---

**Última actualización**: Mayo 2026  
**Mantenido por**: Jose (Ceiba21) con asistencia de Claude AI
