# 🌳 Sistema de Cotizaciones Ceiba21

Sistema completo de gestión de cotizaciones de divisas con publicación automatizada en Telegram, desarrollado para Raspberry Pi 5.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Flask](https://img.shields.io/badge/Flask-3.1-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791)
![License](https://img.shields.io/badge/License-Proprietary-red)

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Arquitectura](#-arquitectura)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [API](#-api)
- [Mantenimiento](#-mantenimiento)
- [Monitoreo](#-monitoreo)
- [Troubleshooting](#-troubleshooting)
- [Licencia](#-licencia)

---

## ✨ Características

### 🎯 Funcionalidades Principales

- **Gestión de Cotizaciones**: CRUD completo para múltiples monedas y métodos de pago
- **Publicación Automática**: Generación de imágenes y publicación en Telegram
- **Calculadora PayPal**: Cálculo interactivo de comisiones
- **Dashboard Administrativo**: Panel completo de administración
- **API REST**: Endpoints para consultas externas
- **Drag & Drop**: Reordenamiento visual de métodos de pago
- **Fórmulas Programables**: Cotizaciones con cálculo automático

### 📊 Monitoreo y Analytics

- **Netdata**: Monitoreo en tiempo real del sistema
- **Dashboard de Temperatura**: Visualización dedicada
- **Logs Automáticos**: Sistema de logging periódico
- **Alertas**: Notificaciones de cambios significativos

### 🔐 Seguridad

- **Cloudflare Tunnel**: Acceso seguro sin exponer puertos
- **Autenticación**: Sistema de login para panel administrativo
- **Firewall UFW**: Configuración de seguridad perimetral
- **Separación de Usuarios**: Aislamiento c21/webmaster
- **Entorno Virtual**: Dependencias aisladas

---

## 🏗️ Arquitectura
```
┌─────────────────────────────────────────────────────────┐
│                    INTERNET                             │
└─────────────────┬───────────────────────────────────────┘
                  │
         ┌────────▼────────┐
         │  Cloudflare     │
         │  (DDoS, SSL)    │
         └────────┬────────┘
                  │
         ┌────────▼─────────────────────────────────┐
         │  Cloudflare Tunnel (cloudflared)         │
         │  • ceiba21.com → Flask (5000)            │
         │  • monitor.ceiba21.com → Netdata (19999) │
         │  • temp.ceiba21.com → Dashboard (8080)   │
         │  • ssh.ceiba21.com → SSH (22)            │
         │  • vnc.ceiba21.com → VNC (5900)          │
         └────────┬─────────────────────────────────┘
                  │
    ┌─────────────▼──────────────┐
    │   Raspberry Pi 5 (ARM64)   │
    │   • 4 cores @ 2.4GHz       │
    │   • 8GB RAM                │
    │   • 2TB NVMe SSD           │
    │   • Debian 13 (Trixie)     │
    └────────────────────────────┘
         │         │         │
    ┌────▼───┐ ┌──▼────┐ ┌─▼──────┐
    │ Flask  │ │ PG 17 │ │ Nginx  │
    │ Gunicorn│ │ DB    │ │ Proxy  │
    └────────┘ └───────┘ └────────┘
```

---

## 📦 Requisitos

### Hardware

- **Raspberry Pi 5** (4GB RAM mínimo, 8GB recomendado)
- **Almacenamiento**: NVMe 256GB+ (2TB recomendado)
- **Conectividad**: Ethernet o WiFi estable

### Software Base

- **OS**: Raspberry Pi OS 64-bit (Debian 13 Trixie)
- **Python**: 3.13+
- **PostgreSQL**: 17+
- **Node.js**: No requerido (CDN usado)

---

## 🚀 Instalación

### 1. Preparación del Sistema
```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias del sistema
sudo apt install -y \
    python3-full \
    python3-pip \
    python3-venv \
    postgresql-17 \
    nginx \
    git \
    curl \
    bc \
    jq
```

### 2. Configurar PostgreSQL
```bash
# Crear usuario y base de datos
sudo -u postgres psql << EOF
CREATE USER webmaster WITH PASSWORD 'tu_password_segura';
CREATE DATABASE cotizaciones_db OWNER webmaster;
GRANT ALL PRIVILEGES ON DATABASE cotizaciones_db TO webmaster;
\c cotizaciones_db
GRANT ALL ON SCHEMA public TO webmaster;
EOF
```

### 3. Clonar Repositorio
```bash
# Crear usuario webmaster si no existe
sudo useradd -m -s /bin/bash webmaster
sudo usermod -aG sudo,www-data webmaster

# Cambiar a webmaster
sudo -u webmaster -i

# Clonar proyecto
cd /var/www
git clone <URL_REPOSITORIO> cotizaciones
cd cotizaciones
```

### 4. Configurar Entorno Virtual
```bash
# Crear venv
python3 -m venv venv

# Activar
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configurar Variables de Entorno
```bash
# Crear archivo .env
nano .env
```

**Contenido:**
```env
# Flask
SECRET_KEY=tu_clave_secreta_aqui
FLASK_ENV=production

# Database
DATABASE_URL=postgresql://webmaster:password@localhost/cotizaciones_db

# Telegram
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_CHANNEL_ID=@tu_canal

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password_hasheada
```

### 6. Inicializar Base de Datos
```bash
# Activar venv
source venv/bin/activate

# Crear tablas
python3 -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### 7. Configurar Cloudflare Tunnel
```bash
# Instalar cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# Autenticar
cloudflared tunnel login

# Crear tunnel
cloudflared tunnel create cotizaciones-rpi

# Configurar
sudo nano /etc/cloudflared/config.yml
```

**Contenido:**
```yaml
tunnel: <TUNNEL_ID>
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: ceiba21.com
    service: http://localhost:5000
  - hostname: monitor.ceiba21.com
    service: http://localhost:19999
  - hostname: temp.ceiba21.com
    service: http://localhost:8080
  - hostname: ssh.ceiba21.com
    service: ssh://localhost:22
  - hostname: vnc.ceiba21.com
    service: tcp://localhost:5900
  - service: http_status:404
```

### 8. Configurar Systemd
```bash
sudo nano /etc/systemd/system/ceiba21.service
```

**Contenido:**
```ini
[Unit]
Description=Ceiba21 Flask Application
After=network.target postgresql.service

[Service]
Type=simple
User=webmaster
WorkingDirectory=/var/www/cotizaciones
Environment="PATH=/var/www/cotizaciones/venv/bin"
ExecStart=/var/www/cotizaciones/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 --timeout 120 wsgi:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Activar servicios:**
```bash
sudo systemctl enable ceiba21
sudo systemctl enable cloudflared
sudo systemctl start ceiba21
sudo systemctl start cloudflared
```

---

## ⚙️ Configuración

### Firewall
```bash
# Configurar UFW
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw allow 5900/tcp comment 'VNC'
sudo ufw allow 8080/tcp comment 'Temperatura'
sudo ufw allow 19999/tcp comment 'Netdata'
sudo ufw enable
```

### Netdata
```bash
# Instalar
curl https://get.netdata.cloud/kickstart.sh > /tmp/netdata-kickstart.sh
sh /tmp/netdata-kickstart.sh
```

---

## 🎮 Uso

### Acceso Web

- **Aplicación Principal**: https://ceiba21.com
- **Dashboard Admin**: https://ceiba21.com/dashboard
- **Monitoreo**: https://monitor.ceiba21.com
- **Temperatura**: https://temp.ceiba21.com

### Gestión de Cotizaciones

1. **Login**: Accede al dashboard con credenciales admin
2. **Monedas**: Gestiona monedas y tasas de cambio
3. **Métodos de Pago**: Configura PayPal, Zelle, USDT, etc.
4. **Cotizaciones**: Establece valores o fórmulas automáticas
5. **Publicar**: Genera imagen y publica en Telegram

### Publicación en Telegram
```bash
# Manual desde el dashboard
https://ceiba21.com/dashboard/telegram

# Via API
curl -X POST https://ceiba21.com/api/publish \
  -H "Content-Type: application/json" \
  -d '{"currency": "VES"}'
```

---

## 📁 Estructura del Proyecto
```
cotizaciones/
├── app/
│   ├── __init__.py              # Factory pattern
│   ├── models.py                # SQLAlchemy models
│   ├── routes/
│   │   ├── main.py             # Rutas públicas
│   │   ├── dashboard.py        # Panel admin
│   │   └── auth.py             # Autenticación
│   ├── telegram/
│   │   ├── bot.py              # Publisher
│   │   └── image_generator.py  # Generador de imágenes
│   ├── templates/              # Jinja2 templates
│   ├── static/                 # CSS, JS, imágenes
│   └── utils/                  # Utilidades
├── venv/                       # Entorno virtual
├── logs/                       # Logs de aplicación
├── .env                        # Variables de entorno
├── requirements.txt            # Dependencias Python
├── wsgi.py                     # Entry point
└── README.md                   # Este archivo
```

---

## 🔌 API

### Endpoints Públicos

#### GET `/api/quotes`
Obtener todas las cotizaciones actuales
```bash
curl https://ceiba21.com/api/quotes
```

**Respuesta:**
```json
{
  "VES": [
    {"method": "PayPal", "rate": 296.25},
    {"method": "Zelle", "rate": 307.43}
  ]
}
```

#### GET `/api/quotes/:currency`
Cotizaciones de una moneda específica
```bash
curl https://ceiba21.com/api/quotes/VES
```

---

## 🛠️ Mantenimiento

### Scripts Automáticos
```bash
# Ver scripts disponibles
ls -lh ~/*.sh

# Dashboard maestro
~/dashboard_ceiba21.sh

# Verificaciones
~/verificar_sistema.sh
~/verificar_temperatura.sh
~/verificar_vnc.sh
~/verificar_red.sh

# Mantenimiento
~/backup_database.sh
~/rotar_logs.sh
~/limpiar_imagenes_telegram.sh

# Sistema de alertas
~/enviar_alerta.sh
~/monitor_servicios.sh
~/alerta_temperatura.sh
~/alerta_disco.sh
~/ver_alertas.sh
```

### Tareas Programadas (Cron)
```
# Logs automáticos
00:00 cada hora   → Monitor de temperatura
00:00 cada 6h     → Estado del sistema
00:00 diario      → Dashboard completo
00:00 domingos    → Verificación de red

# Mantenimiento
02:00 diario      → Backup de base de datos
03:00 diario      → Rotación de logs
04:00 diario      → Limpieza de imágenes antiguas
02:00 día 1 mes   → Limpieza de logs muy antiguos

# Alertas automáticas
*/15 * * * *      → Monitor de servicios críticos
*/30 * * * *      → Monitor de temperatura CPU
06:00 diario      → Monitor de espacio en disco
08:00 lunes       → Reporte semanal de estado
```

### Backups
```bash
# Ubicación de backups
/var/backups/ceiba21/database/

# Restaurar backup
zcat backup.sql.gz | psql -U webmaster -d cotizaciones_db

# Ver últimos backups
ls -lht /var/backups/ceiba21/database/ | head -5
```

---

## 📧 Sistema de Correo y Alertas

### Configuración de Email

**Recepción** (Cloudflare Email Routing):
- `info@ceiba21.com` → `ceiba21.oficial@gmail.com`
- `webmaster@ceiba21.com` → `ceiba21.oficial@gmail.com`

**Envío** (Postfix + Gmail SMTP):
- Servidor: `smtp.gmail.com:587`
- Remitente: `webmaster@ceiba21.com`
- Autenticación: `ceiba21.oficial@gmail.com`
- TLS: Habilitado

### Alertas Automáticas

El sistema envía alertas por email cuando detecta problemas:

#### **Monitor de Servicios Críticos** (cada 15 minutos)
Verifica el estado de:
- ceiba21 (Flask app)
- postgresql
- nginx
- cloudflared
- netdata

Si algún servicio está caído, envía alerta inmediata.

#### **Monitor de Temperatura** (cada 30 minutos)
- Umbral: 75°C
- Sensor: CPU Thermal
- Alerta si temperatura excede el umbral

#### **Monitor de Espacio en Disco** (diario 06:00)
- Umbral: 80% de uso
- Partición: `/` (root)
- Incluye estadísticas de espacio usado/disponible

#### **Alerta de Backup Fallido** (cuando ocurre)
- Se activa si el backup de PostgreSQL falla
- Incluye logs del error
- Permite respuesta rápida a problemas

#### **Reporte Semanal** (Lunes 08:00)
- Resumen del estado de todos los servicios
- Confirmación de que todo funciona correctamente
- Enlaces rápidos a dashboards

### Uso del Sistema de Alertas

#### Enviar alerta manual:
```bash
~/enviar_alerta.sh "Asunto" "Mensaje del cuerpo"
```

#### Ver historial de alertas:
```bash
~/ver_alertas.sh
```

#### Probar monitores manualmente:
```bash
# Servicios
~/monitor_servicios.sh

# Temperatura
~/alerta_temperatura.sh

# Disco
~/alerta_disco.sh
```

#### Ver logs:
```bash
# Historial de alertas enviadas
cat ~/logs/alertas.log

# Logs de Postfix
sudo tail -f /var/log/mail.log

# Verificar cola de correo
mailq
```

### Contenido de las Alertas

Cada alerta incluye:
- 🚨 Descripción del problema
- 📊 Estado actual del sistema:
  - Temperatura CPU
  - Uso de CPU (%)
  - Load average
  - Uso de RAM (%)
  - Uso de disco (%)
  - Uptime
- 🔗 Enlaces rápidos a dashboards
- ⏰ Timestamp de la alerta

### Configuración Avanzada

#### Cambiar umbrales:
```bash
# Editar scripts
nano ~/alerta_temperatura.sh  # Cambiar THRESHOLD=75
nano ~/alerta_disco.sh        # Cambiar THRESHOLD=80
```

#### Cambiar destinatarios:
```bash
nano ~/enviar_alerta.sh
# Modificar: DESTINATARIO="otro@email.com"
```

#### Agregar más servicios al monitor:
```bash
nano ~/monitor_servicios.sh
# Agregar a SERVICIOS=("servicio1" "servicio2" ...)
``````

---

## 📊 Monitoreo

### Netdata
- **URL**: https://monitor.ceiba21.com
- **Métricas**: CPU, RAM, Disco, Red, Temperatura
- **Retención**: 14 días por defecto

### Dashboard de Temperatura
- **URL**: https://temp.ceiba21.com
- **Actualización**: Cada 3 segundos
- **Sensores**: CPU y NVMe

### Logs
```bash
# Logs de aplicación
tail -f /var/www/cotizaciones/logs/app.log

# Logs del sistema
journalctl -u ceiba21 -f

# Logs de Netdata
journalctl -u netdata -f

# Logs automáticos
tail -f ~/logs/monitor_$(date +%Y%m%d).log
```

---

## 🔧 Troubleshooting

### La aplicación no arranca
```bash
# Ver logs
sudo journalctl -u ceiba21 -n 50

# Ver estado
sudo systemctl status ceiba21

# Reiniciar
sudo systemctl restart ceiba21
```

### Base de datos no conecta
```bash
# Verificar PostgreSQL
sudo systemctl status postgresql

# Verificar conexión
psql -U webmaster -d cotizaciones_db -h localhost

# Ver logs
sudo tail -f /var/log/postgresql/postgresql-17-main.log
```

### Cloudflare Tunnel desconectado
```bash
# Ver estado
sudo systemctl status cloudflared

# Ver logs
sudo journalctl -u cloudflared -f

# Reiniciar
sudo systemctl restart cloudflared

# Verificar conexiones
cloudflared tunnel info cotizaciones-rpi
```

### Temperatura no se actualiza
```bash
# Verificar Nginx
sudo nginx -t
sudo systemctl reload nginx

# Verificar API de Netdata
curl http://localhost:19999/api/v1/charts | jq '.charts' | grep temperature

# Limpiar caché del navegador
Ctrl + Shift + Delete
```

---

## 📚 Tecnologías Utilizadas

- **Backend**: Flask 3.1, SQLAlchemy 2.0, Gunicorn
- **Database**: PostgreSQL 17
- **Frontend**: Tailwind CSS, Vanilla JavaScript
- **Telegram**: python-telegram-bot 20.7
- **Imágenes**: Pillow 12.0, CairoSVG
- **Monitoreo**: Netdata 2.7
- **Túnel**: Cloudflare Tunnel
- **Server**: Nginx (proxy)

---

## 👥 Equipo

- **Desarrollador Principal**: Jose (Ceiba21)
- **Asistente IA**: Claude (Anthropic)

---

## 🗺️ Roadmap - Próximas Funcionalidades

### En Desarrollo

- ⬜ **Dashboard web para ver alertas**
  - Interfaz web para visualizar historial de alertas
  - Filtros por tipo, fecha y severidad
  - Estadísticas de alertas por periodo
  
- ⬜ **Integrar alertas con Telegram**
  - Bot que envía alertas críticas por Telegram
  - Comandos para consultar estado del sistema
  - Notificaciones push instantáneas
  
- ⬜ **API para consultar estado del sistema**
  - Endpoints REST para métricas en tiempo real
  - Autenticación con API keys
  - Documentación con Swagger/OpenAPI
  - Integración con herramientas de monitoreo externas
  
- ⬜ **Gráficos de histórico de alertas**
  - Visualización de tendencias de temperatura
  - Gráficos de uso de CPU/RAM/Disco
  - Reportes mensuales automatizados
  - Dashboard con Chart.js o Plotly

### Backlog

- ⬜ Multi-idioma (inglés, portugués)
- ⬜ App móvil con React Native
- ⬜ Integración con más exchanges (Binance, Kraken)
- ⬜ Sistema de notificaciones cuando tasas cambian >X%
- ⬜ Histórico de cotizaciones con análisis de tendencias
- ⬜ Panel de analytics con estadísticas de uso
- ⬜ Sistema de cache con Redis
- ⬜ CDN para imágenes de Telegram

### Ideas Futuras

- Modo oscuro en el dashboard
- Exportar cotizaciones a PDF/Excel
- Webhooks para integración con sistemas externos
- Panel de administración multi-usuario con roles
- Marketplace de plugins para extensiones

---

## 📄 Licencia

© 2025 Ceiba21. Todos los derechos reservados.

Este software es propietario y confidencial. No está permitida su distribución, modificación o uso sin autorización expresa.

---

## 📞 Soporte

- **Web**: https://ceiba21.com
- **Email**: info@ceiba21.com
- **Telegram**: @ceiba21_oficial

---

**Última actualización**: Noviembre 2025
