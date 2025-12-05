# FASE 5: DASHBOARD DE OPERADORES

## 📋 CONTEXTO

Sistema de órdenes Ceiba21 - Ya completamos Fases 1, 2, 3 y 4.

### Estado completado:
- ✅ **Fase 1:** Modelos (BaseModel, User, Operator, Order, Transaction, Message, WebUser)
- ✅ **Fase 2:** Servicios (OrderService, CalculatorService, AuthService, NotificationService)
- ✅ **Fase 3:** Canales (BaseChannel, TelegramChannel, WhatsAppChannel, WebChatChannel, ChannelFactory)
- ✅ **Fase 4:** Bot conversacional de Telegram (FSM completa, comandos admin/operador)

### Objetivo de esta fase:
Crear un dashboard web unificado donde los operadores puedan ver y gestionar TODAS las órdenes desde un solo lugar, sin importar si vienen de Telegram, WhatsApp o WebChat.

---

## 🎯 CONCEPTO CLAVE: DASHBOARD UNIFICADO

### Problema que resolvemos:

**❌ Sin dashboard unificado:**
```
Operador debe:
- Abrir Telegram para ver órdenes de Telegram
- Abrir WhatsApp para ver órdenes de WhatsApp
- Abrir otro sistema para WebChat
→ Caos, órdenes perdidas, lentitud
```

**✅ Con dashboard unificado:**
```
Operador abre UN SOLO navegador:
- Ve TODAS las órdenes (Telegram + WhatsApp + WebChat)
- Chat unificado (historial completo sin importar canal)
- Responde desde UN lugar, mensaje llega al canal correcto
→ Eficiencia máxima, cero órdenes perdidas
```

---

## 🏗️ ARQUITECTURA DEL DASHBOARD

```
┌─────────────────────────────────────────────────┐
│         CLIENTES (Múltiples canales)            │
│  [Telegram Bot] [WhatsApp Bot] [WebChat]        │
└─────────────────┬───────────────────────────────┘
                  │ Mensajes entrantes
                  ↓
┌─────────────────────────────────────────────────┐
│         BASE DE DATOS (PostgreSQL)              │
│  • orders (con channel de origen)               │
│  • messages (historial completo)                │
└─────────────────┬───────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────┐
│      DASHBOARD WEB (Flask + WebSockets)         │
│                                                  │
│  ┌──────────────┐  ┌────────────────────────┐  │
│  │ LISTA        │  │ DETALLE + CHAT         │  │
│  │ ÓRDENES      │  │                        │  │
│  │              │  │ [Orden ORD-001]        │  │
│  │ 🔵 ORD-003   │  │ Cliente: @user         │  │
│  │ @user3       │  │ Canal: Telegram        │  │
│  │ Telegram     │  │                        │  │
│  │              │  │ 💬 Chat:               │  │
│  │ 🟢 ORD-002   │  │ ┌──────────────────┐   │  │
│  │ +58xxx       │  │ │ User: Hola       │   │  │
│  │ WhatsApp     │  │ │ Bot: ¿Cuánto?    │   │  │
│  │              │  │ │ User: 100        │   │  │
│  │ 🔴 ORD-001   │  │ │ [Tu respuesta]   │   │  │
│  │ web-123      │  │ └──────────────────┘   │  │
│  │ WebChat      │  │                        │  │
│  └──────────────┘  │ [✅ Marcar pagada]     │  │
│                    │ [❌ Rechazar]          │  │
│                    └────────────────────────┘  │
└─────────────────────────────────────────────────┘
                  │
                  ↓ Respuesta del operador
┌─────────────────────────────────────────────────┐
│         NotificationService                      │
│         ChannelFactory                           │
└─────────────────┬───────────────────────────────┘
                  │
                  ↓ Envía por canal correcto
┌─────────────────────────────────────────────────┐
│     CLIENTE recibe en SU canal original         │
│     (Telegram/WhatsApp/WebChat)                 │
└─────────────────────────────────────────────────┘
```

---

## 🎨 MOCKUP DEL DASHBOARD

```
┌────────────────────────────────────────────────────────────────────┐
│ Ceiba21 Dashboard                     👤 Operador: Juan ▼  [🔔 3]  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│ ┌─────────────────────┐  ┌──────────────────────────────────────┐│
│ │ ÓRDENES PENDIENTES  │  │ ORDEN: ORD-20251204-001              ││
│ │      (15)           │  ├──────────────────────────────────────┤│
│ ├─────────────────────┤  │                                      ││
│ │ [Filtros ▼]         │  │ 👤 Cliente: @juanperez (Telegram)    ││
│ │ ☐ Telegram          │  │ 💰 Monto: $100 → 28,808.65 Bs       ││
│ │ ☐ WhatsApp          │  │ 📅 Creada: 14:35 (hace 15 min)      ││
│ │ ☐ WebChat           │  │ ⏱️ Asignada a ti: hace 5 min        ││
│ │                     │  │                                      ││
│ │ [Buscar orden...]   │  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ││
│ ├─────────────────────┤  │                                      ││
│ │                     │  │ 📸 COMPROBANTE:                      ││
│ │ 🔴 ORD-003          │  │ ┌────────────────────────────────┐  ││
│ │ @maria_v            │  │ │                                │  ││
│ │ $250 → 76,375 Bs    │  │ │    [Imagen del comprobante]    │  ││
│ │ 📱 Telegram         │  │ │                                │  ││
│ │ ⏰ 14:50 (25 min)    │  │ │                                │  ││
│ │ [TOMAR]             │  │ └────────────────────────────────┘  ││
│ │                     │  │ [🔍 Ampliar] [📥 Descargar]         ││
│ │ 🟡 ORD-002          │  │                                      ││
│ │ +58412xxx           │  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ││
│ │ $100 → 30,550 Bs    │  │                                      ││
│ │ 📱 WhatsApp         │  │ 💬 CONVERSACIÓN:                     ││
│ │ ⏰ 15:02 (13 min)    │  │ ┌────────────────────────────────┐  ││
│ │ [TOMAR]             │  │ │ 👤 User: Hola                  │  ││
│ │                     │  │ │ 🤖 Bot: Bienvenido a Ceiba21   │  ││
│ │ 🟢 ORD-001          │  │ │ 👤 User: Quiero cambiar        │  ││
│ │ web-user123         │  │ │ 🤖 Bot: ¿Qué moneda?           │  ││
│ │ $50 → 15,275 Bs     │  │ │ 👤 User: VES                   │  ││
│ │ 🌐 WebChat          │  │ │ 🤖 Bot: ¿Método de pago?       │  ││
│ │ ⏰ 15:10 (5 min)     │  │ │ 👤 User: PayPal                │  ││
│ │ [TOMAR]             │  │ │ 🤖 Bot: ¿Cuánto enviarás?      │  ││
│ │                     │  │ │ 👤 User: 100                   │  ││
│ │ [Ver todas...]      │  │ │ 🤖 Bot: [Resumen cálculo]      │  ││
│ │                     │  │ │ 👤 User: Sí confirmo           │  ││
│ │                     │  │ │ 🤖 Bot: Datos bancarios        │  ││
│ └─────────────────────┘  │ │ 👤 User: [datos enviados]      │  ││
│                          │ │ 👤 User: [imagen enviada]      │  ││
│ 📊 ESTADÍSTICAS HOY      │ └────────────────────────────────┘  ││
│ ├──────────────────────  │                                      ││
│ │ ✅ Completadas: 12   │ │ ┌────────────────────────────────┐  ││
│ │ ⏳ Pendientes: 3     │ │ │ Escribe tu mensaje aquí...     │  ││
│ │ 💰 Volumen: $1,250   │ │ └────────────────────────────────┘  ││
│ │ ⏱️ Tiempo avg: 18min │ │ [📎 Adjuntar] [😊 Emoji] [Enviar]  ││
│ └──────────────────────  │                                      ││
│                          │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ││
│                          │                                      ││
│                          │ ⚡ ACCIONES RÁPIDAS:                 ││
│                          │ [✅ Marcar como pagada]              ││
│                          │ [❌ Rechazar orden]                  ││
│                          │ [📋 Copiar datos cliente]           ││
│                          │ [🔄 Solicitar más info]             ││
│                          │ [📞 Llamar cliente]                 ││
│                          └──────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 FUNCIONALIDADES DEL DASHBOARD

### 1. Autenticación de operadores

**Sistema de login seguro:**
- Username + password
- Sesiones con Flask-Login
- Roles: ADMIN, OPERATOR, VIEWER
- Permisos granulares

---

### 2. Vista de órdenes (Lista)

**Características:**
- Ver todas las órdenes pendientes en tiempo real
- Indicador visual del canal (🔵 Telegram, 🟢 WhatsApp, 🟡 WebChat)
- Filtros: por canal, por estado, por fecha
- Búsqueda: por referencia, por cliente, por monto
- Ordenar: por fecha, por monto, por tiempo en espera
- Colores según urgencia:
  - 🟢 Verde: < 15 min
  - 🟡 Amarillo: 15-30 min
  - 🔴 Rojo: > 30 min

**Acciones rápidas:**
- Botón "TOMAR" para asignar orden a ti
- Click en orden para ver detalle

---

### 3. Vista de detalle de orden

**Información mostrada:**
- Datos del cliente (nombre, canal, identificador)
- Datos financieros (monto USD, monto local, tasa, comisión)
- Datos de pago del cliente (banco, cuenta, titular, cédula)
- Comprobante de pago (imagen ampliable)
- Estado actual de la orden
- Tiempo transcurrido
- Operador asignado (si aplica)

---

### 4. Chat unificado

**Lo más importante del dashboard:**

**Características:**
- Historial completo de conversación
- Mensajes del usuario, bot y operadores
- Indicadores visuales:
  - 👤 Usuario
  - 🤖 Bot automático
  - 👨‍💼 Operador (con nombre)
- Scroll infinito (cargar más mensajes antiguos)
- Timestamps en cada mensaje
- Texto formateado (negrita, cursiva, código)

**Responder al cliente:**
- Campo de texto simple
- Botón "Enviar" o Enter
- Emojis disponibles
- Adjuntar imágenes (opcional)
- Templates de respuestas rápidas

**IMPORTANTE:** 
- Cuando operador envía mensaje, va automáticamente al canal del cliente
- Si cliente vino por Telegram → mensaje se envía por Telegram
- Si cliente vino por WhatsApp → mensaje se envía por WhatsApp
- Todo esto transparente para el operador (no necesita saber el canal)

---

### 5. Acciones sobre órdenes

**Operador puede:**

1. **✅ Marcar como pagada**
   - Modal: "¿Confirmaste el pago al cliente?"
   - Input opcional: URL del comprobante de pago realizado
   - Al confirmar:
     - Orden → estado COMPLETED
     - Genera transacciones contables automáticamente
     - Notifica al cliente (por su canal)

2. **❌ Rechazar orden**
   - Modal: "¿Motivo del rechazo?"
   - Input obligatorio: razón
   - Al confirmar:
     - Orden → estado CANCELLED
     - Notifica al cliente con el motivo

3. **🔄 Solicitar más información**
   - Templates predefinidos:
     - "Por favor envía una imagen más clara del comprobante"
     - "Verifica que el monto sea exacto"
     - "¿Ya realizaste el pago?"
   - O mensaje personalizado

4. **📋 Copiar datos**
   - Copiar al portapapeles:
     - Datos bancarios del cliente
     - Referencia de la orden
     - Monto a pagar

5. **📞 Contactar cliente**
   - Si tiene teléfono registrado, mostrar número
   - Botón para copiar número

---

### 6. Notificaciones en tiempo real

**WebSocket para notificaciones push:**

**Operador recibe notificación cuando:**
- Nueva orden llega (PENDING)
- Cliente envía nuevo mensaje
- Orden es tomada por otro operador
- Orden es completada/cancelada

**Tipos de notificación:**
- **Toast/Snackbar** en esquina: Para eventos no urgentes
- **Sonido + Badge** en tab del navegador: Para nuevas órdenes
- **Banner destacado**: Para órdenes urgentes (>30 min esperando)

---

### 7. Estadísticas del operador

**Panel personal:**
- Órdenes completadas hoy
- Órdenes pendientes asignadas a mí
- Volumen procesado hoy (USD)
- Tiempo promedio de procesamiento
- Rating de satisfacción (futuro)

**Panel general (solo ADMIN):**
- Total de órdenes del día
- Volumen total
- Operadores activos
- Órdenes por canal (Telegram vs WhatsApp vs WebChat)

---

## 📁 ARCHIVOS A CREAR

```
app/routes/
├── auth.py                    # Login/logout operadores
├── operator_dashboard.py      # Dashboard principal
└── operator_api.py            # Endpoints AJAX/WebSocket

app/templates/
├── auth/
│   ├── login.html            # Página de login
│   └── base_auth.html        # Layout para auth
│
└── operator/
    ├── base.html             # Layout base (navbar, sidebar)
    ├── dashboard.html        # Vista principal
    ├── order_detail.html     # Detalle de orden (o modal)
    └── components/
        ├── order_card.html   # Componente orden en lista
        ├── chat.html         # Componente chat
        └── stats.html        # Componente estadísticas

app/static/
├── css/
│   └── operator.css          # Estilos del dashboard
│
└── js/
    ├── operator_dashboard.js # Lógica principal
    ├── websocket_client.js   # Cliente WebSocket
    └── order_actions.js      # Acciones sobre órdenes
```

---

## 📝 ARCHIVOS A MODIFICAR

- `app/__init__.py` (agregar Flask-SocketIO)
- `wsgi.py` (inicializar SocketIO)
- `requirements.txt` (agregar dependencias)

---

## 🔧 REQUISITOS TÉCNICOS

### 1. Sistema de autenticación (Flask-Login)

```python
# app/routes/auth.py

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.services.auth_service import AuthService
from app.models.operator import Operator

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Página de login para operadores.
    """
    if current_user.is_authenticated:
        return redirect(url_for('operator.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        operator = AuthService.authenticate_operator(username, password)
        
        if operator:
            login_user(operator, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('operator.dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """
    Cerrar sesión.
    """
    AuthService.logout_operator(current_user)
    logout_user()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('auth.login'))
```

---

### 2. Dashboard principal

```python
# app/routes/operator_dashboard.py

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.services.order_service import OrderService
from app.services.auth_service import AuthService

operator_bp = Blueprint('operator', __name__, url_prefix='/operator')

@operator_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Dashboard principal de operadores.
    
    Vista unificada de TODAS las órdenes.
    """
    # Verificar que sea operador activo
    if not current_user.is_active:
        flash('Tu cuenta está desactivada', 'error')
        return redirect(url_for('auth.logout'))
    
    # Obtener órdenes pendientes
    pending_orders = OrderService.get_pending_orders()
    
    # Obtener órdenes asignadas a mí que están en proceso
    my_orders = OrderService.get_operator_orders(
        current_user.id,
        status=OrderStatus.IN_PROCESS
    )
    
    # Estadísticas del día
    stats = OrderService.get_daily_stats()
    
    return render_template(
        'operator/dashboard.html',
        pending_orders=pending_orders,
        my_orders=my_orders,
        stats=stats,
        operator=current_user
    )

@operator_bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """
    Detalle de una orden específica.
    
    Incluye:
    - Datos completos de la orden
    - Historial de chat
    - Acciones disponibles
    """
    order = OrderService.get_order_summary(order_id)
    
    if not order:
        flash('Orden no encontrada', 'error')
        return redirect(url_for('operator.dashboard'))
    
    # Verificar permisos
    if not AuthService.check_permission(current_user, 'view_orders'):
        flash('No tienes permisos', 'error')
        return redirect(url_for('operator.dashboard'))
    
    # Obtener historial de mensajes
    messages = Message.query.filter_by(order_id=order_id).order_by(Message.created_at).all()
    
    return render_template(
        'operator/order_detail.html',
        order=order,
        messages=messages,
        operator=current_user
    )
```

---

### 3. API endpoints para acciones

```python
# app/routes/operator_api.py

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.services.order_service import OrderService
from app.services.notification_service import NotificationService
from app.models.message import Message
from app.channels import ChannelFactory

api_bp = Blueprint('operator_api', __name__, url_prefix='/api/operator')

@api_bp.route('/take-order', methods=['POST'])
@login_required
def take_order():
    """
    Operador toma una orden (asignar a sí mismo).
    
    POST /api/operator/take-order
    Body: {"order_id": 123}
    """
    order_id = request.json.get('order_id')
    
    try:
        order = OrderService.assign_order(order_id, current_user.id)
        
        return jsonify({
            'success': True,
            'message': f'Orden {order.reference} asignada a ti',
            'order': order.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@api_bp.route('/complete-order', methods=['POST'])
@login_required
def complete_order():
    """
    Marcar orden como completada (pago realizado).
    
    POST /api/operator/complete-order
    Body: {
        "order_id": 123,
        "operator_proof_url": "https://..." (opcional)
    }
    """
    order_id = request.json.get('order_id')
    proof_url = request.json.get('operator_proof_url')
    
    try:
        order = OrderService.complete_order(
            order_id=order_id,
            operator_id=current_user.id,
            operator_proof_url=proof_url
        )
        
        return jsonify({
            'success': True,
            'message': f'Orden {order.reference} completada',
            'order': order.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@api_bp.route('/cancel-order', methods=['POST'])
@login_required
def cancel_order():
    """
    Rechazar/cancelar orden.
    
    POST /api/operator/cancel-order
    Body: {
        "order_id": 123,
        "reason": "Comprobante no es válido"
    }
    """
    order_id = request.json.get('order_id')
    reason = request.json.get('reason')
    
    if not reason:
        return jsonify({
            'success': False,
            'message': 'Debes proporcionar un motivo'
        }), 400
    
    try:
        order = OrderService.cancel_order(
            order_id=order_id,
            reason=reason,
            cancelled_by='operator'
        )
        
        return jsonify({
            'success': True,
            'message': f'Orden {order.reference} cancelada',
            'order': order.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@api_bp.route('/send-message', methods=['POST'])
@login_required
def send_message():
    """
    Operador envía mensaje al cliente.
    
    MAGIA: Mensaje va automáticamente al canal correcto del cliente.
    
    POST /api/operator/send-message
    Body: {
        "order_id": 123,
        "message": "Por favor envía comprobante más claro"
    }
    """
    order_id = request.json.get('order_id')
    message_text = request.json.get('message')
    
    if not message_text:
        return jsonify({
            'success': False,
            'message': 'El mensaje no puede estar vacío'
        }), 400
    
    try:
        order = Order.find_by_id(order_id)
        
        if not order:
            return jsonify({
                'success': False,
                'message': 'Orden no encontrada'
            }), 404
        
        # Guardar mensaje en BD
        msg = Message(
            order_id=order_id,
            user_id=order.user_id,
            channel=order.channel,
            content=message_text,
            sender_type='operator',
            operator_id=current_user.id,
            message_type='text'
        )
        msg.save()
        
        # Enviar por el canal correcto del cliente
        channel, recipient_id = ChannelFactory.get_channel_for_user(order.user)
        channel.send_message(recipient_id, message_text)
        
        # Emitir por WebSocket para actualizar dashboard en tiempo real
        socketio.emit('new_message', {
            'order_id': order_id,
            'message': msg.to_dict()
        }, room=f'operator_{current_user.id}')
        
        return jsonify({
            'success': True,
            'message': 'Mensaje enviado',
            'message_data': msg.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_bp.route('/orders', methods=['GET'])
@login_required
def get_orders():
    """
    Obtener lista de órdenes (para actualización dinámica).
    
    GET /api/operator/orders?status=pending&channel=telegram
    """
    status = request.args.get('status')
    channel = request.args.get('channel')
    
    # Construir query
    query = Order.query
    
    if status:
        query = query.filter_by(status=OrderStatus[status.upper()])
    
    if channel:
        query = query.filter_by(channel=channel)
    
    orders = query.order_by(Order.created_at.desc()).limit(50).all()
    
    return jsonify({
        'success': True,
        'orders': [o.to_dict() for o in orders]
    })
```

---

### 4. WebSocket para tiempo real

```python
# app/__init__.py

from flask_socketio import SocketIO, emit, join_room, leave_room

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    # ... configuración ...
    
    socketio.init_app(app, cors_allowed_origins="*")
    
    return app

# ==========================================
# WebSocket eventos
# ==========================================

@socketio.on('connect', namespace='/operator')
def operator_connect():
    """
    Cuando operador abre dashboard, conectar al WebSocket.
    """
    if not current_user.is_authenticated:
        return False
    
    # Unir a sala personal del operador
    join_room(f'operator_{current_user.id}')
    
    # Unir a sala general de operadores
    join_room('operators')
    
    # Marcar operador como online
    current_user.is_online = True
    current_user.save()
    
    emit('connected', {'message': 'Conectado al dashboard'})

@socketio.on('disconnect', namespace='/operator')
def operator_disconnect():
    """
    Cuando operador cierra dashboard.
    """
    if current_user.is_authenticated:
        current_user.is_online = False
        current_user.save()

@socketio.on('ping', namespace='/operator')
def handle_ping():
    """
    Mantener conexión activa.
    """
    emit('pong')

# ==========================================
# Funciones para emitir eventos
# ==========================================

def notify_new_order(order):
    """
    Notificar a TODOS los operadores online de nueva orden.
    
    Llamar desde OrderService.submit_order()
    """
    socketio.emit('new_order', {
        'order_id': order.id,
        'reference': order.reference,
        'user': order.user.get_display_name(),
        'amount_usd': float(order.amount_usd),
        'amount_local': float(order.amount_local),
        'currency': order.currency.code,
        'channel': order.channel,
        'created_at': order.created_at.isoformat()
    }, namespace='/operator', room='operators')

def notify_order_taken(order, operator):
    """
    Notificar que orden fue tomada por otro operador.
    """
    socketio.emit('order_taken', {
        'order_id': order.id,
        'reference': order.reference,
        'operator': operator.full_name
    }, namespace='/operator', room='operators')

def notify_new_message(order_id, message):
    """
    Notificar nuevo mensaje en una orden.
    
    Solo al operador que tiene asignada la orden.
    """
    order = Order.find_by_id(order_id)
    
    if order.operator_id:
        socketio.emit('new_message', {
            'order_id': order_id,
            'message': message.to_dict()
        }, namespace='/operator', room=f'operator_{order.operator_id}')
```

---

### 5. Frontend JavaScript

```javascript
// app/static/js/operator_dashboard.js

class OperatorDashboard {
    constructor() {
        this.socket = null;
        this.currentOrderId = null;
        this.init();
    }
    
    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.loadOrders();
        this.startHeartbeat();
    }
    
    // ==========================================
    // WebSocket
    // ==========================================
    
    connectWebSocket() {
        this.socket = io('/operator');
        
        this.socket.on('connect', () => {
            console.log('✅ Conectado al servidor');
            this.showNotification('Conectado al dashboard', 'success');
        });
        
        this.socket.on('disconnect', () => {
            console.log('❌ Desconectado del servidor');
            this.showNotification('Conexión perdida, reconectando...', 'warning');
        });
        
        this.socket.on('new_order', (data) => {
            console.log('🔔 Nueva orden:', data);
            this.handleNewOrder(data);
        });
        
        this.socket.on('order_taken', (data) => {
            console.log('👤 Orden tomada:', data);
            this.handleOrderTaken(data);
        });
        
        this.socket.on('new_message', (data) => {
            console.log('💬 Nuevo mensaje:', data);
            this.handleNewMessage(data);
        });
    }
    
    startHeartbeat() {
        // Ping cada 30 segundos para mantener conexión
        setInterval(() => {
            this.socket.emit('ping');
        }, 30000);
    }
    
    // ==========================================
    // Handlers de eventos WebSocket
    // ==========================================
    
    handleNewOrder(data) {
        // Agregar orden a la lista
        this.addOrderToList(data);
        
        // Mostrar notificación
        this.showNotification(`Nueva orden: ${data.reference}`, 'info', true);
        
        // Sonido
        this.playNotificationSound();
        
        // Badge en tab del navegador
        this.updateBrowserBadge('+1');
    }
    
    handleOrderTaken(data) {
        // Remover orden de la lista de pendientes
        this.removeOrderFromList(data.order_id);
        
        // Notificar
        this.showNotification(
            `${data.operator} tomó la orden ${data.reference}`,
            'info'
        );
    }
    
    handleNewMessage(data) {
        // Si tengo abierta esta orden, agregar mensaje al chat
        if (this.currentOrderId === data.order_id) {
            this.appendMessage(data.message);
        } else {
            // Mostrar badge en la orden
            this.showBadgeOnOrder(data.order_id);
        }
    }
    
    // ==========================================
    // Acciones sobre órdenes
    // ==========================================
    
    async takeOrder(orderId) {
        try {
            const response = await fetch('/api/operator/take-order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ order_id: orderId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                this.loadOrderDetail(orderId);
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Error al tomar orden', 'error');
        }
    }
    
    async completeOrder(orderId, proofUrl = null) {
        // Confirmar con modal
        const confirmed = await this.showConfirmModal(
            '¿Marcar como pagada?',
            '¿Confirmaste que realizaste el pago al cliente?'
        );
        
        if (!confirmed) return;
        
        try {
            const response = await fetch('/api/operator/complete-order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    order_id: orderId,
                    operator_proof_url: proofUrl
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                this.removeOrderFromList(orderId);
                this.closeSidebar();
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Error al completar orden', 'error');
        }
    }
    
    async cancelOrder(orderId) {
        // Modal para solicitar motivo
        const reason = await this.showReasonModal(
            'Cancelar orden',
            'Indica el motivo de la cancelación:'
        );
        
        if (!reason) return;
        
        try {
            const response = await fetch('/api/operator/cancel-order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    order_id: orderId,
                    reason: reason
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                this.removeOrderFromList(orderId);
                this.closeSidebar();
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Error al cancelar orden', 'error');
        }
    }
    
    async sendMessage(orderId, message) {
        if (!message.trim()) return;
        
        try {
            const response = await fetch('/api/operator/send-message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    order_id: orderId,
                    message: message
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Limpiar input
                document.getElementById('message-input').value = '';
                
                // Mensaje se agregará automáticamente vía WebSocket
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Error al enviar mensaje', 'error');
        }
    }
    
    // ==========================================
    // UI Helpers
    // ==========================================
    
    showNotification(message, type = 'info', persistent = false) {
        // Implementar toast notification
        // Usar librería como Toastify o implementar custom
    }
    
    playNotificationSound() {
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.play().catch(e => console.log('Audio bloqueado por navegador'));
    }
    
    updateBrowserBadge(text) {
        // Actualizar título del tab
        const originalTitle = document.title;
        document.title = `(${text}) ${originalTitle}`;
    }
    
    // ... más métodos de UI
}

// Inicializar cuando cargue la página
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new OperatorDashboard();
});
```

---

## 🎨 TEMPLATES HTML

### 1. Login

```html
<!-- app/templates/auth/login.html -->

{% extends "auth/base_auth.html" %}

{% block content %}
<div class="min-h-screen flex items-center justify-center bg-gray-100">
    <div class="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold text-gray-900">Ceiba21</h1>
            <p class="text-gray-600 mt-2">Dashboard de Operadores</p>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                <div class="mb-4 p-4 rounded {% if category == 'error' %}bg-red-100 text-red-700{% else %}bg-green-100 text-green-700{% endif %}">
                    {{ message }}
                </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" action="{{ url_for('auth.login') }}">
            <div class="mb-4">
                <label class="block text-gray-700 text-sm font-bold mb-2" for="username">
                    Usuario
                </label>
                <input 
                    class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                    id="username" 
                    name="username" 
                    type="text" 
                    required
                    autofocus
                >
            </div>
            
            <div class="mb-6">
                <label class="block text-gray-700 text-sm font-bold mb-2" for="password">
                    Contraseña
                </label>
                <input 
                    class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                    id="password" 
                    name="password" 
                    type="password" 
                    required
                >
            </div>
            
            <div class="mb-6">
                <label class="flex items-center">
                    <input type="checkbox" name="remember" class="mr-2">
                    <span class="text-sm text-gray-700">Recordarme</span>
                </label>
            </div>
            
            <button 
                class="w-full bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
                type="submit"
            >
                Iniciar Sesión
            </button>
        </form>
    </div>
</div>
{% endblock %}
```

---

### 2. Dashboard principal

```html
<!-- app/templates/operator/dashboard.html -->

{% extends "operator/base.html" %}

{% block content %}
<div class="flex h-screen bg-gray-100">
    
    <!-- Sidebar izquierdo: Lista de órdenes -->
    <div class="w-1/3 bg-white border-r border-gray-200 overflow-y-auto">
        <div class="p-4 border-b border-gray-200">
            <h2 class="text-xl font-bold text-gray-900">Órdenes Pendientes</h2>
            <p class="text-sm text-gray-600">({{ pending_orders|length }})</p>
            
            <!-- Filtros -->
            <div class="mt-4 space-y-2">
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" data-filter="telegram">
                    <span>🔵 Telegram</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" data-filter="whatsapp">
                    <span>🟢 WhatsApp</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" data-filter="webchat">
                    <span>🟡 WebChat</span>
                </label>
            </div>
            
            <!-- Búsqueda -->
            <input 
                type="text" 
                placeholder="Buscar orden..." 
                class="mt-4 w-full px-3 py-2 border border-gray-300 rounded-md"
                id="search-orders"
            >
        </div>
        
        <!-- Lista de órdenes -->
        <div id="orders-list">
            {% for order in pending_orders %}
            {% include 'operator/components/order_card.html' %}
            {% endfor %}
        </div>
    </div>
    
    <!-- Panel principal: Detalle de orden -->
    <div class="flex-1 flex flex-col">
        <div id="order-detail-container" class="flex-1">
            <!-- Aquí se carga el detalle de la orden seleccionada -->
            <div class="flex items-center justify-center h-full text-gray-500">
                <div class="text-center">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 class="mt-2 text-sm font-medium text-gray-900">Selecciona una orden</h3>
                    <p class="mt-1 text-sm text-gray-500">Para ver los detalles y chat</p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Sidebar derecho: Estadísticas (opcional, puede ser colapsable) -->
    <div class="w-64 bg-white border-l border-gray-200 p-4">
        <h3 class="text-lg font-bold text-gray-900 mb-4">Estadísticas Hoy</h3>
        
        <div class="space-y-4">
            <div>
                <p class="text-sm text-gray-600">Completadas</p>
                <p class="text-2xl font-bold text-green-600">{{ stats.completed }}</p>
            </div>
            
            <div>
                <p class="text-sm text-gray-600">Pendientes</p>
                <p class="text-2xl font-bold text-yellow-600">{{ stats.pending }}</p>
            </div>
            
            <div>
                <p class="text-sm text-gray-600">Volumen</p>
                <p class="text-2xl font-bold text-blue-600">${{ "%.2f"|format(stats.total_volume_usd) }}</p>
            </div>
            
            <div>
                <p class="text-sm text-gray-600">Tiempo promedio</p>
                <p class="text-2xl font-bold text-purple-600">
                    {% if stats.average_processing_time %}
                        {{ "%.0f"|format(stats.average_processing_time) }} min
                    {% else %}
                        --
                    {% endif %}
                </p>
            </div>
        </div>
    </div>
    
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/operator_dashboard.js') }}"></script>
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
{% endblock %}
```

---

## 🔐 PERMISOS Y ROLES

### Matriz de permisos:

| Acción | ADMIN | OPERATOR | VIEWER |
|--------|-------|----------|--------|
| Ver órdenes | ✅ | ✅ | ✅ |
| Tomar órdenes | ✅ | ✅ | ❌ |
| Aprobar/rechazar | ✅ | ✅ | ❌ |
| Ver chat | ✅ | ✅ | ✅ |
| Enviar mensajes | ✅ | ✅ | ❌ |
| Ver reportes | ✅ | ✅ | ✅ |
| Gestionar operadores | ✅ | ❌ | ❌ |
| Editar tasas | ✅ | ❌ | ❌ |
| Exportar datos | ✅ | ✅ | ❌ |

### Implementación:

```python
# Decorador para verificar permisos
from functools import wraps
from flask import abort

def require_permission(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.has_permission(permission):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Uso:
@operator_bp.route('/approve-order/<int:order_id>')
@login_required
@require_permission('approve_orders')
def approve_order(order_id):
    # Solo operadores con permiso pueden acceder
    ...
```

---

## 📊 MONITOREO Y ANALYTICS

### Métricas a trackear:

1. **Tiempo promedio de respuesta**
   - Desde que llega orden hasta que operador la toma
   
2. **Tiempo promedio de procesamiento**
   - Desde que operador toma orden hasta que la completa
   
3. **Tasa de completitud**
   - Órdenes completadas / Órdenes totales
   
4. **Órdenes por operador**
   - Ranking de productividad
   
5. **Órdenes por canal**
   - Telegram vs WhatsApp vs WebChat
   
6. **Horarios pico**
   - Cuándo hay más órdenes

### Implementar en dashboard:

```python
@operator_bp.route('/reports')
@login_required
@require_permission('view_reports')
def reports():
    """
    Vista de reportes y analytics.
    """
    from datetime import datetime, timedelta
    
    # Últimos 7 días
    start_date = datetime.now() - timedelta(days=7)
    
    # Órdenes por día
    daily_orders = db.session.query(
        db.func.date(Order.created_at).label('date'),
        db.func.count(Order.id).label('count')
    ).filter(
        Order.created_at >= start_date
    ).group_by('date').all()
    
    # Órdenes por canal
    orders_by_channel = db.session.query(
        Order.channel,
        db.func.count(Order.id)
    ).group_by(Order.channel).all()
    
    # Top operadores
    top_operators = db.session.query(
        Operator.full_name,
        db.func.count(Order.id).label('orders_count')
    ).join(Order).group_by(Operator.id).order_by(
        db.desc('orders_count')
    ).limit(10).all()
    
    return render_template(
        'operator/reports.html',
        daily_orders=daily_orders,
        orders_by_channel=orders_by_channel,
        top_operators=top_operators
    )
```

---

## 🧪 TESTING

### Tests necesarios:

1. **Test de autenticación**
   ```python
   def test_login_success():
       # Login con credenciales correctas
       
   def test_login_fail():
       # Login con credenciales incorrectas
       
   def test_logout():
       # Cerrar sesión
   ```

2. **Test de permisos**
   ```python
   def test_admin_can_access_all():
       # Admin puede acceder a todo
       
   def test_operator_cannot_manage_operators():
       # Operador no puede gestionar otros operadores
       
   def test_viewer_cannot_take_orders():
       # Viewer no puede tomar órdenes
   ```

3. **Test de WebSocket**
   ```python
   def test_websocket_connection():
       # Conectar al WebSocket
       
   def test_new_order_notification():
       # Recibir notificación de nueva orden
       
   def test_message_broadcast():
       # Mensaje se envía correctamente
   ```

4. **Test de acciones**
   ```python
   def test_take_order():
       # Tomar orden correctamente
       
   def test_complete_order():
       # Completar orden y generar transacciones
       
   def test_cancel_order():
       # Cancelar orden con motivo
   ```

---

## 📦 DEPENDENCIAS NECESARIAS

Agregar a `requirements.txt`:

```txt
flask-login==0.6.3
flask-socketio==5.3.6
python-socketio==5.10.0
eventlet==0.33.3  # Para producción con WebSockets
```

---

## 🚀 DESPLIEGUE

### Configuración de producción:

```python
# wsgi.py

from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # Desarrollo
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
else:
    # Producción con eventlet
    import eventlet
    eventlet.monkey_patch()
```

### Systemd service:

```ini
# /etc/systemd/system/ceiba21-dashboard.service

[Unit]
Description=Ceiba21 Dashboard
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=webmaster
WorkingDirectory=/var/www/cotizaciones
Environment="PATH=/var/www/cotizaciones/venv/bin"
ExecStart=/var/www/cotizaciones/venv/bin/gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

**IMPORTANTE:** Con WebSockets, usar solo 1 worker (`-w 1`) con eventlet.

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### 1. Seguridad

- ✅ HTTPS obligatorio para WebSockets
- ✅ CSRF protection en formularios
- ✅ Session timeout (30 minutos inactividad)
- ✅ Rate limiting en endpoints API
- ✅ Sanitizar inputs para prevenir XSS

### 2. Performance

- ✅ Índices en BD (order.status, order.channel, order.operator_id)
- ✅ Caché de estadísticas en Redis (5 minutos)
- ✅ Pagination en lista de órdenes (máximo 50 por página)
- ✅ Lazy loading de imágenes grandes

### 3. UX

- ✅ Indicadores de carga (spinners)
- ✅ Confirmaciones antes de acciones destructivas
- ✅ Atajos de teclado (ej: Ctrl+Enter para enviar mensaje)
- ✅ Responsive (funciona en tablet)
- ✅ Notificaciones no intrusivas

### 4. Escalabilidad

- ✅ WebSockets con Redis como message broker (futuro, si hay múltiples servidores)
- ✅ Separar static files a CDN (futuro)
- ✅ Monitoreo con Sentry para errores

---

## 🎯 CHECKLIST DE IMPLEMENTACIÓN

### Fase 5a: Autenticación (Día 1)

- [ ] Instalar Flask-Login
- [ ] Crear `app/routes/auth.py`
- [ ] Crear template `auth/login.html`
- [ ] Configurar sesiones en Flask
- [ ] Implementar UserMixin en Operator model
- [ ] Testing: Login/logout funciona

### Fase 5b: Dashboard estructura (Día 2)

- [ ] Crear `app/routes/operator_dashboard.py`
- [ ] Crear template `operator/base.html` (layout)
- [ ] Crear template `operator/dashboard.html`
- [ ] Crear componente `order_card.html`
- [ ] Estilos CSS básicos
- [ ] Testing: Dashboard se ve correctamente

### Fase 5c: Lista de órdenes (Día 2-3)

- [ ] Endpoint para obtener órdenes
- [ ] Renderizar lista con filtros
- [ ] Implementar búsqueda
- [ ] Indicadores visuales por canal
- [ ] Ordenar por urgencia (colores)
- [ ] Testing: Filtros y búsqueda funcionan

### Fase 5d: Detalle de orden + chat (Día 3-4)

- [ ] Template `operator/order_detail.html`
- [ ] Mostrar información completa de orden
- [ ] Renderizar historial de chat
- [ ] Campo para enviar mensaje
- [ ] Botones de acciones
- [ ] Testing: Detalle se carga correctamente

### Fase 5e: API endpoints (Día 4)

- [ ] Crear `app/routes/operator_api.py`
- [ ] Endpoint `/api/operator/take-order`
- [ ] Endpoint `/api/operator/complete-order`
- [ ] Endpoint `/api/operator/cancel-order`
- [ ] Endpoint `/api/operator/send-message`
- [ ] Endpoint `/api/operator/orders` (lista dinámica)
- [ ] Testing: Todos los endpoints funcionan

### Fase 5f: WebSockets (Día 5)

- [ ] Instalar Flask-SocketIO
- [ ] Configurar en `app/__init__.py`
- [ ] Implementar eventos: connect, disconnect, ping
- [ ] Funciones de notificación: new_order, order_taken, new_message
- [ ] Cliente JavaScript para WebSocket
- [ ] Testing: Notificaciones en tiempo real funcionan

### Fase 5g: JavaScript interactivo (Día 5-6)

- [ ] Crear `operator_dashboard.js`
- [ ] Clase OperatorDashboard
- [ ] Métodos para acciones (take, complete, cancel, send)
- [ ] UI helpers (notificaciones, modales)
- [ ] Manejo de errores
- [ ] Testing: Interacciones funcionan sin reload

### Fase 5h: Permisos y roles (Día 6)

- [ ] Decorador `@require_permission`
- [ ] Aplicar a todas las rutas sensibles
- [ ] UI condicional según rol
- [ ] Testing: Permisos se respetan

### Fase 5i: Estadísticas y reportes (Día 7)

- [ ] Vista de reportes
- [ ] Gráficos con Chart.js
- [ ] Exportar a Excel
- [ ] Testing: Reportes correctos

### Fase 5j: Testing completo (Día 7)

- [ ] Tests unitarios de rutas
- [ ] Tests de permisos
- [ ] Tests de WebSocket
- [ ] Tests de acciones
- [ ] Testing en navegadores (Chrome, Firefox, Safari)
- [ ] Testing responsive

### Fase 5k: Despliegue

- [ ] Configurar Gunicorn con eventlet
- [ ] Configurar systemd service
- [ ] Configurar Nginx para WebSockets
- [ ] Testing en producción
- [ ] Documentación para operadores

---

## 🆘 TROUBLESHOOTING

### WebSocket no conecta

**Causa:** Nginx mal configurado para WebSockets

**Solución:**
```nginx
# /etc/nginx/sites-available/ceiba21

location /socket.io {
    proxy_pass http://127.0.0.1:5000/socket.io;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

---

### Notificaciones no llegan

**Causa:** Redis no está corriendo o no está configurado como message broker

**Solución:**
```python
# app/__init__.py
socketio.init_app(app, 
    message_queue='redis://localhost:6379/1',
    cors_allowed_origins="*"
)
```

---

### Dashboard lento

**Causa:** Muchas órdenes sin pagination

**Solución:**
```python
# Agregar limit en query
orders = Order.query.filter_by(status=OrderStatus.PENDING)\
    .order_by(Order.created_at.desc())\
    .limit(50)\
    .all()
```

---

## 📖 REFERENCIAS

### Documentación oficial:

- **Flask-Login:** https://flask-login.readthedocs.io/
- **Flask-SocketIO:** https://flask-socketio.readthedocs.io/
- **Socket.IO Client:** https://socket.io/docs/v4/client-api/
- **Tailwind CSS:** https://tailwindcss.com/docs
- **Chart.js:** https://www.chartjs.org/docs/

### Recursos internos:

- Plan completo: `/mnt/user-data/outputs/PLAN_SISTEMA_ORDENES.md`
- Fase 4 (Bot): `/mnt/user-data/outputs/FASE_4_BOT_CONVERSACIONAL.md`

---

## ✅ CRITERIOS DE ÉXITO

Al finalizar la Fase 5, el sistema debe:

1. ✅ Operador puede hacer login en dashboard
2. ✅ Dashboard muestra TODAS las órdenes (Telegram + WhatsApp + WebChat)
3. ✅ Operador puede tomar orden y asignarla a sí mismo
4. ✅ Operador puede ver historial completo del chat
5. ✅ Operador puede responder al cliente desde dashboard
6. ✅ Mensaje del operador llega al canal correcto del cliente
7. ✅ Operador recibe notificaciones en tiempo real de nuevas órdenes
8. ✅ Operador puede marcar orden como pagada
9. ✅ Sistema genera contabilidad automática al completar
10. ✅ Operador puede cancelar orden con motivo
11. ✅ Dashboard funciona sin necesidad de recargar página
12. ✅ Permisos se respetan según rol (ADMIN/OPERATOR/VIEWER)

---

## 🎬 PRÓXIMOS PASOS (FASE 6)

Después de completar la Fase 5, continuaremos con:

**FASE 6: Contabilidad automática y reportes**
- Dashboard financiero
- Exportar a Excel/PDF
- Reportes programados por email
- Gráficos de tendencias

---

**Autor:** Jose (Ceiba21)  
**Asistente:** Claude (Anthropic)  
**Fecha:** Diciembre 2024  
**Versión:** 1.0
