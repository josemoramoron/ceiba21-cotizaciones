# 🌳 Ceiba21 — Sistema de Cotizaciones

Plataforma completa de exchange de criptomonedas y divisas construida con Flask 3.1, PostgreSQL 17 y Python 3.13. Gestiona cotizaciones, publica automáticamente en Telegram, ingesta pagos multi-método (PayPal, Zelle y los que se agreguen) en una tabla unificada, ofrece una calculadora pública con conversor de monedas, incorpora mensajería SMS bidireccional vía un gateway Android, y proporciona un dashboard administrativo para operadores.

Desplegada sobre Raspberry Pi 5 con Cloudflare Tunnel — sin exponer puertos, sin IP pública, con SSL automático.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Flask](https://img.shields.io/badge/Flask-3.1.2-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red)
![License](https://img.shields.io/badge/License-Proprietary-red)

---

## 📋 Tabla de Contenidos

- [Módulos del Sistema](#-módulos-del-sistema)
- [Arquitectura](#-arquitectura)
- [Stack Tecnológico](#-stack-tecnológico)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Desarrollo Local](#-desarrollo-local)
- [Flujo de Deploy](#-flujo-de-deploy)
- [API](#-api)
- [Mantenimiento](#-mantenimiento)
- [Monitoreo](#-monitoreo)
- [Troubleshooting](#-troubleshooting)
- [Pendientes por Módulo](#-pendientes-por-módulo)
- [Roadmap](#-roadmap)
- [Licencia](#-licencia)

---

## 🧩 Módulos del Sistema

### 💱 Cotizaciones
CRUD completo para múltiples monedas (VES, COP, BRL, MXN, etc.) y métodos de pago (PayPal, Zelle, USDT, Wise, Binance). Soporta dos modos de valoración:
- **Manual**: valor fijo en USD
- **Fórmula**: cálculo automático basado en tasas de cambio (`BCV_VES * 1.05 + 2`)

Las cotizaciones se recalculan automáticamente cuando cambia una tasa de cambio.

**Visibilidad pública configurable por código (sin migración):**
- Los métodos estructurales/pivote (p. ej. `REF`) permanecen activos para el cálculo interno pero nunca se muestran en superficies públicas (tabla `/cotizaciones`, calculadora, Telegram). La regla vive en el frozenset `PaymentMethod.CODIGOS_NO_PUBLICOS` — única fuente de verdad vía `es_visible_publico` / `get_visibles_publico()`.
- USD se oculta de la tabla `/cotizaciones` mediante el frozenset paralelo `Currency.OCULTAS_EN_COTIZACIONES`, mientras sigue disponible en la calculadora.

### 📱 Publicación en Telegram
Genera imágenes de cotizaciones con Pillow/CairoSVG y las publica en un canal de Telegram. Soporta publicación VES y COP, imagen personalizada opcional, y mensaje adicional. El timeout de las llamadas usa split connect/read `(5, 60)` para evitar que un worker de Gunicorn se bloquee.

### 💳 Ingesta de Pagos Unificada (Multi-método)
Sistema de ingesta que lee correos de pago de Gmail vía IMAP y los unifica en una sola tabla `payments`, sin importar el método. Reemplaza conceptualmente al antiguo `PaypalPayment`. Cada fuente de correo (remitente y método asociado) se configura desde el dashboard mediante el modelo `PaymentSource`, de modo que agregar un nuevo método no requiere tocar código. Para cada correo:
1. Parsea el HTML con BeautifulSoup para extraer monto, comisión, tipo (G&S / F&F en PayPal), transaction ID y fecha
2. Verifica duplicados por `message_id` y `transaction_id`
3. Aplica cotización automática del método correspondiente
4. Guarda en PostgreSQL (tabla unificada `payments`)
5. Marca el correo como leído

La columna `DESTINATARIO` se puebla correctamente para pagos Zelle.

**Ejecución programada (producción):** un script CLI one-shot `scripts/run_ingesta.py` se invoca por `cron` mediante un wrapper shell (`ceiba21_ingesta.sh`). El `APScheduler` embebido queda restringido a `FLASK_ENV=development` para evitar conflictos de múltiples schedulers entre workers de Gunicorn. Para importaciones históricas masivas (que exceden el timeout de Gunicorn) existe `scripts/importar_historico.py`, que acepta una fecha `YYYY-MM-DD` y procesa sin restricción de tiempo HTTP.

### 🧮 Calculadora Pública (Todo-en-uno)
Calculadora en `/calculadora` con dos modos en pestañas de dos niveles:
- **PayPal** (subtabs Recibir / Enviar): calcula comisiones PayPal (5,4% + $0,30 USD) en ambas direcciones, con conversión opcional a moneda local usando la cotización PayPal vigente.
- **Conversor Fiat**: convierte entre cualquier par de monedas (fiat↔fiat) y de método de pago a fiat (método→fiat), usando cotizaciones en tiempo real vía el endpoint `/api/calcular`. El botón de permutación ↔ aplica solo a pares fiat↔fiat.

Las conversiones fiat↔fiat aplican un **margen global configurable** sobre el precio de referencia (`precio_cliente = tasa_ref / (1 + margen/100)`); las conversiones método→fiat usan directamente la cotización del método (que ya incorpora su propio margen). El margen se administra desde el dashboard y se persiste en la tabla `system_config`.

USD funciona como moneda en los selectores (no solo como pivote interno), permitiendo cálculos `USD → COP`, `COP → USD`, etc.

### 🔄 Conversor de Monedas (Dashboard)
Herramienta interna en `/dashboard/conversor` que convierte entre cualquier par de monedas vía cross-rate derivado del pivote USD, con spread configurable por operación. Incluye la sección de configuración del margen de la calculadora pública.

### 📲 Mensajería SMS (Gateway Android Multi-SIM)
Módulo de envío y recepción de SMS integrado en `/dashboard/sms`, que se apoya en la app [SMS Gateway for Android](https://docs.sms-gate.app/) corriendo en un teléfono dedicado en modo Local Server. El teléfono está conectado a un board multi-SIM físico (20 ranuras) mediante cable FPC.

- **Recepción:** la app dispara un webhook (`sms:received`) hacia `/dashboard/sms/webhook/incoming` por cada SMS entrante. El payload llega anidado bajo la clave `payload` (campos `messageId`, `message`, `sender`, `simNumber`); el servicio lo desempaqueta, deduplica por `messageId` y persiste el mensaje. Como el board tiene una sola ranura física activa a la vez, el SMS entrante se estampa con el **slot activo del board** (guardado en `system_config`), no con el `simNumber` del teléfono.
- **Envío:** el dashboard envía vía el endpoint `/message` del gateway. El envío se hace en modo **automático** (sin especificar SIM al gateway), porque el board expone una única ranura física al teléfono; pedir una SIM por número que el teléfono no conoce produce `GENERIC_FAILURE`.
- **Estado de entrega:** los webhooks `sms:sent` / `sms:delivered` / `sms:failed` apuntan a `/dashboard/sms/webhook/status` y actualizan el estado de los mensajes salientes (mapeo `event` → estado, match por `messageId`).
- **Gestión de SIMs:** las 20 ranuras del board se administran desde `/dashboard/sms/sims` (etiqueta, número, operador, país, color, notas). El "slot activo" se persiste como preferencia en `system_config`.
- **Notificaciones:** polling ligero desde el navegador (`/api/unread` cada 15 s, `/api/health` cada 30 s) en lugar de SSE, porque el estado en memoria no es compatible con los 3 workers de Gunicorn en producción.

> ⚠️ **Limitación de hardware actual:** el board usa switches deslizantes mecánicos, por lo que el cambio físico de SIM activa es **manual y presencial** (mover el switch). El dashboard solo registra cuál SIM se considera activa. La rotación remota de SIM requiere otro hardware (módems individuales por SIM, o un SIM bank con control por software) — ver [Pendientes por Módulo](#-pendientes-por-módulo).

### 🤖 Bot Conversacional Multicanal
Bot de conversación con máquina de estados que opera en Telegram, Web y WhatsApp (patrón Strategy). Maneja consultas de cotizaciones, inicio de órdenes y seguimiento.

### 📋 Sistema de Órdenes
Gestión completa del ciclo de vida de órdenes de compra/venta: creación, asignación a operador, procesamiento, comprobantes de pago y completado.

### 🚫 Blacklist y Verificación de Fraude
Sistema de reportes de usuarios fraudulentos con:
- Bloqueo por user_id, telegram_id, teléfono, email o DNI
- Bloqueo preventivo (sin cuenta registrada)
- Apelaciones desde formulario público
- Verificación automática de fraude al crear órdenes
- Estadísticas por categoría y severidad

### 📊 Contabilidad Automática
Registro de transacciones con precisión `Decimal` (nunca `float`). Genera reportes de:
- Balance por período (ingresos, comisiones, gastos)
- Distribución de ganancias por método de pago
- Distribución de órdenes por moneda
- Comparativa hoy vs ayer
- Serie temporal de fees diarios

---
## 🏗️ Arquitectura

### Capas (estricto)

```
┌─────────────────────────────────────┐
│   TEMPLATES  (Jinja2 — solo HTML)   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   ROUTES  (Blueprints — orquesta)   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   SERVICES  (toda la lógica)        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   MODELS  (SQLAlchemy — datos)      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   DATABASE  (PostgreSQL 17)         │
└─────────────────────────────────────┘
```

**Reglas:**
- Routes nunca llaman directamente a Models — siempre vía Services
- Templates sin lógica Python — solo presentación Jinja2
- Services concentran toda la lógica de negocio
- Funciones ≤ 60 líneas de lógica; excepciones específicas (nunca `except: pass`)
- CSS adaptativo solo vía variables; sin Bootstrap junto a Tailwind

### Infraestructura

```
┌──────────────────────────────────────────────────┐
│                    INTERNET                       │
└──────────────────┬───────────────────────────────┘
                   │
          ┌────────▼────────┐
          │   Cloudflare    │
          │  (DDoS + SSL)   │
          └────────┬────────┘
                   │
   ┌───────────────▼──────────────────────────┐
   │        Cloudflare Tunnel                 │
   │  ceiba21.com          → Flask :5000      │
   │  monitor.ceiba21.com  → Netdata :19999   │
   │  temp.ceiba21.com     → Dashboard :8080  │
   │  ssh.ceiba21.com      → SSH :22          │
   └───────────────┬──────────────────────────┘
                   │
     ┌─────────────▼──────────────┐
     │   Raspberry Pi 5 (ARM64)   │
     │   4 cores · 8GB RAM        │
     │   2TB NVMe · Debian 13     │
     └──────┬──────┬──────┬───────┘
            │      │      │
       ┌────▼──┐ ┌─▼───┐ ┌▼──────┐
       │Flask  │ │PG17 │ │Nginx  │
       │Gunicorn│ │     │ │Proxy  │
       └───────┘ └─────┘ └───────┘
```

### Mensajería SMS (flujo)

```
┌──────────────┐   webhook    ┌────────────────────────┐
│  Teléfono    │  sms:received│   Ceiba21 / Flask      │
│  Android     │─────────────▶│  /dashboard/sms/       │
│ (SMS Gateway)│              │     webhook/incoming   │
│              │◀─────────────│  /message (envío)      │
└──────┬───────┘   POST envío └────────────┬───────────┘
       │ cable FPC                         │
┌──────▼───────┐                  ┌────────▼───────────┐
│ Board 20 SIM │                  │  PostgreSQL        │
│ (1 activa)   │                  │  sms_messages      │
└──────────────┘                  │  sms_sim_slots     │
                                  └────────────────────┘
```

---

## 🛠️ Stack Tecnológico

### Backend

| Paquete | Versión | Uso |
|---|---|---|
| Python | 3.13 | Lenguaje principal |
| Flask | 3.1.2 | Framework web |
| SQLAlchemy | 2.0.44 | ORM |
| Flask-SQLAlchemy | 3.1.1 | Integración Flask↔SQLAlchemy |
| Flask-Login | 0.6.3 | Autenticación de sesión |
| Flask-Caching | 2.1.0 | Caché con Redis |
| Flask-Session | 0.8.0 | Sesiones del lado servidor |
| Gunicorn | 23.0.0 | WSGI server |
| psycopg2-binary | 2.9.11 | Driver PostgreSQL |
| redis | 5.0.1 | Caché y sesiones |
| APScheduler | 3.10.4 | Scheduler (ingesta en dev) |
| requests | 2.32.5 | HTTP client (gateway SMS, APIs) |
| python-dotenv | 1.2.1 | Variables de entorno |

### Telegram e Imágenes

| Paquete | Versión | Uso |
|---|---|---|
| python-telegram-bot | 22.5 | SDK Telegram |
| Pillow | 12.0.0 | Generación de imágenes |
| CairoSVG | 2.8.2 | Renderizado SVG |
| cairocffi | 1.7.1 | Bindings libcairo |

### PayPal / Gmail

| Paquete | Versión | Uso |
|---|---|---|
| beautifulsoup4 | 4.12.3 | Parseo HTML correos PayPal |
| httpx | 0.27.0 | HTTP client async |

### Frontend

| Tecnología | Uso |
|---|---|
| Tailwind CSS 3.x (CDN) | Framework CSS |
| Font Awesome 6.4 | Iconografía |
| Vanilla JS (ES6+) | Interactividad |
| Jinja2 3.1.6 | Motor de templates |
| CSS Custom Properties | Sistema de temas (claro/oscuro) |

### Testing

| Paquete | Versión | Uso |
|---|---|---|
| pytest | 9.0.3 | Framework de tests (58 tests) |
| pytest-flask | 1.3.0 | Fixtures Flask |

### Infraestructura

| Tecnología | Uso |
|---|---|
| Raspberry Pi 5 (ARM64) | Hardware — 4 cores, 8GB RAM, 2TB NVMe |
| Debian 13 Trixie | Sistema operativo |
| PostgreSQL 17 | Base de datos principal |
| Redis | Caché de sesiones y queries |
| Nginx | Reverse proxy |
| Cloudflare Tunnel | Acceso público sin exponer puertos |
| Systemd | Gestión del servicio Flask |
| Netdata | Monitoreo del sistema |
| SMS Gateway for Android | Gateway de SMS (teléfono dedicado, modo Local Server) |

---

## 📁 Estructura del Proyecto

```
ceiba21-cotizaciones/
│
├── .clinerules              # Reglas de codificación para asistentes de IA
├── .clineignore             # Archivos bloqueados para asistentes de IA
├── .env.example             # Plantilla de variables de entorno
├── .gitignore
├── README.md
├── requirements.txt         # Dependencias Python
├── wsgi.py                  # Entry point Gunicorn
├── start_bot.py             # Iniciar bot conversacional de Telegram
│
├── app/
│   ├── __init__.py          # Factory pattern — create_app()
│   ├── config.py            # Configuración dev/prod
│   ├── decorators.py        # Control de acceso por rol (require_roles)
│   │
│   ├── models/              # SQLAlchemy — solo estructura de datos
│   │   ├── base.py          # BaseModel con timestamps y save()
│   │   ├── currency.py      # Monedas (VES, USD, COP, BRL, MXN…)
│   │   ├── exchange_rate.py # Tasas entre pares de monedas
│   │   ├── payment_method.py# Métodos de pago (PayPal, Zelle, USDT…)
│   │   ├── quote.py         # Cotizaciones con fórmulas programables
│   │   ├── quote_history.py # Historial de cambios
│   │   ├── operator.py      # Operadores del dashboard (roles: admin/operator/viewer)
│   │   ├── order.py         # Órdenes de compra/venta
│   │   ├── transaction.py   # Transacciones completadas
│   │   ├── user.py          # Usuarios del bot conversacional
│   │   ├── web_user.py      # Usuarios del dashboard web
│   │   ├── message.py       # Mensajes del bot
│   │   ├── paypal_payment.py# (legacy) Pagos PayPal — reemplazado por payment.py
│   │   ├── payment.py        # Pagos unificados multi-método (tabla `payments`)
│   │   ├── payment_source.py # Fuentes de ingesta (remitente → método)
│   │   ├── system_config.py  # Configuración key-value (margen, slot SIM activo, etc.)
│   │   ├── blacklist.py     # Reportes y apelaciones de blacklist
│   │   ├── sim_slot.py       # Slots SIM del board multi-SIM (tabla `sms_sim_slots`)
│   │   └── sms_message.py    # Mensajes SMS entrantes/salientes (tabla `sms_messages`)
│   │
│   ├── routes/              # Blueprints Flask — solo orquestación
│   │   ├── auth.py          # Login / logout
│   │   ├── dashboard.py     # Panel administrativo CRUD + conversor + config margen
│   │   ├── main.py          # API REST pública
│   │   ├── public.py        # Páginas públicas (home, calculadora, API /api/calcular)
│   │   ├── operator_dashboard.py  # Dashboard de operadores
│   │   ├── blacklist.py     # CRUD de blacklist
│   │   ├── payments_unified.py # Dashboard de pagos unificado (/dashboard/pagos)
│   │   ├── bot_control.py   # Control del bot conversacional
│   │   └── sms.py            # Módulo SMS (/dashboard/sms) + webhooks
│   │
│   ├── services/            # Lógica de negocio — toda aquí
│   │   ├── base_service.py
│   │   ├── quote_service.py
│   │   ├── exchange_rate_service.py
│   │   ├── currency_service.py
│   │   ├── payment_method_service.py
│   │   ├── operator_service.py
│   │   ├── order_service.py
│   │   ├── user_service.py
│   │   ├── auth_service.py
│   │   ├── blacklist_service.py
│   │   ├── accounting_service.py
│   │   ├── calculator_service.py     # Cálculos PayPal + conversor público
│   │   ├── system_config_service.py  # Lectura/escritura tipada de system_config
│   │   ├── gmail_service.py          # Lectura IMAP de Gmail
│   │   ├── paypal_parser_service.py  # Parseo HTML de correos PayPal
│   │   ├── api_service.py            # APIs externas (BCV, Binance)
│   │   ├── image_service.py
│   │   ├── notification_service.py
│   │   ├── fraud_check_service.py
│   │   ├── cache_service.py
│   │   ├── bot_service.py
│   │   └── sms_service.py            # Gateway HTTP, envío/ingesta SMS, slots SIM
│   │
│   ├── bot/                 # Bot conversacional multicanal
│   │   ├── conversation_handler.py
│   │   ├── message_parser.py
│   │   ├── responses.py
│   │   └── states.py
│   │
│   ├── channels/            # Canales de comunicación (patrón Strategy)
│   │   ├── base_channel.py
│   │   ├── telegram_channel.py
│   │   ├── webchat_channel.py
│   │   └── whatsapp_channel.py
│   │
│   ├── telegram/            # Integración Telegram
│   │   ├── bot.py                # Publisher (publica cotizaciones)
│   │   ├── bot_conversational.py # Bot interactivo
│   │   ├── formatters.py
│   │   └── image_generator.py    # Genera imágenes con Pillow/CairoSVG
│   │
│   ├── templates/           # Jinja2 — sin lógica Python
│   │   ├── base.html
│   │   ├── public_base.html
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── operator/
│   │   ├── blacklist/
│   │   ├── payments/
│   │   ├── public/
│   │   └── sms/                  # Vistas del módulo SMS
│   │       ├── index.html        # Dashboard SMS
│   │       ├── send.html         # Enviar SMS
│   │       ├── inbox.html        # Bandeja de entrada
│   │       ├── history.html      # Historial de enviados
│   │       ├── sims.html         # Gestión de slots SIM
│   │       ├── _status_badge.html
│   │       ├── _pagination.html
│   │       └── _breadcrumb.html
│   │
│   ├── static/
│   │   ├── css/style.css    # Variables CSS, tema claro/oscuro
│   │   ├── js/
│   │   └── img/
│   │
│   ├── utils/               # Utilidades reutilizables
│   │   ├── __init__.py
│   │   ├── formato.py        # Filtro formato_eu (1.234,56)
│   │   └── fecha.py          # Filtro hora_co (UTC → America/Bogota)
│   │
│   └── tests/               # 58 tests
│       ├── conftest.py
│       ├── test_models.py
│       ├── test_routes.py
│       ├── test_calculator.py
│       ├── test_parsers.py
│       └── test_payment_model.py
│
├── docs/                    # Documentación técnica de decisiones
│   ├── ESTRUCTURA_PROYECTO.md
│   ├── DEPLOY_GUIDE.md
│   ├── PLAN_SISTEMA_ORDENES.md
│   ├── BLACKLIST_IMPLEMENTATION.md
│   └── …
│
└── scripts/                 # Migraciones y utilidades
    ├── create_tables.py
    ├── seed_data.py
    ├── seed_payment_sources.py       # Siembra fuentes de pago (idempotente)
    ├── seed_usd_currency.py          # Agrega USD como moneda pivote activa
    ├── run_ingesta.py                # Ingesta one-shot para cron (producción)
    ├── importar_historico.py         # Importación histórica masiva (CLI, sin timeout)
    ├── migrate_paypal_to_payments.py # Migración legacy → tabla unificada
    ├── init_sms.py                   # Crea tablas SMS y siembra 20 slots (idempotente)
    ├── health_check.py
    └── safe_restart.sh
```

---
## 📦 Requisitos

### Hardware
- **Raspberry Pi 5** — 4GB RAM mínimo, 8GB recomendado
- **Almacenamiento** — NVMe 256GB+
- **Conectividad** — Ethernet estable
- **(Opcional, módulo SMS)** Teléfono Android con la app SMS Gateway + board multi-SIM

### Software
- Debian 13 Trixie (64-bit)
- Python 3.13+
- PostgreSQL 17+
- Redis 7+
- Nginx

---

## 🚀 Instalación

### 1. Preparar el sistema
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-full python3-pip python3-venv \
    postgresql-17 nginx redis-server git curl bc jq
```

### 2. Configurar PostgreSQL
```bash
sudo -u postgres psql << EOF
CREATE USER webmaster WITH PASSWORD 'tu_password_segura';
CREATE DATABASE cotizaciones_db OWNER webmaster;
GRANT ALL PRIVILEGES ON DATABASE cotizaciones_db TO webmaster;
\c cotizaciones_db
GRANT ALL ON SCHEMA public TO webmaster;
EOF
```

### 3. Clonar y configurar entorno
```bash
sudo useradd -m -s /bin/bash webmaster
sudo usermod -aG sudo,www-data webmaster
sudo -u webmaster -i

cd /var/www
git clone <URL_REPOSITORIO> cotizaciones
cd cotizaciones

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Variables de entorno
```bash
cp .env.example .env
nano .env
```

```env
# Flask
SECRET_KEY=clave-secreta-segura-minimo-32-caracteres
FLASK_ENV=production

# Database
DATABASE_URL=postgresql://webmaster:password@localhost/cotizaciones_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHANNEL_ID=@tu_canal

# Gmail IMAP (para ingesta de pagos)
GMAIL_IMAP_USER=tu_cuenta@gmail.com
GMAIL_IMAP_PASSWORD=app_password_de_google

# Módulo SMS (gateway Android) — opcional
SMS_GATEWAY_IP=192.168.20.16
SMS_GATEWAY_PORT=8080
SMS_GATEWAY_USER=sms
SMS_GATEWAY_PASSWORD=app_password_del_gateway

# Moneda local por defecto
DEFAULT_LOCAL_CURRENCY=VES

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password_hasheada
```

> ⚠️ En producción `FLASK_ENV` **debe** ser `production` para que el `APScheduler` embebido no compita con el cron de ingesta. Dev y prod divergen: audita el `.env` al agregar integraciones nuevas (la ausencia de credenciales GMAIL_IMAP en prod causó un 500 en su momento).

### 5. Inicializar base de datos
```bash
source venv/bin/activate
python scripts/create_tables.py
python scripts/seed_data.py    # Datos iniciales opcionales
python scripts/init_sms.py     # Tablas SMS + 20 slots (si se usa el módulo SMS)
```

### 6. Configurar Systemd
```bash
sudo nano /etc/systemd/system/ceiba21.service
```

```ini
[Unit]
Description=Ceiba21 Flask Application
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=webmaster
WorkingDirectory=/var/www/cotizaciones
Environment="PATH=/var/www/cotizaciones/venv/bin"
ExecStart=/var/www/cotizaciones/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    wsgi:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable ceiba21
sudo systemctl start ceiba21
```

### 7. Configurar Cloudflare Tunnel
```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb \
    -o cloudflared.deb
sudo dpkg -i cloudflared.deb

cloudflared tunnel login
cloudflared tunnel create ceiba21
sudo nano /etc/cloudflared/config.yml
```

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: ceiba21.com
    service: http://localhost:5000
  - hostname: monitor.ceiba21.com
    service: http://localhost:19999
  - hostname: ssh.ceiba21.com
    service: ssh://localhost:22
  - service: http_status:404
```

```bash
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

### 8. (Opcional) Configurar el gateway SMS

En la app SMS Gateway del teléfono (modo Local Server), reservar la IP del teléfono por DHCP (por MAC) para que no cambie, y registrar los webhooks vía API:

```bash
# Webhook de recepción
curl -X POST -u sms:PASSWORD \
  -H "Content-Type: application/json" \
  -d '{"url": "https://ceiba21.com/dashboard/sms/webhook/incoming", "event": "sms:received"}' \
  http://IP_TELEFONO:8080/webhooks

# Webhooks de estado (uno por evento)
for ev in sms:sent sms:delivered sms:failed; do
  curl -X POST -u sms:PASSWORD \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"https://ceiba21.com/dashboard/sms/webhook/status\", \"event\": \"$ev\"}" \
    http://IP_TELEFONO:8080/webhooks
done
```

---

## ⚙️ Configuración

### Firewall
```bash
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw allow 19999/tcp comment 'Netdata'
sudo ufw enable
```

### Netdata
```bash
curl https://get.netdata.cloud/kickstart.sh > /tmp/netdata-kickstart.sh
sh /tmp/netdata-kickstart.sh
```

---

## 💻 Desarrollo Local

### Requisitos
- Windows + VSCode
- Python 3.13 en PATH
- PostgreSQL 17 local (base: `ceiba21_dev`)
- Redis como servicio Windows

### Setup
```powershell
# Clonar y configurar
git clone https://github.com/josemoramoron/ceiba21-cotizaciones
cd ceiba21-cotizaciones

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

Crear `.env` apuntando a la base local:
```env
DATABASE_URL=postgresql://postgres:password@localhost/ceiba21_dev
FLASK_ENV=development
REDIS_URL=redis://localhost:6379/0
```

```powershell
# Iniciar servidor local
flask run
# → http://localhost:5000
```

### Ejecutar tests
```powershell
python -m pytest app\tests\ -v
```
> Siempre con `python -m pytest` — nunca solo `pytest`.

### Verificar que la app carga
```powershell
python -c "from app import create_app; app = create_app(); print('OK')"
```

---

## 🚢 Flujo de Deploy

El deploy es un proceso de un solo comando desde la máquina de desarrollo:

```powershell
# 1. Commit de los cambios
git add -A
git commit -m "descripción clara del cambio"

# 2. Push al repositorio
git push origin master

# 3. Deploy al Raspberry Pi (via SSH + deploy.sh)
ssh ceiba21-local-webmaster "/var/www/cotizaciones/deploy.sh"
```

**Lo que hace `deploy.sh`:**
1. `git pull` desde GitHub
2. `pip install -r requirements.txt` (solo instala lo nuevo)
3. `systemctl restart ceiba21`

**SSH aliases configurados:**
- `ceiba21-local-webmaster` → `192.168.20.13` (red local)
- `ceiba21-tunnel` → vía Cloudflare Tunnel (acceso remoto, p. ej. desde hotspot móvil)

> ⚠️ **Nunca** modificar archivos directamente en el Raspberry Pi.

---
## 🔌 API

### Endpoints Públicos

#### `GET /api/quotes`
Todas las cotizaciones activas.
```bash
curl https://ceiba21.com/api/quotes
```
```json
{
  "VES": [
    {"method": "PayPal", "rate": 296.25},
    {"method": "Zelle", "rate": 307.43}
  ],
  "COP": [
    {"method": "PayPal", "rate": 4120.00}
  ]
}
```

#### `GET /api/quotes/<currency>`
Cotizaciones de una moneda específica.
```bash
curl https://ceiba21.com/api/quotes/VES
```

#### `POST /api/calcular`
Calculadora pública: conversión fiat↔fiat o método→fiat. Aplica el margen global a las conversiones fiat↔fiat.
```bash
curl -X POST https://ceiba21.com/api/calcular \
  -H "Content-Type: application/json" \
  -d '{"tengo":"USD","quiero":"COP","monto":100,"tipo":"fiat_to_fiat"}'
```
```json
{
  "tengo": "USD", "quiero": "COP", "monto": 100,
  "tasa_ref": 4200.0, "tasa_efectiva": 4000.0,
  "margen": 5, "resultado": 400000.0, "tipo": "fiat_to_fiat"
}
```

### Endpoints del Dashboard (requieren autenticación)

| Método | Ruta | Descripción |
|---|---|---|
| `PUT` | `/dashboard/api/quote/<id>` | Actualizar cotización |
| `POST` | `/dashboard/api/recalculate` | Recalcular todas las cotizaciones |
| `POST` | `/dashboard/api/fetch-rate/<currency>` | Obtener tasa desde API externa |
| `GET` | `/dashboard/api/test-providers` | Probar proveedores de tasas |
| `POST` | `/dashboard/api/convertir` | Convertir entre monedas (conversor interno) |
| `GET` | `/dashboard/api/config/margen-calculadora` | Leer margen de la calculadora pública |
| `POST` | `/dashboard/api/config/margen-calculadora` | Guardar margen de la calculadora pública |

### Endpoints de Pagos (requieren autenticación)

Blueprint unificado con prefijo `/dashboard/pagos`.

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/dashboard/pagos/api/ingestar` | Disparar ingesta manual de Gmail |
| `POST` | `/dashboard/pagos/api/calcular/<id>` | Calcular cotización de un pago |
| `POST` | `/dashboard/pagos/api/editar/<id>` | Editar un pago |
| `POST` | `/dashboard/pagos/api/calcular-manual` | Previsualizar un pago manual |
| `GET` | `/dashboard/pagos/api/resumen` | Resumen de pagos por estado/método |
| `GET` | `/dashboard/pagos/api/test-gmail` | Verificar conexión IMAP |
| `GET` | `/dashboard/pagos/api/scheduler/estado` | Estado del scheduler de ingesta |
| `POST` | `/dashboard/pagos/api/scheduler/pausar` | Pausar ingesta automática (dev) |
| `POST` | `/dashboard/pagos/api/scheduler/reanudar` | Reanudar ingesta automática (dev) |
| `POST` | `/dashboard/pagos/api/importar_desde` | Importar pagos desde una fecha |

### Endpoints de SMS

Blueprint con prefijo `/dashboard/sms`. Las vistas y la API requieren rol **admin**; los webhooks están exentos del guard (el gateway no tiene sesión) y su seguridad se basa en lo poco predecible de la URL y el acceso vía túnel.

**Vistas (HTML, requieren admin):**

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/dashboard/sms/` | Dashboard SMS (estado gateway, contadores, actividad) |
| `GET/POST` | `/dashboard/sms/enviar` | Formulario y envío de SMS |
| `GET` | `/dashboard/sms/inbox` | Bandeja de entrada (marca leídos) |
| `GET` | `/dashboard/sms/historial` | Historial de enviados |
| `GET` | `/dashboard/sms/sims` | Gestión de slots SIM |
| `POST` | `/dashboard/sms/sims/<slot>/editar` | Editar metadata de un slot |

**API JSON (requieren admin):**

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/dashboard/sms/api/sims/<slot>/activar` | Fijar el slot SIM activo (preferencia) |
| `GET` | `/dashboard/sms/api/unread` | Contador de no leídos (polling) |
| `GET` | `/dashboard/sms/api/health` | Estado del gateway Android (polling) |

**Webhooks (llamados por la app del teléfono, sin sesión):**

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/dashboard/sms/webhook/incoming` | Recibe SMS entrantes (`sms:received`) |
| `POST` | `/dashboard/sms/webhook/status` | Estado de entrega (`sms:sent`/`delivered`/`failed`) |

---

## 🛠️ Mantenimiento

### Backups
```bash
# Ubicación
/var/backups/ceiba21/database/

# Restaurar
zcat backup.sql.gz | psql -U webmaster -d cotizaciones_db

# Ver últimos backups
ls -lht /var/backups/ceiba21/database/ | head -5
```

### Scripts de sistema
```bash
~/verificar_sistema.sh
~/verificar_temperatura.sh
~/backup_database.sh
~/rotar_logs.sh
~/limpiar_imagenes_telegram.sh
~/monitor_servicios.sh
```

### Cron jobs
```
*/5  * * * *    Ingesta de pagos (run_ingesta.py vía ceiba21_ingesta.sh)
*/15 * * * *    Monitor de servicios críticos
*/30 * * * *    Alerta de temperatura CPU (umbral: 75°C)
06:00 diario    Monitor de espacio en disco (umbral: 80%)
02:00 diario    Backup de PostgreSQL
03:00 diario    Rotación de logs
08:00 lunes     Reporte semanal de estado
```

### Alertas por email

El sistema envía alertas automáticas por email (Postfix + Gmail SMTP) ante:
- Servicio caído (ceiba21, postgresql, nginx, cloudflared, netdata)
- Temperatura CPU > 75°C
- Disco > 80% de uso
- Backup fallido

Cada alerta incluye temperatura, CPU, RAM, disco, uptime y links a dashboards.

---

## 📊 Monitoreo

| Dashboard | URL | Descripción |
|---|---|---|
| Aplicación | https://ceiba21.com | Cotizaciones públicas |
| Calculadora | https://ceiba21.com/calculadora | Calculadora PayPal + conversor |
| Admin | https://ceiba21.com/dashboard | Panel administrativo |
| Pagos | https://ceiba21.com/dashboard/pagos | Dashboard de pagos unificado |
| SMS | https://ceiba21.com/dashboard/sms | Mensajería SMS |
| Netdata | https://monitor.ceiba21.com | Métricas del sistema en tiempo real |
| Temperatura | https://temp.ceiba21.com | CPU y NVMe (actualización 3s) |

### Logs
```bash
# Aplicación Flask
journalctl -u ceiba21 -f

# PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-17-main.log

# Alertas enviadas
cat ~/logs/alertas.log

# Nginx
sudo tail -f /var/log/nginx/error.log
```

---

## 🔧 Troubleshooting

### La aplicación no arranca
```bash
sudo journalctl -u ceiba21 -n 50
sudo systemctl status ceiba21
sudo systemctl restart ceiba21
```

### Base de datos no conecta
```bash
sudo systemctl status postgresql
psql -U webmaster -d cotizaciones_db -h localhost
sudo tail -f /var/log/postgresql/postgresql-17-main.log
```

### Cloudflare Tunnel desconectado
```bash
sudo systemctl status cloudflared
sudo journalctl -u cloudflared -f
sudo systemctl restart cloudflared
cloudflared tunnel info ceiba21
```

### Redis no disponible
```bash
sudo systemctl status redis
redis-cli ping
sudo systemctl restart redis
```

### Ingesta de pagos no funciona
```bash
# Probar conexión IMAP desde el dashboard
curl -X GET https://ceiba21.com/dashboard/pagos/api/test-gmail \
  -H "Cookie: session=..."

# Verificar que el cron de ingesta esté activo y revisar su log
crontab -l | grep ingesta
tail -f ~/logs/ingesta.log

# Forzar una corrida manual
python scripts/run_ingesta.py
```

> ⚠️ En producción `FLASK_ENV` debe ser `production` para que el `APScheduler`
> embebido no compita con el cron. Verifica con `grep FLASK_ENV .env`.

### SMS no se reciben
```bash
# Verificar que el gateway está online desde el dashboard
curl https://ceiba21.com/dashboard/sms/api/health -H "Cookie: session=..."

# Verificar webhooks registrados en el gateway (desde un equipo en la LAN)
curl -X GET -u sms:PASSWORD http://IP_TELEFONO:8080/webhooks

# Ver lo que se guardó
sudo -u postgres psql -d cotizaciones_db \
  -c "SELECT id, phone, text, gateway_id, sim_slot, created_at \
      FROM sms_messages WHERE direction='inbound' \
      ORDER BY created_at DESC LIMIT 5;"
```
Si el remitente llega como `desconocido` o el texto vacío: el payload del webhook viene anidado bajo `payload` con los campos `sender`/`message`/`messageId`. El servicio ya lo desempaqueta; mensajes viejos previos a esa corrección pueden mostrar el formato antiguo.

### SMS no se envían (quedan en Pending → Failed)
```bash
# Probar envío directo al gateway, sin pasar por Ceiba21 (desde la LAN)
curl -X POST -u sms:PASSWORD \
  -H "Content-Type: application/json" \
  -d '{"textMessage": {"text": "prueba"}, "phoneNumbers": ["+57300..."]}' \
  http://IP_TELEFONO:8080/message

# Consultar el estado del mensaje devuelto
curl -X GET -u sms:PASSWORD http://IP_TELEFONO:8080/message/<ID>
```
Causas comunes de `RESULT_ERROR_GENERIC_FAILURE`:
1. La SIM activa no tiene saldo / plan de SMS (recibir es gratis, enviar consume saldo).
2. La SIM no está bien registrada en la red (señal o contacto del FPC).
3. Se especificó una SIM por número que el teléfono no conoce — **el envío debe ir en modo automático**, ya que el board expone una sola ranura física.

### Tests fallan al correr
```bash
# Asegurarse de usar el comando correcto
python -m pytest app\tests\ -v

# Verificar que la BD de desarrollo existe
psql -U postgres -c "\l" | grep ceiba21_dev
```

---
## 📌 Pendientes por Módulo

Índice del estado real de cada módulo: lo que está hecho y lo que falta. Sirve como mapa de trabajo para retomar cualquier área.

### 💱 Cotizaciones
- ✅ CRUD de monedas y métodos, modos manual/fórmula, recálculo automático
- ✅ Visibilidad pública por frozenset (REF oculto, USD oculto en `/cotizaciones`)
- ⬜ Gráficos de histórico de cotizaciones (Chart.js, tendencias por período)
- ⬜ Exportar cotizaciones a PDF
- ⬜ Alertas cuando una tasa cambia más de X%

### 📱 Publicación en Telegram
- ✅ Generación de imágenes (Pillow/CairoSVG), publicación VES/COP, timeout split
- ⬜ Bot que notifica cambios críticos de tasa y caída de servicios en Telegram

### 💳 Ingesta de Pagos Unificada
- ✅ Tabla `payments` unificada, `PaymentSource` configurable desde dashboard
- ✅ Ingesta vía cron one-shot, importación histórica masiva, columna DESTINATARIO (Zelle)
- ✅ Soporta PayPal (F&F/G&S), Zelle, USDT/cripto
- ⬜ Fases restantes: transferencias bancarias, integración con órdenes, notificaciones push
- ⬜ Más parsers según se agreguen métodos

### 🧮 Calculadora Pública
- ✅ PayPal (recibir/enviar) + Conversor Fiat (fiat↔fiat y método→fiat)
- ✅ Margen global configurable, USD como moneda en selectores
- ⬜ Conversiones método↔método y fiat→método
- ⬜ Panel de analytics con estadísticas de uso de la calculadora

### 📲 Mensajería SMS
- ✅ Recepción vía webhook (payload anidado, dedupe por `messageId`)
- ✅ Envío en modo automático, historial, inbox, hora local CO, migas de pan
- ✅ Identificación de la SIM receptora (estampa el slot activo del board)
- ✅ Webhooks de estado de entrega (`sent`/`delivered`/`failed`)
- ✅ Gestión de 20 slots SIM con metadata y color
- ⬜ **Rotación remota de SIM** — bloqueada por el hardware actual (switches deslizantes mecánicos que no se mueven por software). Requiere uno de estos caminos:
  - Módems individuales por SIM (ESP32 + SIM800L/SIM7000G/SIM7670G), comandos AT — para 2-4 SIMs
  - SIM bank comercial + módem pool con control por API — para 10-20+ SIMs
  - Rediseño del board con chip multiplexor ISO-7816 controlado por GPIO — proyecto de electrónica
- ⬜ **Trazabilidad de SIM en envío** — actualmente el envío va siempre en automático (el board expone una sola ranura física). Cuando exista rotación real, el selector de SIM en el envío volverá a tener sentido.
- ⬜ Token de autenticación en el webhook entrante (hoy sin token; alcanzable solo vía túnel con URL poco predecible)
- ⬜ Soporte de mensajes multipart (>160 caracteres)

### 🤖 Bot Conversacional
- ✅ Máquina de estados multicanal (Telegram/Web/WhatsApp, patrón Strategy)
- ⬜ Cobertura de tests del flujo conversacional

### 📋 Sistema de Órdenes
- ✅ Ciclo de vida completo: creación, asignación, procesamiento, comprobantes, completado
- ⬜ Integración con la ingesta de pagos (conciliar pago ↔ orden automáticamente)

### 🚫 Blacklist
- ✅ Bloqueo multi-criterio, apelaciones, verificación automática, estadísticas
- ⬜ Tests unitarios de `BlacklistService`

### 📊 Contabilidad
- ✅ Reportes con precisión Decimal, balance por período, distribuciones, series temporales
- ⬜ Tests unitarios de `AccountingService`

### 🧪 Calidad / Transversal
- ✅ 58 tests (models, routes, calculator, parsers, payment model)
- ⬜ Tests unitarios para Services: `PaypalParserService`, `BlacklistService`, `AccountingService`, `GmailService`, `SmsService`
- ⬜ API REST documentada con Swagger/OpenAPI en `/api/docs`
- ⬜ **Cleanup `datetime.utcnow()`** — `BaseModel` usa `datetime.utcnow` (deprecado en Python futuro). Migrar a `datetime.now(datetime.UTC)` timezone-aware. Genera `DeprecationWarning` en los tests; no rompe nada hoy.
- ⬜ Multi-idioma (inglés, portugués)
- ⬜ **Unificación de tokens de frontend** — el amarillo de marca (`#F7D917`) y las variables de tema están duplicados en tres lugares con nombres inconsistentes (Tailwind config `ceiba-yellow`; `public_base.html` inline `:root` con `--y`/`--color-*`; `style.css` con `--color-primary`/`--color-*`). Meta: una sola fuente de verdad para los design tokens.

---

## 🗺️ Roadmap

### Completado recientemente

- ✅ **Módulo SMS integrado** — mensajería bidireccional vía gateway Android, tablas `sms_messages`/`sms_sim_slots`, webhooks de recepción y estado, gestión de 20 slots SIM, dentro de la arquitectura de Ceiba21 sin procesos ni BD extra
- ✅ **Filtro de hora local** — `hora_co` convierte UTC → America/Bogota en todas las vistas
- ✅ **Sistema de pagos unificado (multi-método)** — tabla `payments`, `PaymentSource` configurable, ingesta vía cron one-shot
- ✅ **Calculadora pública todo-en-uno** — PayPal (recibir/enviar) + Conversor Fiat
- ✅ **Margen global configurable** — `system_config` + administración desde el dashboard
- ✅ **USD como moneda en la calculadora** — además de su rol de pivote interno
- ✅ **Visibilidad por código** — REF y USD ocultos en superficies públicas sin migración de BD

### En desarrollo / Próximo

- ⬜ **Rotación remota de SIM** (módulo SMS) — pendiente de hardware adecuado
- ⬜ **Fases restantes de ingesta** — transferencias bancarias, integración con órdenes, notificaciones push
- ⬜ **Tests unitarios para Services** — cubrir parsers, blacklist, contabilidad, gmail, sms
- ⬜ **API REST documentada con Swagger/OpenAPI** — documentación interactiva en `/api/docs`
- ⬜ **Gráficos de histórico de cotizaciones** — dashboard con Chart.js
- ⬜ **Alertas en Telegram** — bot que notifica cambios críticos de tasa y caída de servicios

### Backlog

- ⬜ Conversiones método↔método y fiat→método en la calculadora pública
- ⬜ Multi-idioma (inglés, portugués)
- ⬜ Exportar cotizaciones a PDF
- ⬜ Webhooks para integración con sistemas externos
- ⬜ CDN para imágenes generadas de Telegram
- ⬜ Histórico de cotizaciones con análisis de tendencias
- ⬜ Panel de analytics con estadísticas de uso de la calculadora
- ⬜ Sistema de notificaciones cuando una tasa cambia más de X%
- ⬜ Unificación de design tokens del frontend
- ⬜ Cleanup de `datetime.utcnow()` deprecado en `BaseModel`

---

## 📚 Documentación Técnica

La carpeta `docs/` contiene documentación de decisiones de arquitectura:

| Documento | Contenido |
|---|---|
| `ESTRUCTURA_PROYECTO.md` | Árbol de directorios, descripción de capas, flujos de datos |
| `DEPLOY_GUIDE.md` | Guía detallada de deployment en Raspberry Pi |
| `PLAN_SISTEMA_ORDENES.md` | Diseño del sistema de órdenes |
| `BLACKLIST_IMPLEMENTATION.md` | Implementación del sistema de blacklist |
| `SOLUCION_ESCALABLE_FORMULAS.md` | Diseño de fórmulas programables para cotizaciones |

---

## 👥 Equipo

- **Desarrollador Principal**: Jose (Ceiba21)
- **Asistente de IA**: Claude (Anthropic) — arquitectura, revisiones de código y documentación

---

## 📄 Licencia

© 2026 Ceiba21. Todos los derechos reservados.

Software propietario y confidencial. No está permitida su distribución, modificación o uso sin autorización expresa del titular.

---

## 📞 Soporte

- **Web**: https://ceiba21.com
- **Email**: info@ceiba21.com
- **Telegram**: @ceiba21_oficial

---

**Última actualización**: Junio 2026