# 🌳 Ceiba21 — Sistema de Cotizaciones

Plataforma completa de exchange de criptomonedas y divisas construida con Flask 3.1, PostgreSQL 17 y Python 3.13. Gestiona cotizaciones, publica automáticamente en Telegram, ingesta pagos multi-método (PayPal, Zelle y los que se agreguen) en una tabla unificada, ofrece una calculadora pública con conversor de monedas, y proporciona un dashboard administrativo para operadores.

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
- [Roadmap](#-roadmap)
- [Licencia](#-licencia)

---

## 🧩 Módulos del Sistema

### 💱 Cotizaciones
CRUD completo para múltiples monedas (VES, COP, BRL, MXN, etc.) y métodos de pago (PayPal, Zelle, USDT, Wise, Binance). Soporta dos modos de valoración:
- **Manual**: valor fijo en USD
- **Fórmula**: cálculo automático basado en tasas de cambio (`BCV_VES * 1.05 + 2`)

Las cotizaciones se recalculan automáticamente cuando cambia una tasa de cambio.

### 📱 Publicación en Telegram
Genera imágenes de cotizaciones con Pillow/CairoSVG y las publica en un canal de Telegram. Soporta publicación VES y COP, imagen personalizada opcional, y mensaje adicional.

### 💳 Ingesta de Pagos Unificada (Multi-método)
Sistema de ingesta que lee correos de pago de Gmail vía IMAP y los unifica en una sola tabla `payments`, sin importar el método. Reemplaza conceptualmente al antiguo `PaypalPayment`. Cada fuente de correo (remitente y método asociado) se configura desde el dashboard mediante el modelo `PaymentSource`, de modo que agregar un nuevo método no requiere tocar código. Para cada correo:
1. Parsea el HTML con BeautifulSoup para extraer monto, comisión, tipo (G&S / F&F en PayPal), transaction ID y fecha
2. Verifica duplicados por `message_id` y `transaction_id`
3. Aplica cotización automática del método correspondiente
4. Guarda en PostgreSQL (tabla unificada `payments`)
5. Marca el correo como leído

**Ejecución programada (producción):** un script CLI one-shot `scripts/run_ingesta.py` se invoca por `cron` mediante un wrapper shell (`ceiba21_ingesta.sh`). El `APScheduler` embebido queda restringido a `FLASK_ENV=development` para evitar conflictos de múltiples schedulers entre workers de Gunicorn. Para importaciones históricas masivas (que exceden el timeout de Gunicorn) existe `scripts/importar_historico.py`, que acepta una fecha `YYYY-MM-DD` y procesa sin restricción de tiempo HTTP.

### 🧮 Calculadora Pública (Todo-en-uno)
Calculadora en `/calculadora` con dos modos en pestañas de dos niveles:
- **PayPal** (subtabs Recibir / Enviar): calcula comisiones PayPal (5,4% + $0,30 USD) en ambas direcciones, con conversión opcional a moneda local usando la cotización PayPal vigente.
- **Conversor Fiat**: convierte entre cualquier par de monedas (fiat↔fiat) y de método de pago a fiat (método→fiat), usando cotizaciones en tiempo real vía el endpoint `/api/calcular`. El botón de permutación ↔ aplica solo a pares fiat↔fiat.

Las conversiones fiat↔fiat aplican un **margen global configurable** sobre el precio de referencia (`precio_cliente = tasa_ref / (1 + margen/100)`); las conversiones método→fiat usan directamente la cotización del método (que ya incorpora su propio margen). El margen se administra desde el dashboard y se persiste en la tabla `system_config`.

USD funciona como moneda en los selectores (no solo como pivote interno), permitiendo cálculos `USD → COP`, `COP → USD`, etc.

### 🔄 Conversor de Monedas (Dashboard)
Herramienta interna en `/dashboard/conversor` que convierte entre cualquier par de monedas vía cross-rate derivado del pivote USD, con spread configurable por operación. Incluye la sección de configuración del margen de la calculadora pública.

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
| APScheduler | 3.10.4 | Scheduler (ingesta PayPal cada 5 min) |
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
| Vanilla JS (ES6+) | Interactividad |
| Jinja2 3.1.6 | Motor de templates |
| CSS Custom Properties | Sistema de temas (claro/oscuro) |

### Testing

| Paquete | Versión | Uso |
|---|---|---|
| pytest | 9.0.3 | Framework de tests |
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
├── requirements.txt         # 44 dependencias Python
├── wsgi.py                  # Entry point Gunicorn
├── start_bot.py             # Iniciar bot conversacional de Telegram
│
├── app/
│   ├── __init__.py          # Factory pattern — create_app()
│   ├── config.py            # Configuración dev/prod
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
│   │   ├── system_config.py  # Configuración key-value (margen calculadora, etc.)
│   │   └── blacklist.py     # Reportes y apelaciones de blacklist
│   │
│   ├── routes/              # Blueprints Flask — solo orquestación
│   │   ├── auth.py          # Login / logout
│   │   ├── dashboard.py     # Panel administrativo CRUD + conversor + config margen
│   │   ├── main.py          # API REST pública
│   │   ├── public.py        # Páginas públicas (home, calculadora, API /api/calcular)
│   │   ├── operator_dashboard.py  # Dashboard de operadores
│   │   ├── blacklist.py     # CRUD de blacklist
│   │   ├── payments_unified.py # Dashboard de pagos unificado (/dashboard/pagos)
│   │   └── bot_control.py   # Control del bot conversacional
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
│   │   ├── payment_ingestion_service.py # Orquesta ingesta multi-método + scheduler
│   │   ├── api_service.py            # APIs externas (BCV, Binance)
│   │   ├── image_service.py
│   │   ├── notification_service.py
│   │   ├── fraud_check_service.py
│   │   ├── cache_service.py
│   │   └── bot_service.py
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
│   │   └── public/
│   │
│   ├── static/
│   │   ├── css/style.css    # Variables CSS, tema claro/oscuro
│   │   ├── js/
│   │   └── img/
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_models.py
│       └── test_routes.py
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
    ├── health_check.py
    └── safe_restart.sh
```

---

## 📦 Requisitos

### Hardware
- **Raspberry Pi 5** — 4GB RAM mínimo, 8GB recomendado
- **Almacenamiento** — NVMe 256GB+
- **Conectividad** — Ethernet estable

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
CREATE DATABASE ceiba21_prod OWNER webmaster;
GRANT ALL PRIVILEGES ON DATABASE ceiba21_prod TO webmaster;
\c ceiba21_prod
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
DATABASE_URL=postgresql://webmaster:password@localhost/ceiba21_prod

# Redis
REDIS_URL=redis://localhost:6379/0

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHANNEL_ID=@tu_canal

# Gmail IMAP (para ingesta PayPal)
GMAIL_IMAP_USER=tu_cuenta@gmail.com
GMAIL_IMAP_PASSWORD=app_password_de_google

# Moneda local por defecto
DEFAULT_LOCAL_CURRENCY=VES

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password_hasheada
```

### 5. Inicializar base de datos
```bash
source venv/bin/activate
python scripts/create_tables.py
python scripts/seed_data.py  # Datos iniciales opcionales
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
- `ceiba21-local-webmaster` → `192.168.1.12` (red local)
- `ceiba21-webmaster` → vía Cloudflare Tunnel (acceso remoto)

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

---

## 🛠️ Mantenimiento

### Backups
```bash
# Ubicación
/var/backups/ceiba21/database/

# Restaurar
zcat backup.sql.gz | psql -U webmaster -d ceiba21_prod

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
psql -U webmaster -d ceiba21_prod -h localhost
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

# O directamente en el servidor
source venv/bin/activate
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from app.services.gmail_service import GmailService
    print(GmailService().test_connection())
"

# Verificar que el cron de ingesta esté activo y revisar su log
crontab -l | grep ingesta
tail -f ~/logs/ingesta.log

# Forzar una corrida manual
python scripts/run_ingesta.py
```

> ⚠️ En producción `FLASK_ENV` debe ser `production` para que el `APScheduler`
> embebido no compita con el cron. Verifica con `grep FLASK_ENV .env`.

### Tests fallan al correr
```bash
# Asegurarse de usar el comando correcto
python -m pytest app\tests\ -v

# Verificar que la BD de desarrollo existe
psql -U postgres -c "\l" | grep ceiba21_dev
```

---

## 🗺️ Roadmap

### Completado recientemente

- ✅ **Sistema de pagos unificado (multi-método)** — tabla `payments`, `PaymentSource` configurable, ingesta vía cron one-shot
- ✅ **Calculadora pública todo-en-uno** — PayPal (recibir/enviar) + Conversor Fiat (fiat↔fiat y método→fiat)
- ✅ **Margen global configurable** — `system_config` + administración desde el dashboard
- ✅ **USD como moneda en la calculadora** — además de su rol de pivote interno
- ✅ **Filtro de monedas activas en la matriz** — `get_quotes_matrix()` respeta `active=True` en todas las páginas

### En desarrollo

- ⬜ **Fases restantes de ingesta** — Zelle (Bank of America), transferencias bancarias, integración con órdenes, notificaciones push
- ⬜ **Tests unitarios para Services** — cubrir `PaypalParserService`, `BlacklistService`, `AccountingService`, `GmailService`
- ⬜ **API REST documentada con Swagger/OpenAPI** — documentación interactiva en `/api/docs`
- ⬜ **Gráficos de histórico de cotizaciones** — dashboard con Chart.js, tendencias por período
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