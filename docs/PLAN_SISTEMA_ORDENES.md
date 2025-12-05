# 📋 PLAN DE DESARROLLO: SISTEMA DE ÓRDENES CEIBA21

## 🎯 CONTEXTO ACTUAL DEL PROYECTO

### Estado actual (Completado):
- ✅ Dashboard administrativo funcionando
- ✅ Gestión de monedas, métodos de pago y cotizaciones
- ✅ Calculadora web de comisiones PayPal
- ✅ Publicación automática en canal de Telegram
- ✅ Vista pública de cotizaciones en sitio web
- ✅ Sistema de monitoreo y alertas
- ✅ Botones radiales visuales (Telegram, WhatsApp, WebChat) - **SIN FUNCIONALIDAD AÚN**

### Tecnologías actuales:
- Backend: Flask 3.1 + Python 3.13
- Base de datos: PostgreSQL 17
- ORM: SQLAlchemy 2.0
- Servidor: Raspberry Pi 5 (8GB RAM, 2TB NVMe)
- Proxy: Cloudflare Tunnel
- Monitoreo: Netdata
- Bot actual: python-telegram-bot (solo publicación de tasas)

### Ubicación del proyecto:
- Servidor: `/var/www/cotizaciones`
- Usuario: `webmaster`
- Entorno virtual: `/var/www/cotizaciones/venv`
- Repositorio: https://github.com/josemoramoron/ceiba21-cotizaciones.git

---

## 🚀 OBJETIVO GENERAL

Crear un sistema completo de gestión de órdenes de cambio de divisas donde:

1. **Clientes** pueden iniciar operaciones desde múltiples canales (Telegram, WhatsApp, WebChat)
2. **Bots** automatizados guían al cliente paso a paso hasta completar datos
3. **Operadores** atienden TODAS las órdenes desde UN SOLO dashboard web unificado
4. **Sistema** genera contabilidad automática y reportes

---

## 🏗️ ARQUITECTURA OPTIMIZADA

```
┌─────────────────────────────────────────────────┐
│         CLIENTES (Múltiples canales)            │
│  [Telegram Bot] [WhatsApp Bot] [WebChat]        │
└─────────────────┬───────────────────────────────┘
                  │ Conversaciones automatizadas
                  ↓
┌─────────────────────────────────────────────────┐
│       CAPA DE PROCESAMIENTO (Flask)             │
│  • ConversationHandler (máquina de estados)     │
│  • OrderService (lógica de órdenes)             │
│  • CalculatorService (reutilizar existente)     │
│  • NotificationService (enviar respuestas)      │
└─────────────────┬───────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────┐
│         BASE DE DATOS (PostgreSQL)              │
│  • users (clientes)                             │
│  • operators (operadores con roles)             │
│  • orders (órdenes con estados)                 │
│  • transactions (contabilidad automática)       │
│  • messages (historial completo de chats)       │
└─────────────────┬───────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────┐
│    DASHBOARD UNIFICADO (Único punto operativo)  │
│  • Vista de órdenes en tiempo real              │
│  • Chat unificado (todos los canales)           │
│  • Acciones: aprobar/rechazar/contactar         │
│  • Estadísticas y reportes                      │
│  • WebSockets para notificaciones push          │
└─────────────────────────────────────────────────┘
```

### **PRINCIPIO CLAVE: Channel-Agnostic (Independiente del canal)**

Toda la lógica de negocio NO debe saber de dónde viene el cliente. Los servicios reciben datos genéricos y funcionan igual para Telegram, WhatsApp o WebChat.

---

## 📦 ESTRUCTURA DE CÓDIGO PROPUESTA

```
app/
├── models/                    # Modelos de datos (SQLAlchemy)
│   ├── base.py               # ✨ NUEVO: Clase base con métodos comunes
│   ├── user.py               # ✨ NUEVO: Cliente (channel-agnostic)
│   ├── operator.py           # ✨ NUEVO: Operador con roles y permisos
│   ├── order.py              # ✨ NUEVO: Órdenes con máquina de estados
│   ├── transaction.py        # ✨ NUEVO: Contabilidad automática
│   ├── message.py            # ✨ NUEVO: Historial de conversaciones
│   ├── web_user.py           # ✨ NUEVO: Usuarios registrados en web
│   ├── currency.py           # ✅ EXISTENTE (mantener)
│   ├── payment_method.py     # ✅ EXISTENTE (mantener)
│   └── quote.py              # ✅ EXISTENTE (mantener)
│
├── services/                  # Lógica de negocio reutilizable
│   ├── base_service.py       # ✨ NUEVO: Clase base para servicios
│   ├── order_service.py      # ✨ NUEVO: Gestión de órdenes
│   ├── user_service.py       # ✨ NUEVO: Gestión de usuarios
│   ├── auth_service.py       # ✨ NUEVO: Autenticación y permisos
│   ├── accounting_service.py # ✨ NUEVO: Reportes contables
│   ├── calculator_service.py # 🔄 REFACTORIZAR: Hacer channel-agnostic
│   ├── notification_service.py # ✨ NUEVO: Notificaciones multi-canal
│   └── currency_service.py   # ✅ EXISTENTE (mantener)
│
├── channels/                  # ✨ NUEVO: Adaptadores por canal (Strategy Pattern)
│   ├── base_channel.py       # Interfaz abstracta
│   ├── telegram_channel.py   # Implementación Telegram
│   ├── whatsapp_channel.py   # Implementación WhatsApp (futuro)
│   └── webchat_channel.py    # Implementación WebChat
│
├── bot/                       # ✨ NUEVO: Conversación automatizada
│   ├── conversation_handler.py # Máquina de estados del bot
│   ├── message_parser.py      # Validaciones de entrada
│   └── responses.py           # Templates de respuestas
│
├── routes/
│   ├── operator.py           # ✨ NUEVO: Dashboard operadores
│   ├── auth.py               # ✨ NUEVO: Login/registro web
│   ├── api_orders.py         # ✨ NUEVO: API REST para órdenes
│   ├── webchat.py            # ✨ NUEVO: Chat en vivo web
│   ├── main.py               # ✅ EXISTENTE (mantener)
│   └── dashboard.py          # ✅ EXISTENTE (mantener admin)
│
├── templates/
│   ├── operator/             # ✨ NUEVO: Vistas de operadores
│   │   ├── dashboard.html    # Dashboard principal unificado
│   │   ├── order_detail.html # Detalle de orden con chat
│   │   └── reports.html      # Reportes y estadísticas
│   ├── auth/                 # ✨ NUEVO: Login/registro
│   │   ├── login.html
│   │   ├── register.html
│   │   └── verify_email.html
│   ├── dashboard/            # ✅ EXISTENTE (admin)
│   └── public/               # ✅ EXISTENTE
│
└── utils/
    ├── permissions.py         # ✨ NUEVO: Decoradores de permisos
    ├── state_machine.py       # ✨ NUEVO: FSM genérica
    └── enums.py              # ✨ NUEVO: Enums centralizados
```

---

## 🗄️ MODELOS DE DATOS (POO)

### **Principios de diseño:**
1. **BaseModel**: Todos los modelos heredan funcionalidad común (save, delete, to_dict)
2. **Channel-agnostic**: User model no asume canal específico
3. **Auditoría**: Timestamps automáticos en todos los modelos
4. **Relaciones claras**: FK bien definidas con cascade
5. **Métodos de negocio**: Lógica en los modelos (ej: `order.calculate_totals()`)

### **1. BaseModel (Clase madre)**

```python
class BaseModel(db.Model):
    """
    Clase abstracta base para TODOS los modelos.
    
    Proporciona:
    - id, created_at, updated_at automáticos
    - Métodos: save(), delete(), update(), to_dict()
    - find_by_id(), find_all() como métodos de clase
    """
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### **2. User (Cliente - Channel-agnostic)**

```python
class User(BaseModel):
    """
    Cliente que usa el servicio.
    
    IMPORTANTE: No asume canal específico.
    Puede tener múltiples identidades (telegram_id, whatsapp_id, etc.)
    """
    __tablename__ = 'users'
    
    # Identificadores por canal (todos nullable)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=True, index=True)
    whatsapp_id = db.Column(db.String(50), unique=True, nullable=True, index=True)
    webchat_session_id = db.Column(db.String(100), unique=True, nullable=True)
    app_user_id = db.Column(db.String(100), unique=True, nullable=True)
    
    # Información
    username = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    
    # Estado
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    
    # Estadísticas (desnormalizadas)
    total_orders = db.Column(db.Integer, default=0)
    total_volume_usd = db.Column(db.Numeric(12, 2), default=0.00)
    
    # Relaciones
    orders = db.relationship('Order', backref='user', lazy='dynamic')
    messages = db.relationship('Message', backref='user', lazy='dynamic')
    
    # Métodos clave:
    # - get_display_name()
    # - get_contact_id(channel)
    # - find_by_channel(channel, channel_id) [classmethod]
    # - create_from_channel(channel, data) [classmethod]
```

### **3. Operator (Operador con roles)**

```python
class OperatorRole(Enum):
    ADMIN = 'admin'      # Acceso total
    OPERATOR = 'operator' # Procesa órdenes
    VIEWER = 'viewer'    # Solo lectura

class Operator(BaseModel):
    """
    Operador que procesa órdenes.
    
    Sistema de permisos granular con JSON.
    """
    __tablename__ = 'operators'
    
    # Identificación
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    # Rol y permisos
    role = db.Column(db.Enum(OperatorRole), default=OperatorRole.OPERATOR)
    permissions = db.Column(db.JSON, default=dict)
    
    # Estado
    is_active = db.Column(db.Boolean, default=True)
    is_online = db.Column(db.Boolean, default=False)
    
    # Estadísticas
    orders_processed = db.Column(db.Integer, default=0)
    average_processing_time = db.Column(db.Integer, default=0)
    
    # Notificaciones
    telegram_notification_id = db.Column(db.BigInteger, nullable=True)
    
    # Relaciones
    assigned_orders = db.relationship('Order', backref='operator')
    
    # Métodos clave:
    # - set_password(password)
    # - check_password(password)
    # - has_permission(permission)
    # - get_available_operators() [classmethod]
```

### **4. Order (Orden con máquina de estados)**

```python
class OrderStatus(Enum):
    DRAFT = 'draft'           # Usuario completando datos
    PENDING = 'pending'       # Esperando verificación
    IN_PROCESS = 'in_process' # Operador procesando
    COMPLETED = 'completed'   # Completada
    CANCELLED = 'cancelled'   # Cancelada

class Order(BaseModel):
    """
    Orden de cambio de divisas.
    
    Entidad CENTRAL del negocio.
    """
    __tablename__ = 'orders'
    
    # Identificación
    reference = db.Column(db.String(20), unique=True, nullable=False, index=True)
    # Formato: ORD-YYYYMMDD-XXX
    
    # Relaciones
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    operator_id = db.Column(db.Integer, db.ForeignKey('operators.id'), nullable=True)
    
    # Datos financieros (snapshot al momento)
    amount_usd = db.Column(db.Numeric(12, 2), nullable=False)
    amount_local = db.Column(db.Numeric(15, 2), nullable=False)
    fee_usd = db.Column(db.Numeric(10, 2), nullable=False)
    net_usd = db.Column(db.Numeric(12, 2), nullable=False)
    exchange_rate = db.Column(db.Numeric(10, 4), nullable=False)
    
    # Referencias
    currency_id = db.Column(db.Integer, db.ForeignKey('currencies.id'))
    payment_method_from_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'))
    payment_method_to_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'))
    
    # Datos del cliente (JSON flexible)
    client_payment_data = db.Column(db.JSON, nullable=False)
    
    # Comprobantes
    payment_proof_url = db.Column(db.String(500))
    operator_proof_url = db.Column(db.String(500))
    
    # Estado
    status = db.Column(db.Enum(OrderStatus), default=OrderStatus.DRAFT, index=True)
    
    # Canal de origen
    channel = db.Column(db.String(20), nullable=False, default='telegram')
    channel_chat_id = db.Column(db.String(100))
    
    # Timestamps
    submitted_at = db.Column(db.DateTime)
    assigned_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Relaciones
    transactions = db.relationship('Transaction', backref='order', cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='order')
    
    # Métodos clave:
    # - generate_reference()
    # - calculate_totals(calculator_service)
    # - transition_to(new_status, operator, reason)
    # - get_summary_for_notification()
    # - get_daily_stats(date) [classmethod]
```

### **5. Transaction (Contabilidad automática)**

```python
class TransactionType(Enum):
    INCOME = 'income'   # Cliente → Ceiba21
    EXPENSE = 'expense' # Ceiba21 → Cliente
    FEE = 'fee'        # Ganancia de Ceiba21

class Transaction(BaseModel):
    """
    Transacción contable.
    
    Cada orden genera 3 transacciones automáticamente:
    1. INCOME: Cliente nos pagó
    2. FEE: Nuestra comisión
    3. EXPENSE: Pagamos al cliente
    """
    __tablename__ = 'transactions'
    
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    type = db.Column(db.Enum(TransactionType), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False)
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_methods.id'))
    description = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Métodos clave:
    # - create_from_order(order) [classmethod]
    # - get_daily_report(date) [classmethod]
```

### **6. Message (Historial de conversaciones)**

```python
class Message(BaseModel):
    """
    Historial completo de mensajes.
    
    Un solo lugar para TODO el historial, sin importar canal.
    """
    __tablename__ = 'messages'
    
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Canal de origen
    channel = db.Column(db.String(20), nullable=False)
    
    # Contenido
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, image, document
    attachment_url = db.Column(db.String(500))
    
    # Quién envió
    sender_type = db.Column(db.String(20), nullable=False)  # user, bot, operator
    operator_id = db.Column(db.Integer, db.ForeignKey('operators.id'), nullable=True)
    
    # Metadata
    is_read = db.Column(db.Boolean, default=False)
```

### **7. WebUser (Usuarios registrados en web)**

```python
class WebUser(BaseModel, UserMixin):
    """
    Usuario registrado en ceiba21.com
    
    Diferente de User (que es cliente vía bot).
    Puede vincularse con User si también usa bot.
    """
    __tablename__ = 'web_users'
    
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    
    # Vinculación con User (si usa bot también)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Verificación de email
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100))
    
    # Métodos de Flask-Login requeridos
```

---

## ⚙️ SERVICIOS (Lógica de negocio)

### **Principio SOLID: Single Responsibility**

Cada servicio tiene UNA responsabilidad clara.

### **1. OrderService**

```python
class OrderService(BaseService):
    """
    Gestión completa de órdenes.
    
    Métodos:
    - create_order(**kwargs) → Crear orden DRAFT
    - submit_order(order_id, proof_url) → DRAFT → PENDING
    - assign_order(order_id, operator_id) → PENDING → IN_PROCESS
    - complete_order(order_id, operator_id) → IN_PROCESS → COMPLETED
    - cancel_order(order_id, reason) → Cualquier → CANCELLED
    - get_pending_orders()
    - get_operator_orders(operator_id, status)
    - get_daily_stats(date)
    """
```

### **2. CalculatorService (REFACTORIZAR)**

```python
class CalculatorService(BaseService):
    """
    Cálculos de tasas y comisiones.
    
    IMPORTANTE: Debe ser reutilizado por:
    - Calculadora web
    - Bot Telegram
    - Bot WhatsApp
    - OrderService
    - API REST
    
    Métodos:
    - get_rate(currency_id, payment_method_id)
    - calculate_fee(amount_usd, payment_method_id)
    - calculate_exchange(amount_usd, currency_id, payment_method_id)
    - get_all_rates(currency_id)
    """
```

### **3. NotificationService**

```python
class NotificationService(BaseService):
    """
    Notificaciones multi-canal.
    
    Punto único para TODAS las notificaciones.
    
    A usuarios:
    - notify_order_confirmed(order)
    - notify_order_completed(order)
    - notify_order_cancelled(order, reason)
    
    A operadores:
    - notify_new_order(order)
    - notify_operator_assigned(order, operator)
    
    Internos:
    - _send_telegram_user(user, message)
    - _send_whatsapp(user, message)
    - _send_webchat_notification(user, message)
    - _send_email(to, subject, body)
    """
```

### **4. AuthService**

```python
class AuthService(BaseService):
    """
    Autenticación y autorización.
    
    Métodos:
    - authenticate_operator(username, password)
    - authenticate_web_user(email, password)
    - register_web_user(email, password, ...)
    - check_permission(operator, permission)
    - require_permission(permission) [decorador]
    - request_password_reset(email)
    - reset_password(token, new_password)
    """
```

---

## 📡 CAPA DE CANALES (Strategy Pattern)

### **Concepto: Abstracción total**

```
BaseChannel (interfaz) → TelegramChannel, WhatsAppChannel, WebChatChannel

Todos implementan:
- send_message(recipient_id, text)
- send_image(recipient_id, url, caption)
- send_buttons(recipient_id, text, buttons)
- get_user_info(user_id)
```

### **Ventaja:**

```python
# OrderService NO sabe de canales:
NotificationService.notify_order_completed(order)

# NotificationService usa ChannelFactory:
channel, recipient_id = ChannelFactory.get_channel_for_user(order.user)
channel.send_message(recipient_id, message)

# ¡Funciona para CUALQUIER canal sin cambios!
```

---

## 🤖 CONVERSACIÓN AUTOMATIZADA (Bot)

### **ConversationHandler (Máquina de estados finita)**

```python
class ConversationState(Enum):
    START = 'start'
    SELECT_CURRENCY = 'select_currency'
    SELECT_METHOD_FROM = 'select_method_from'
    ENTER_AMOUNT = 'enter_amount'
    CONFIRM_CALCULATION = 'confirm_calculation'
    ENTER_PAYMENT_DATA = 'enter_payment_data'
    AWAIT_PROOF = 'await_proof'
    COMPLETED = 'completed'

class ConversationHandler:
    """
    Maneja conversación paso a paso con cliente.
    
    FLUJO:
    /start → SELECT_CURRENCY → SELECT_METHOD → ENTER_AMOUNT 
    → CONFIRM → ENTER_DATA → AWAIT_PROOF → COMPLETED
    
    Cada estado tiene un handler que procesa input y transiciona.
    """
    
    def handle_message(user, message, current_state):
        # Procesar mensaje según estado actual
        # Validar input
        # Transicionar a siguiente estado
        # Retornar respuesta
```

---

## 💻 DASHBOARD UNIFICADO

### **Características clave:**

1. **Vista de órdenes en tiempo real**
   - Lista de órdenes pendientes
   - Filtros por estado, fecha, canal
   - Notificaciones visuales de nuevas órdenes

2. **Chat unificado**
   - Historial completo de conversación
   - No importa si vino de Telegram, WhatsApp o Web
   - Operador responde en un solo lugar

3. **Acciones rápidas**
   - Tomar orden (asignar a mí)
   - Marcar como pagada
   - Rechazar/cancelar
   - Solicitar más información

4. **Tiempo real con WebSockets**
   - Notificaciones push al navegador
   - Actualización automática de estados
   - Chat en vivo

### **Tecnologías:**

- Flask-SocketIO para WebSockets
- JavaScript vanilla (o Alpine.js para reactividad ligera)
- Tailwind CSS (ya usado en el proyecto)

---

## 📊 SISTEMA DE PERMISOS

### **Permisos granulares (JSON en Operator.permissions):**

```python
PERMISSIONS = {
    "view_orders": True/False,
    "take_orders": True/False,
    "approve_orders": True/False,
    "cancel_orders": True/False,
    "view_reports": True/False,
    "manage_operators": True/False,
    "edit_rates": True/False
}

# Admin tiene TODOS los permisos automáticamente
# Operator tiene permisos configurables
# Viewer solo lectura
```

### **Uso en rutas:**

```python
@app.route('/operator/approve-order/<int:order_id>')
@login_required
@AuthService.require_permission('approve_orders')
def approve_order(order_id):
    # Solo operadores con permiso pueden acceder
    ...
```

---

## 🎯 PLAN DE IMPLEMENTACIÓN POR FASES

### **FASE 1: Base de datos y modelos** ⏱️ 1-2 días

**Objetivo:** Crear estructura de datos completa.

**Tareas:**
1. Crear `app/models/base.py` con BaseModel
2. Crear `app/models/user.py` con User (channel-agnostic)
3. Crear `app/models/operator.py` con Operator y OperatorRole
4. Crear `app/models/order.py` con Order y OrderStatus
5. Crear `app/models/transaction.py` con Transaction
6. Crear `app/models/message.py` con Message
7. Crear `app/models/web_user.py` con WebUser
8. Actualizar `app/models/__init__.py` para importar todo
9. Crear migraciones de BD
10. Probar con seeds básicos

**Archivos a crear:**
- `app/models/base.py`
- `app/models/user.py`
- `app/models/operator.py`
- `app/models/order.py`
- `app/models/transaction.py`
- `app/models/message.py`
- `app/models/web_user.py`

**Archivos a modificar:**
- `app/models/__init__.py`

**Testing:**
- Script de seed: `scripts/seed_operators.py`
- Script de seed: `scripts/seed_test_orders.py`

---

### **FASE 2: Servicios base** ⏱️ 2-3 días

**Objetivo:** Implementar lógica de negocio reutilizable.

**Tareas:**
1. Crear `app/services/base_service.py`
2. Crear `app/services/order_service.py` con CRUD de órdenes
3. REFACTORIZAR `app/services/calculator_service.py` (channel-agnostic)
4. Crear `app/services/user_service.py`
5. Crear `app/services/auth_service.py`
6. Crear `app/services/notification_service.py` (básico)
7. Integrar Redis para cache de tasas
8. Testing unitario de servicios

**Archivos a crear:**
- `app/services/base_service.py`
- `app/services/order_service.py`
- `app/services/user_service.py`
- `app/services/auth_service.py`
- `app/services/notification_service.py`

**Archivos a modificar:**
- `app/services/calculator_service.py` (refactorizar)

**Configuración adicional:**
- Instalar Redis: `sudo apt install redis-server`
- Agregar a `requirements.txt`: `redis==5.0.1`, `flask-caching==2.1.0`

---

### **FASE 3: Capa de canales** ⏱️ 2-3 días

**Objetivo:** Abstracción de canales con Strategy Pattern.

**Tareas:**
1. Crear `app/channels/base_channel.py` (interfaz abstracta)
2. Crear `app/channels/telegram_channel.py`
3. Crear `app/channels/whatsapp_channel.py` (estructura, sin implementar)
4. Crear `app/channels/webchat_channel.py` (estructura)
5. Crear `app/channels/__init__.py` con ChannelFactory
6. Actualizar NotificationService para usar canales
7. Testing de envío de mensajes por Telegram

**Archivos a crear:**
- `app/channels/base_channel.py`
- `app/channels/telegram_channel.py`
- `app/channels/whatsapp_channel.py`
- `app/channels/webchat_channel.py`
- `app/channels/__init__.py`

**Archivos a modificar:**
- `app/services/notification_service.py`

---

### **FASE 4: Bot conversacional (Telegram)** ⏱️ 3-4 días

**Objetivo:** Bot que guía al cliente paso a paso.

**Tareas:**
1. Crear `app/bot/conversation_handler.py` (FSM)
2. Crear `app/bot/message_parser.py` (validaciones)
3. Crear `app/bot/responses.py` (templates de mensajes)
4. Integrar bot con OrderService
5. Configurar handlers de Telegram (actualizar bot existente)
6. Testing del flujo completo

**Archivos a crear:**
- `app/bot/__init__.py`
- `app/bot/conversation_handler.py`
- `app/bot/message_parser.py`
- `app/bot/responses.py`

**Archivos a modificar:**
- `app/telegram/bot.py` (refactorizar para usar ConversationHandler)

**Flujo a implementar:**
```
/start → Saludo
→ ¿Qué moneda? (botones)
→ ¿Método de pago? (botones)
→ ¿Cuánto envías? (input numérico)
→ Resumen + confirmación
→ Solicitar datos de pago
→ Enviar comprobante
→ Confirmación recibida
```

---

### **FASE 5: Dashboard de operadores** ⏱️ 4-5 días

**Objetivo:** Panel web unificado para atender TODAS las órdenes.

**Tareas:**
1. Crear sistema de autenticación (login operadores)
2. Crear `app/routes/auth.py` (login/logout)
3. Crear `app/routes/operator.py` (dashboard)
4. Crear templates HTML:
   - `templates/operator/dashboard.html`
   - `templates/operator/order_detail.html`
   - `templates/auth/login.html`
5. Implementar WebSockets con Flask-SocketIO
6. Vista de órdenes pendientes
7. Vista de detalle con chat unificado
8. Acciones: tomar/aprobar/rechazar

**Archivos a crear:**
- `app/routes/auth.py`
- `app/routes/operator.py`
- `templates/auth/login.html`
- `templates/operator/dashboard.html`
- `templates/operator/order_detail.html`
- `app/static/js/operator_dashboard.js`

**Dependencias adicionales:**
- `flask-socketio==5.3.6`
- `flask-login==0.6.3`

---

### **FASE 6: Contabilidad automática** ⏱️ 2 días

**Objetivo:** Reportes financieros automáticos.

**Tareas:**
1. Crear `app/services/accounting_service.py`
2. Integrar creación de transacciones en `complete_order()`
3. Dashboard de reportes contables
4. Exportar a Excel/PDF
5. Gráficos con Chart.js

**Archivos a crear:**
- `app/services/accounting_service.py`
- `templates/operator/reports.html`

---

### **FASE 7: Registro de usuarios web** ⏱️ 2 días

**Objetivo:** Usuarios pueden registrarse en ceiba21.com.

**Tareas:**
1. Formulario de registro
2. Verificación de email
3. Login de usuarios web
4. Dashboard de usuario (ver sus órdenes)
5. Recuperación de contraseña

**Archivos a crear:**
- `templates/auth/register.html`
- `templates/auth/verify_email.html`
- `templates/auth/reset_password.html`
- `templates/user/dashboard.html`

---

### **FASE 8: WebChat en vivo** ⏱️ 3 días (FUTURO)

**Objetivo:** Chat en vivo en ceiba21.com sin depender de Telegram/WhatsApp.

**Tareas:**
1. Widget de chat flotante en sitio web
2. WebSocket para comunicación en tiempo real
3. Integración con ConversationHandler
4. Integración con dashboard de operadores

---

### **FASE 9: WhatsApp Bot** ⏱️ 3-4 días (FUTURO)

**Objetivo:** Bot de WhatsApp (igual que Telegram).

**Tareas:**
1. Configurar Twilio WhatsApp API
2. Implementar completamente `whatsapp_channel.py`
3. Webhooks para recibir mensajes
4. Testing

---

### **FASE 10: App móvil** ⏱️ 3-4 semanas (FUTURO)

**Objetivo:** App nativa para iOS/Android.

**Recomendación:** Flutter
- ✅ Un solo código para iOS y Android
- ✅ Performance nativa
- ✅ UI hermosa con Material Design
- ✅ Comunidad grande

**Alternativa:** React Native si prefieres JavaScript

---

## 🛠️ CONFIGURACIONES ADICIONALES

### **Redis (para cache):**

```bash
# Instalar
sudo apt install redis-server

# Configurar límite de memoria
sudo nano /etc/redis/redis.conf
# Agregar: maxmemory 100mb

# Habilitar
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### **Flask-SocketIO (para WebSockets):**

```bash
# En venv
pip install flask-socketio python-socketio

# Modificar wsgi.py o crear nuevo app_socketio.py
```

### **Connection Pooling PostgreSQL:**

```python
# config.py
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 1800,
    'pool_pre_ping': True
}
```

### **Variables de entorno adicionales (.env):**

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Telegram
TELEGRAM_OPERATORS_CHANNEL_ID=-100XXXXXXXXX

# Email (ya configurado)
EMAIL_SENDER=webmaster@ceiba21.com

# Dashboard
DASHBOARD_URL=https://ceiba21.com

# Flask-SocketIO
SOCKETIO_MESSAGE_QUEUE=redis://localhost:6379/1
```

---

## 📝 PROMPTS PARA CLINE POR FASE

### **FASE 1: Modelos**

```
CONTEXTO:
Estoy desarrollando un sistema de gestión de órdenes para Ceiba21, plataforma de cambio de divisas.

ESTADO ACTUAL:
- Dashboard admin funcionando
- Modelos: Currency, PaymentMethod, Quote
- Ubicación: /var/www/cotizaciones

OBJETIVO FASE 1: Crear modelos de datos

Necesito crear los siguientes modelos usando SQLAlchemy 2.0:

1. BaseModel (clase abstracta base)
2. User (cliente channel-agnostic)
3. Operator (con roles y permisos)
4. Order (con máquina de estados)
5. Transaction (contabilidad)
6. Message (historial de chats)
7. WebUser (usuarios registrados web)

REQUISITOS:
- Heredar de BaseModel
- Usar enums para estados
- FK con cascade apropiados
- Timestamps automáticos
- Métodos útiles en cada clase
- Mantener estilo del código existente (ver app/models/currency.py como referencia)

ARCHIVOS A CREAR:
- app/models/base.py
- app/models/user.py
- app/models/operator.py
- app/models/order.py
- app/models/transaction.py
- app/models/message.py
- app/models/web_user.py

ARCHIVOS A MODIFICAR:
- app/models/__init__.py (agregar imports)

¿Empezamos con BaseModel? Muéstrame el código y explica las decisiones de diseño.
```

### **FASE 2: Servicios**

```
Ya tenemos los modelos creados. Ahora necesito implementar la capa de servicios.

OBJETIVO: Crear servicios reutilizables con lógica de negocio

Servicios a crear:
1. BaseService (clase base)
2. OrderService (gestión de órdenes)
3. UserService (gestión de usuarios)
4. AuthService (autenticación)
5. NotificationService (básico, sin canales aún)

IMPORTANTE: 
- OrderService debe ser channel-agnostic
- Reutilizar CalculatorService existente (necesita refactor)
- Métodos claros y documentados

ARCHIVOS A CREAR:
- app/services/base_service.py
- app/services/order_service.py
- app/services/user_service.py
- app/services/auth_service.py
- app/services/notification_service.py

ARCHIVOS A REFACTORIZAR:
- app/services/calculator_service.py (hacer channel-agnostic)

Empecemos con BaseService y OrderService.
```

### **FASE 3: Canales**

```
Necesito implementar la capa de abstracción de canales (Strategy Pattern).

OBJETIVO: Que NotificationService pueda enviar mensajes a Telegram, WhatsApp o WebChat sin saber cuál es.

Crear:
1. BaseChannel (interfaz abstracta)
2. TelegramChannel (implementación completa)
3. WhatsAppChannel (estructura para futuro)
4. WebChatChannel (estructura para futuro)
5. ChannelFactory

Métodos comunes:
- send_message(recipient_id, text)
- send_image(recipient_id, url, caption)
- send_buttons(recipient_id, text, buttons)
- get_user_info(user_id)

ARCHIVOS A CREAR:
- app/channels/base_channel.py
- app/channels/telegram_channel.py
- app/channels/whatsapp_channel.py
- app/channels/webchat_channel.py
- app/channels/__init__.py

Empecemos con BaseChannel y TelegramChannel.
```

---

## 🎯 PRIORIDADES Y ORDEN DE IMPLEMENTACIÓN

**Semana 1-2:**
- ✅ Fase 1: Modelos (CRÍTICO)
- ✅ Fase 2: Servicios (CRÍTICO)

**Semana 3:**
- ✅ Fase 3: Canales (IMPORTANTE)
- ✅ Fase 4: Bot Telegram (IMPORTANTE)

**Semana 4:**
- ✅ Fase 5: Dashboard operadores (CRÍTICO)

**Semana 5:**
- ✅ Fase 6: Contabilidad (IMPORTANTE)
- ✅ Fase 7: Registro web (BUENO TENER)

**Futuro:**
- ⏳ Fase 8: WebChat
- ⏳ Fase 9: WhatsApp Bot
- ⏳ Fase 10: App móvil

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### **Activar entorno virtual:**

```bash
cd /var/www/cotizaciones
source venv/bin/activate
```

### **Cuándo activar venv:**
- ✅ Al ejecutar scripts Python del proyecto
- ✅ Al instalar paquetes con pip
- ✅ Al ejecutar Flask/Gunicorn
- ❌ NO para comandos del sistema (git, sudo, etc.)

### **Testing:**

Después de cada fase, crear scripts de prueba:
```bash
python scripts/test_phase1_models.py
python scripts/test_phase2_services.py
```

### **Git workflow:**

```bash
# Crear rama por fase
git checkout -b feature/fase1-modelos

# Commits frecuentes
git add .
git commit -m "feat: añadir BaseModel y User"

# Push y merge a main
git push origin feature/fase1-modelos
```

### **Backup antes de cambios grandes:**

```bash
# Backup de BD
~/backup_database.sh

# Backup de código
cd /var/www
tar -czf cotizaciones_backup_$(date +%Y%m%d).tar.gz cotizaciones/
```

---

## 📚 RECURSOS Y DOCUMENTACIÓN

### **Tecnologías:**
- Flask: https://flask.palletsprojects.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- python-telegram-bot: https://docs.python-telegram-bot.org/
- Flask-SocketIO: https://flask-socketio.readthedocs.io/

### **Patrones de diseño:**
- Strategy Pattern (canales)
- Factory Pattern (ChannelFactory)
- Service Layer Pattern (servicios)
- Repository Pattern (modelos)

---

## ✅ CRITERIOS DE ÉXITO

### **Al finalizar TODAS las fases:**

1. ✅ Cliente puede crear orden completa desde Telegram bot
2. ✅ Operador ve orden en dashboard web
3. ✅ Operador puede responder al cliente desde dashboard
4. ✅ Cliente recibe respuesta en su canal (Telegram)
5. ✅ Orden se completa y genera contabilidad automática
6. ✅ Reportes financieros disponibles
7. ✅ Sistema funciona igual para Telegram, WhatsApp (futuro) y WebChat (futuro)
8. ✅ Cero cambios en servicios al agregar nuevo canal

---

## 🚨 NOTAS FINALES

- **Mantener coherencia:** Seguir estilo de código existente
- **Documentar:** Docstrings en español, claros y útiles
- **Testing:** Probar cada fase antes de continuar
- **Git:** Commits frecuentes y descriptivos
- **Backup:** Siempre antes de cambios grandes
- **Entorno virtual:** Recordar activar cuando sea necesario

---

**Autor:** Jose (Ceiba21)  
**Asistente:** Claude (Anthropic)  
**Fecha:** Diciembre 2025  
**Versión:** 1.0

---

## 📎 ANEXOS

### **Anexo A: Estructura actual del proyecto**

```
/var/www/cotizaciones/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── currency.py
│   │   ├── exchange_rate.py
│   │   ├── payment_method.py
│   │   ├── quote.py
│   │   └── quote_history.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── main.py
│   │   └── public.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── api_service.py
│   │   ├── currency_service.py
│   │   ├── exchange_rate_service.py
│   │   ├── payment_method_service.py
│   │   └── quote_service.py
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── bot.py
│   │   ├── formatters.py
│   │   └── image_generator.py
│   ├── templates/
│   ├── static/
│   └── utils/
├── venv/
├── logs/
├── instance/
├── requirements.txt
├── wsgi.py
└── README.md
```

### **Anexo B: Variables de entorno actuales (.env)**

```bash
# Flask
SECRET_KEY=...
FLASK_ENV=production

# Database
DATABASE_URL=postgresql://webmaster:password@localhost/cotizaciones_db

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHANNEL_ID=@ceiba21_canal

# Admin (para dashboard actual)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=...
```

### **Anexo C: Comandos útiles**

```bash
# Activar venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Crear migraciones (si usas Flask-Migrate)
flask db migrate -m "Add orders system"
flask db upgrade

# Correr servidor de desarrollo
flask run --host=0.0.0.0 --port=5000

# Reiniciar servicio en producción
sudo systemctl restart ceiba21

# Ver logs
sudo journalctl -u ceiba21 -f

# Acceder a PostgreSQL
psql -U webmaster -d cotizaciones_db
```
