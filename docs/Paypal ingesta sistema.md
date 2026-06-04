# Sistema de Ingesta Automática de Pagos PayPal
**Proyecto:** Ceiba21-Cotizaciones  
**Sesión:** feat/paypal-gmail-ingesta-automatica  
**Fecha:** Junio 2026  
**Estado:** ✅ Fase 1 completada y funcionando en desarrollo local

---

## 1. Resumen Ejecutivo

Se implementó un sistema que lee automáticamente los correos de confirmación de pago de PayPal desde Gmail via IMAP, parsea los datos del HTML, calcula el valor a pagar al cliente usando las cotizaciones vigentes de Ceiba21, y los registra en PostgreSQL con un dashboard para gestión manual por parte del operador.

**Resultado:** 20-50 pagos/día que se transcribían manualmente ahora se registran automáticamente cada 5 minutos sin intervención humana.

---

## 2. Arquitectura del Sistema

### 2.1 Flujo completo

```
Gmail (ceiba21oficial@gmail.com)
    │
    │  Correos de: service@intl.paypal.com
    │  Asunto:     "Ha recibido un pago"
    │
    ▼
GmailService (IMAP SSL — imap.gmail.com:993)
    │  Lee correos NO LEÍDOS con filtro doble
    │  (remitente + asunto exacto)
    │
    ▼
PaypalParserService (BeautifulSoup4)
    │  Extrae: pagador, montos, comisión,
    │  ID transacción, fecha, tipo de pago
    │
    ▼
PaymentIngestionService (orquestador)
    │  ┌─ ¿Ya existe? → duplicado, saltar
    │  ├─ ¿Moneda USD? → calcular automático
    │  └─ ¿Otra moneda? → estado MANUAL
    │
    ▼
CalculatorService.calcular_pago_paypal_recibido()
    │  Busca cotización PayPal vigente en quotes
    │  Calcula: monto_neto × tasa = valor_a_pagar
    │
    ▼
PostgreSQL → tabla paypal_payments
    │
    ▼
Dashboard /dashboard/paypal/
    Lista + Filtros + Detalle + Edición
```

### 2.2 Scheduler automático

```python
# APScheduler corre en background al iniciar Flask
# Cada 5 minutos ejecuta:
job_ingesta() → PaymentIngestionService.procesar_nuevos_pagos()
```

---

## 3. Archivos del Sistema

### Modelos
```
app/models/paypal_payment.py
    └── PaypalPayment(BaseModel)     — tabla paypal_payments
    └── PaypalPaymentStatus          — constantes de estado
    └── PaypalPaymentType            — personal / comercial
```

### Servicios
```
app/services/gmail_service.py
    └── GmailService
        ├── get_new_paypal_payments()  — lee inbox IMAP
        ├── mark_as_read()             — marca leído tras procesar
        └── test_connection()          — health check

app/services/paypal_parser_service.py
    └── PaypalParserService
        ├── parse_email()              — extrae datos del HTML
        ├── _limpiar_monto()           — parsea "$ 20,00 USD"
        ├── _parsear_fecha()           — parsea "2 de junio de 2026"
        └── _detectar_tipo_pago()      — personal vs comercial

app/services/payment_ingestion_service.py
    └── PaymentIngestionService
        ├── procesar_nuevos_pagos()    — orquestador principal
        ├── _procesar_correo()         — procesa un correo individual
        └── obtener_resumen()          — conteos por estado
    └── inicializar_scheduler()        — registra job en APScheduler

app/services/calculator_service.py (existente, extendido)
    └── CalculatorService
        └── calcular_pago_paypal_recibido()  — NUEVO: cálculo para pagos recibidos
```

### Routes
```
app/routes/payments.py
    └── paypal_payments_bp (/dashboard/paypal)
        ├── GET  /                     — lista con filtros y paginación
        ├── GET  /<id>                 — detalle/edición
        ├── POST /api/ingestar         — dispara ingesta manual
        ├── POST /api/calcular/<id>    — calcula (con/sin persistir)
        ├── POST /api/editar/<id>      — edita estado, notas, valores
        ├── GET  /api/resumen          — conteos por estado
        └── GET  /api/test-gmail       — health check IMAP
```

### Templates
```
app/templates/payments/
    ├── list.html     — tabla pagos + stat cards + filtros + botón ingesta
    └── detail.html   — detalle + calculadora moneda + edición estado/notas
```

### Scripts
```
scripts/create_paypal_payments_table.py  — migración manual (alternativa a db.create_all)
```

---

## 4. Modelo de Datos

### Tabla `paypal_payments`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | SERIAL PK | ID interno |
| `email_message_id` | VARCHAR UNIQUE | ID Gmail — evita duplicados |
| `cuenta_destino` | VARCHAR | Gmail que recibió el correo |
| `pagador_nombre` | VARCHAR | Nombre del pagador según PayPal |
| `importe_bruto` | NUMERIC(10,2) | Monto recibido antes de comisión |
| `moneda` | VARCHAR(10) | USD, EUR, BRL, etc. |
| `comision_paypal` | NUMERIC(10,2) | Comisión PayPal (NULL si F&F) |
| `importe_neto` | NUMERIC(10,2) | Monto tras comisión (NULL si F&F) |
| `tipo_pago` | VARCHAR(20) | `personal` o `comercial` |
| `paypal_transaction_id` | VARCHAR(50) UNIQUE | ID transacción PayPal |
| `fecha_pago` | DATETIME | Fecha según el correo |
| `direccion_envio` | TEXT | Opcional en ambos tipos |
| `cotizacion_id` | FK → quotes.id | Cotización aplicada |
| `tasa_aplicada` | NUMERIC(12,4) | Snapshot histórico de la tasa |
| `valor_a_pagar` | NUMERIC(15,2) | Monto en moneda local |
| `moneda_pago_local` | VARCHAR(10) | VES, COP, BRL, etc. |
| `estado` | VARCHAR(20) | Ver estados abajo |
| `notas` | TEXT | Notas manuales del operador |
| `procesado_por` | FK → operators.id | Quién procesó |
| `created_at` | DATETIME | Timestamp automático |
| `updated_at` | DATETIME | Timestamp automático |

### Estados del pago

| Estado | Descripción | Cuándo se asigna |
|---|---|---|
| `pendiente` | Recibido, sin procesar | Ingesta automática cuando no hay cotización |
| `procesado` | Cotización aplicada | Automático si hay cotización USD vigente |
| `pagado` | Enviado al cliente | Manual por el operador |
| `revision` | Requiere revisión | Manual por el operador |
| `manual` | Moneda no USD | Automático cuando moneda ≠ USD |

### Tipos de pago PayPal

| Tipo | PayPal | Comisión | Detección |
|---|---|---|---|
| `personal` | Friends & Family | ❌ No | Sin fila "Comisión" en HTML |
| `comercial` | Goods & Services | ✅ Sí | Con fila "Comisión" en HTML |

---

## 5. Variables de Entorno Requeridas

```env
# app/.env
GMAIL_IMAP_USER=ceiba21oficial@gmail.com
GMAIL_IMAP_PASSWORD=xxxx xxxx xxxx xxxx   # App Password de Google
DEFAULT_LOCAL_CURRENCY=VES                 # Moneda local por defecto
```

```python
# app/config.py
GMAIL_IMAP_USER = os.getenv('GMAIL_IMAP_USER')
GMAIL_IMAP_PASSWORD = os.getenv('GMAIL_IMAP_PASSWORD')
DEFAULT_LOCAL_CURRENCY = os.getenv('DEFAULT_LOCAL_CURRENCY', 'VES')
```

---

## 6. Dependencias Instaladas

```
beautifulsoup4==4.14.3    # Parser HTML de correos
APScheduler==3.11.2       # Scheduler automático cada 5 min
soupsieve==2.8.4          # Dependencia de beautifulsoup4
tzlocal==5.3.1            # Dependencia de APScheduler
```

---

## 7. Correos PayPal Soportados

Se analizaron 3 correos reales de producción e identificaron las variantes:

| Variante | Moneda | Comisión | Dirección |
|---|---|---|---|
| Tipo A personal | USD | ❌ | Opcional |
| Tipo B comercial | USD | ✅ | Opcional |
| Tipo C otra moneda | EUR/BRL/etc. | Cualquiera | Opcional |

**Filtro de seguridad:** Solo se procesan correos con:
- `FROM: service@intl.paypal.com`
- `SUBJECT: Ha recibido un pago`

Esto excluye correos de publicidad, actualizaciones de políticas y notificaciones de PayPal.

---

## 8. Lógica de Cálculo

```
Pago comercial (G&S):
    monto_base = importe_neto  (ya descontada comisión PayPal)
    valor_a_pagar = monto_base × cotizacion_paypal_ves

Pago personal (F&F):
    monto_base = importe_bruto  (sin comisión)
    valor_a_pagar = monto_base × cotizacion_paypal_ves

Moneda no USD (EUR, etc.):
    estado = 'manual'
    valor_a_pagar = NULL  (operador completa manualmente)
```

La cotización se obtiene de `quotes` filtrando por:
- `payment_method.code = 'PAYPAL'`
- `currency.code = moneda_seleccionada`

---

## 9. Dashboard — Funcionalidades Implementadas

### Lista (`/dashboard/paypal/`)
- Tabla con todos los pagos ordenados por `id DESC`
- Stat cards con conteo por estado (clickeables como filtro)
- Filtros por estado: todos / pendiente / procesado / pagado / manual / revisión
- Botón "Verificar correos ahora" con spinner y toast de resultado
- Paginación (25 por página)
- Columnas: #, Pagador, Monto, Neto/Comisión, Valor a pagar, Tipo G&S/F&F, Estado, Fecha

### Detalle (`/dashboard/paypal/<id>`)
- Vista completa de todos los datos del correo
- Calculadora de moneda: desplegable → muestra valor sin guardar
- Botón "Guardar cálculo" → persiste tasa y valor
- Selector de estado con botones visuales
- Campo de notas del operador
- Campos manuales para monedas no USD
- Sección de metadatos (fechas, message ID)

---

## 10. Fases Pendientes

### Fase 2 — Mejoras del sistema de pagos

#### 2.1 Soporte para otros métodos de pago
- **Zelle:** Los correos varían por banco emisor (Chase, Bank of America, Wells Fargo). Requiere parser específico por banco o regex flexible.
- **Transferencias bancarias:** Depende del banco — algunos envían correo, otros no. Evaluar si se usa IMAP o entrada manual.
- **USDT/Crypto:** No llega por email. Requiere webhook de exchange (Binance, Kraken) o watcher de blockchain.

#### 2.2 Integración con sistema de órdenes
- Asociar cada `PaypalPayment` con una `Order` existente
- Campo `order_id FK → orders.id` en `paypal_payments`
- Flujo: pago entra → operador lo asocia a una orden pendiente → orden pasa a `completada`
- Vista en el detalle del pago con buscador de órdenes

#### 2.3 Notificaciones
- Alerta en Telegram al operador cuando entra un pago nuevo
- Usar `notification_service.py` existente
- Mensaje: pagador, monto, valor en VES calculado

#### 2.4 Búsqueda y filtros avanzados
- Filtro por rango de fechas
- Filtro por monto
- Búsqueda por nombre de pagador o ID de transacción
- Export a CSV

#### 2.5 Historial de cambios de estado
- Tabla `paypal_payment_history` que registre cada cambio de estado con timestamp y operador
- Similar a `quote_history` existente en el proyecto

### Fase 3 — Mejoras de arquitectura (.clinerules)
Ver documento `DIAGNOSTICO_CLINERULES.md` para el detalle completo.

---

## 11. Notas de Implementación

### Deduplicación
El sistema usa dos capas de protección contra duplicados:
1. `email_message_id` UNIQUE — primer filtro al buscar en IMAP
2. `paypal_transaction_id` UNIQUE — segundo filtro antes de insertar

### Correos marcados como leídos
Independientemente de si el procesamiento fue exitoso o no, el correo se marca como leído en Gmail para evitar reprocesamiento infinito en caso de error.

### Scheduler en desarrollo vs producción
El scheduler APScheduler corre en background dentro del proceso Flask. En producción con Gunicorn multi-worker puede ejecutarse múltiples veces. Solución recomendada: mover a un worker dedicado con Celery o cron del sistema operativo.

### App Password Gmail
La autenticación usa una App Password de 16 caracteres (no la contraseña normal de Google). Fue creada en noviembre 2025 y está activa. Si se revoca, regenerar en `myaccount.google.com/apppasswords`.