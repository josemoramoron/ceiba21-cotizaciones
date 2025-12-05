# FASE 4: BOT CONVERSACIONAL DE TELEGRAM

## 📋 CONTEXTO

Sistema de órdenes Ceiba21 - Ya completamos Fases 1, 2 y 3.

### Estado completado:
- ✅ **Fase 1:** Modelos (BaseModel, User, Operator, Order, Transaction, Message, WebUser)
- ✅ **Fase 2:** Servicios (OrderService, CalculatorService, AuthService, NotificationService)
- ✅ **Fase 3:** Canales (BaseChannel, TelegramChannel, WhatsAppChannel, WebChatChannel, ChannelFactory)

### Objetivo de esta fase:
Crear un bot conversacional de Telegram que guíe al cliente paso a paso para crear órdenes completas.

---

## 🎯 FLUJO A IMPLEMENTAR

### 1. Comando /start
Usuario escribe `/start` y recibe saludo con opciones del menú principal.

### 2. Menú principal
Bot presenta opciones:
- 💱 **Nueva operación**
- 📊 **Cotizaciones** (enlace a ceiba21.com/cotizaciones)
- 🧮 **Calculadora** (enlace a ceiba21.com/calculadora)
- 📋 **Condiciones de uso** (enlace a ceiba21.com/condiciones)
- 💬 **Ayuda**

### 3. Si selecciona "Nueva operación":

**a. Selección de moneda destino**
- ¿Qué moneda recibirás? 
- Botones: VES, COP, CLP, ARS

**b. Selección de método de pago origen**
- ¿Método de pago de origen?
- Botones: PayPal, Zelle, USDT

**c. Ingreso de cantidad**
- ¿Qué cantidad ENVIARÁS?
- Input numérico (en USD)

**d. Confirmación del cálculo**
- Mostrar cálculo (con descuento de comisión si aplica)
- Botones: ✅ Sí / ❌ No

**e. Solicitud de datos de pago**
- Banco
- Número de cuenta
- Nombre del titular
- Cédula/DNI

**f. Instrucciones de pago**
- Proporcionar datos de Ceiba21 para que cliente realice el pago

**g. Espera de comprobante**
- Cliente envía imagen del comprobante

**h. Confirmación**
- Confirmar recepción
- Notificar a operadores

---

## 🏗️ ARQUITECTURA

### Componentes a crear:

1. **ConversationState** (Enum con estados)
2. **ConversationHandler** (clase principal - FSM)
3. **MessageParser** (validaciones de input)
4. **ResponseTemplates** (mensajes del bot)

---

## 📁 ARCHIVOS A CREAR

```
app/bot/
├── __init__.py
├── conversation_handler.py
├── states.py
├── message_parser.py
└── responses.py
```

---

## 📝 ARCHIVOS A MODIFICAR

- `app/telegram/bot.py` (integrar ConversationHandler)

---

## 🔧 REQUISITOS TÉCNICOS

### 1. app/bot/states.py

```python
from enum import Enum

class ConversationState(Enum):
    START = 'start'
    MAIN_MENU = 'main_menu'
    SELECT_CURRENCY = 'select_currency'
    SELECT_METHOD_FROM = 'select_method_from'
    SELECT_METHOD_TO = 'select_method_to'
    ENTER_AMOUNT = 'enter_amount'
    CONFIRM_CALCULATION = 'confirm_calculation'
    ENTER_BANK = 'enter_bank'
    ENTER_ACCOUNT = 'enter_account'
    ENTER_HOLDER = 'enter_holder'
    ENTER_DNI = 'enter_dni'
    AWAIT_PROOF = 'await_proof'
    MANUAL_ATTENTION = 'manual_attention'  # Operador intervino manualmente
    COMPLETED = 'completed'
```

---

### 2. app/bot/conversation_handler.py

**Clase principal con:**

#### Métodos principales:
- `handle_message(user, message, current_state)` → Procesar input del usuario
- `transition_to(new_state)` → Cambiar estado de la conversación
- `transfer_to_operator(order, reason)` → Transferir a atención manual

#### Integraciones:
- OrderService para crear/actualizar órdenes
- CalculatorService para mostrar cálculos
- Redis para guardar estado de conversación
- Verificar si bot está activo antes de procesar (`bot_enabled` flag)

---

### 3. app/bot/message_parser.py

**Validaciones:**
- `validate_amount(text)` → Verificar que sea número válido
- `validate_account(text)` → Formato de cuenta bancaria
- `validate_dni(text)` → Formato de cédula/DNI
- `parse_selection(text, options)` → Botón clickeado

---

### 4. app/bot/responses.py

**Templates de mensajes:**
- `welcome_message()` → Mensaje /start con menú principal
- `main_menu_message()` → Opciones principales
- `help_message()` → Información de ayuda
- `select_currency_message(currencies)` → Con botones
- `calculation_summary(calculation_data)` → Resumen formateado
- `request_payment_data_message()` → Instrucciones
- `payment_info_message(order)` → Datos de Ceiba21
- `proof_received_message(order)` → Confirmación
- `transferred_to_operator_message()` → Cuando se pasa a manual

---

## 💰 LÓGICA DE COMISIONES

### PayPal (caso especial)

PayPal es el ÚNICO método que cobra comisión de plataforma.

**Flujo:**
1. Cliente dice cuánto ENVIARÁ (ej: $100)
2. Sistema calcula comisión PayPal (5.4% + $0.30)
3. Sistema muestra monto NETO que recibiremos
4. **Fórmula:** `neto = (monto_enviado - 0.30) / 1.054`

**Ejemplo:**
```
Cliente envía: $100.00 USD
Comisión PayPal: -$5.70 USD
Ceiba21 recibe: $94.30 USD
```

---

### Otros métodos (Zelle, USDT, etc.)

**NO cobran comisión de plataforma:**
- Lo que envía = lo que recibimos
- Cliente debe asumir cualquier comisión de su banco/plataforma

**Mensaje aclaratorio:**
```
⚠️ Nota: Si tu banco o plataforma cobra comisión por la transferencia, 
esta corre por tu cuenta. Solo te pagaremos el monto neto que recibamos.
```

---

## 🔄 REUTILIZAR CalculatorService

**IMPORTANTE:** NO reimplementar la lógica de cálculo. Usar el servicio existente.

```python
from app.services.calculator_service import CalculatorService

# Para calcular (ya maneja PayPal correctamente)
result = CalculatorService.calculate_exchange(
    amount_usd=amount,  # Lo que el cliente ENVIARÁ
    currency_id=currency_id,
    payment_method_id=payment_method_id
)

# result contiene:
# {
#     'amount_usd': Decimal('100.00'),      # Lo que enviará
#     'fee_usd': Decimal('5.70'),           # Comisión (si PayPal)
#     'net_usd': Decimal('94.30'),          # Lo que recibiremos
#     'exchange_rate': Decimal('305.50'),
#     'amount_local': Decimal('28808.65'),  # Bolívares que recibirá
#     'currency_code': 'VES'
# }

# Si el método NO tiene comisión (Zelle, USDT):
# fee_usd será 0.00 y net_usd = amount_usd
```

**TODA la información viene DINÁMICAMENTE de la base de datos:**
- Tasas de cambio
- Métodos de pago
- Comisiones
- Monedas disponibles

**NO hardcodear valores.**

---

## 🛑 CONTROL DEL BOT (Admin)

### 1. Variable de control en Redis

```python
# Activar/desactivar bot
redis_client.set('bot_enabled', '1')  # 1 = activo, 0 = detenido

# Verificar antes de procesar
def is_bot_enabled():
    return redis_client.get('bot_enabled') == '1'
```

---

### 2. Comandos admin para controlar bot

```python
# Solo operadores ADMIN pueden ejecutar

@admin_required
def stop_bot_command(update, context):
    redis_client.set('bot_enabled', '0')
    update.message.reply_text('🛑 Bot detenido. Las conversaciones se pausarán.')

@admin_required
def start_bot_command(update, context):
    redis_client.set('bot_enabled', '1')
    update.message.reply_text('✅ Bot activado.')
```

---

### 3. Mensaje cuando bot está detenido

```python
def handle_message_when_disabled(update, context):
    update.message.reply_text(
        '⚠️ El bot está temporalmente deshabilitado.\n'
        'Un operador te atenderá pronto.\n\n'
        'Para contacto inmediato: @ceiba21_soporte'
    )
```

---

## 👤 INTERVENCIÓN MANUAL DE OPERADOR

### 1. Comando para operador tomar conversación

```python
# Desde dashboard o Telegram del operador
/takeover ORDER_ID

# Esto hace:
# - Pausar bot automático para esa orden
# - Cambiar estado a MANUAL_ATTENTION
# - Notificar al cliente: "Un operador te atenderá personalmente"
# - Todos los mensajes siguientes van directo a operador
```

---

### 2. Implementación en ConversationHandler

```python
def handle_message(self, user, message, current_state):
    # Verificar si bot está activo
    if not is_bot_enabled():
        return self.bot_disabled_response()
    
    # Verificar si conversación está en modo manual
    if current_state == ConversationState.MANUAL_ATTENTION:
        # No procesar automáticamente, guardar en Message
        self.save_message_for_operator(user, message)
        return {'text': 'Tu mensaje fue recibido. Un operador lo revisará.'}
    
    # Procesar normalmente
    ...
```

---

### 3. Tracking de intervención manual

```python
# Guardar quién está atendiendo manualmente
redis_client.setex(
    f'manual_order:{order.id}',
    7200,  # 2 horas
    operator.id
)
```

---

## 🔗 INTEGRACIÓN CON BOT EXISTENTE

Actualmente tenemos en `app/telegram/bot.py` un bot que solo publica tasas.

### Necesitamos:

1. ✅ Mantener funcionalidad de publicación (no tocar)
2. ✅ Agregar nuevos handlers para conversación
3. ✅ Agregar comandos de control para admin/operadores
4. ✅ Usar python-telegram-bot `CommandHandler` y `MessageHandler`

---

### Ejemplo de estructura en bot.py:

```python
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from app.bot.conversation_handler import ConversationHandler as ConvHandler
from app.services.auth_service import AuthService

# ==========================================
# HANDLERS EXISTENTES (MANTENER)
# ==========================================
dispatcher.add_handler(CommandHandler('publicar', publicar_tasas))

# ==========================================
# NUEVOS HANDLERS PARA CONVERSACIÓN
# ==========================================
conv_handler = ConvHandler()

def start_command(update, context):
    user = get_or_create_user_from_telegram(update.message.from_user)
    response = conv_handler.handle_message(user, '/start', None)
    update.message.reply_text(response['text'], reply_markup=response.get('buttons'))

def message_handler(update, context):
    # Verificar si bot está activo
    if not is_bot_enabled():
        handle_message_when_disabled(update, context)
        return
    
    user = get_or_create_user_from_telegram(update.message.from_user)
    current_state = get_user_state(user)
    response = conv_handler.handle_message(user, update.message.text, current_state)
    update.message.reply_text(response['text'], reply_markup=response.get('buttons'))

def photo_handler(update, context):
    # Manejar comprobantes de pago
    user = get_or_create_user_from_telegram(update.message.from_user)
    current_state = get_user_state(user)
    
    if current_state == ConversationState.AWAIT_PROOF:
        # Descargar imagen
        photo_file = update.message.photo[-1].get_file()
        photo_url = save_proof_to_storage(photo_file)
        
        response = conv_handler.handle_proof(user, photo_url)
        update.message.reply_text(response['text'])

# ==========================================
# COMANDOS DE CONTROL (SOLO ADMIN)
# ==========================================

def stop_bot_command(update, context):
    telegram_id = update.message.from_user.id
    operator = Operator.query.filter_by(telegram_notification_id=telegram_id).first()
    
    if not operator or operator.role != OperatorRole.ADMIN:
        update.message.reply_text('❌ No tienes permisos.')
        return
    
    redis_client.set('bot_enabled', '0')
    update.message.reply_text('🛑 Bot detenido.')

def start_bot_command(update, context):
    telegram_id = update.message.from_user.id
    operator = Operator.query.filter_by(telegram_notification_id=telegram_id).first()
    
    if not operator or operator.role != OperatorRole.ADMIN:
        update.message.reply_text('❌ No tienes permisos.')
        return
    
    redis_client.set('bot_enabled', '1')
    update.message.reply_text('✅ Bot activado.')

def takeover_command(update, context):
    # /takeover ORD-20251204-001
    telegram_id = update.message.from_user.id
    operator = Operator.query.filter_by(telegram_notification_id=telegram_id).first()
    
    if not operator:
        update.message.reply_text('❌ No estás registrado como operador.')
        return
    
    if len(context.args) < 1:
        update.message.reply_text('Uso: /takeover ORD-20251204-001')
        return
    
    order_reference = context.args[0]
    order = Order.query.filter_by(reference=order_reference).first()
    
    if not order:
        update.message.reply_text('❌ Orden no encontrada.')
        return
    
    # Transferir a atención manual
    conv_handler.transfer_to_operator(order, operator)
    update.message.reply_text(f'✅ Atendiendo manualmente orden {order_reference}')

# ==========================================
# REGISTRAR HANDLERS
# ==========================================
dispatcher.add_handler(CommandHandler('start', start_command))
dispatcher.add_handler(CommandHandler('stopbot', stop_bot_command))
dispatcher.add_handler(CommandHandler('startbot', start_bot_command))
dispatcher.add_handler(CommandHandler('takeover', takeover_command))
dispatcher.add_handler(MessageHandler(Filters.photo, photo_handler))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
dispatcher.add_handler(CallbackQueryHandler(button_callback_handler))
```

---

## 💾 GESTIÓN DE ESTADO

**Usar Redis para guardar estado temporal de conversación:**

```python
# Guardar estado
redis_client.setex(f'conv_state:{user.id}', 3600, state.value)

# Guardar datos temporales de la conversación
redis_client.setex(f'conv_data:{user.id}', 3600, json.dumps(data))

# Obtener estado
state_str = redis_client.get(f'conv_state:{user.id}')
current_state = ConversationState(state_str) if state_str else None

# Obtener datos
data_str = redis_client.get(f'conv_data:{user.id}')
conv_data = json.loads(data_str) if data_str else {}
```

**Ventajas de Redis:**
- ⚡ Rápido (en memoria)
- 🔄 TTL automático (expira después de 1 hora)
- 📊 Ligero (no sobrecarga PostgreSQL)

---

## 🛠️ FUNCIONES AUXILIARES NECESARIAS

### 1. get_or_create_user_from_telegram(telegram_user)
- Buscar `User` por `telegram_id`
- Si no existe, crear con `User.create_from_channel('telegram', data)`

### 2. create_order_draft(user, conversation_data)
- Usar `OrderService.create_order()`
- Estado inicial: `DRAFT`

### 3. format_buttons(options, callback_prefix)
- Convertir lista de opciones a `InlineKeyboardMarkup` de Telegram

### 4. is_bot_enabled()
- Verificar flag en Redis

### 5. save_proof_to_storage(photo_file)
- Guardar imagen en servidor
- Retornar URL pública

---

## 📱 EJEMPLO DE FLUJO COMPLETO

### Escenario 1: Nueva operación con PayPal (con comisión)

```
Usuario: /start

Bot: 
¡Hola! 👋 Bienvenido a Ceiba21 🌳
Cambio de divisas rápido y seguro.

¿Qué deseas hacer?
[💱 Nueva operación]
[📊 Ver cotizaciones]
[🧮 Calculadora]
[📋 Condiciones de uso]
[💬 Ayuda]

---

Usuario: Click en "Nueva operación"

Bot:
Perfecto! Vamos a crear tu operación.

¿Qué moneda recibirás?
[🇻🇪 Bolívares VES] [🇨🇴 Pesos COP]
[🇨🇱 Pesos CLP] [🇦🇷 Pesos ARS]

---

Usuario: Click en "Bolívares VES"

Bot:
Excelente! Recibirás Bolívares 🇻🇪

¿Método de pago de origen?
[💳 PayPal] [💵 Zelle] [₿ USDT]

---

Usuario: Click en "PayPal"

Bot:
¿Qué cantidad enviarás? 💵

Ejemplo: 100

---

Usuario: "100"

Bot:
📊 RESUMEN
━━━━━━━━━━━
Si me envías: $100.00 USD
Comisión PayPal: -$5.70 USD
Recibiré: $94.30 USD (PayPal)
Recibirás: 28,808.65 Bs
Tasa aplicada: 305.50 Bs/$
━━━━━━━━━━━
¿Confirmas? [✅ Sí] [❌ No]

---

Usuario: Click "Sí"

Bot:
Excelente! 📋

Para que te enviemos los bolívares, necesito:

📌 Datos de tu cuenta:
1. Banco
2. Número de cuenta
3. Titular
4. Cédula/DNI

Empecemos: ¿Cuál es tu banco?

---

Usuario: "Banco Venezuela"

Bot:
¿Número de cuenta?
(20 dígitos sin espacios ni guiones)

---

Usuario: "01020123456789012345"

Bot:
¿Nombre completo del titular de la cuenta?

---

Usuario: "Juan Pérez"

Bot:
¿Cédula o DNI del titular?
(Formato: V-12345678 o E-12345678)

---

Usuario: "V-12345678"

Bot:
Perfecto! ✅ Datos verificados

📋 ORDEN: ORD-20251204-001

Ahora envía tu pago de PayPal a:
━━━━━━━━━━━
💳 PayPal: ceiba21@paypal.com
💰 Monto EXACTO: $100.00 USD
📝 Orden: ORD-20251204-001
━━━━━━━━━━━

⚠️ IMPORTANTE:
- Verifica el monto exacto
- Envía como "Bienes y Servicios" o "Amigos y Familia" según prefieras
- Guarda el comprobante

Una vez realizado el pago, envía la captura de pantalla del comprobante.

---

Usuario: [envía imagen]

Bot:
✅ Comprobante recibido!

📋 Orden: ORD-20251204-001
⏳ Estado: Verificando pago

Un operador verificará tu pago y realizará la transferencia en breve.
Te notificaremos cuando tus bolívares estén en camino.

Tiempo estimado: 10-30 minutos

Gracias por usar Ceiba21 💚
```

**Sistema automáticamente:**
- Orden → estado `PENDING`
- Guarda comprobante
- Notifica a operadores en canal privado con botones:
  - [✅ Tomar orden]
  - [❌ Rechazar]
  - [👤 Contactar cliente]

---

### Escenario 2: Nueva operación con Zelle (sin comisión)

```
Usuario: Click en "Zelle"

Bot:
¿Qué cantidad enviarás? 💵

⚠️ Nota: Si tu banco cobra comisión por la transferencia, 
esta corre por tu cuenta. Solo te pagaremos el monto neto 
que recibamos.

Ejemplo: 100

---

Usuario: "100"

Bot:
📊 RESUMEN
━━━━━━━━━━━
Si me envías: $100.00 USD (Zelle)
Recibiré: $100.00 USD
Recibirás: 30,550.00 Bs
Tasa aplicada: 305.50 Bs/$
━━━━━━━━━━━
¿Confirmas? [✅ Sí] [❌ No]
```

*El resto del flujo continúa igual (solicitud de datos bancarios, etc.)*

---

## 📜 COMANDOS DISPONIBLES

### Comandos para usuarios:

- `/start` - Iniciar conversación y ver menú principal
- `/status` - Ver estado de mi última orden
- `/cancel` - Cancelar conversación actual
- `/help` - Ayuda y soporte

### Comandos para administradores:

- `/stopbot` - Detener bot (solo ADMIN)
- `/startbot` - Activar bot (solo ADMIN)

### Comandos para operadores:

- `/takeover ORDER_ID` - Tomar conversación manualmente (ej: `/takeover ORD-20251204-001`)

---

## ⚠️ MANEJO DE ERRORES Y CASOS ESPECIALES

### 1. Usuario envía texto cuando se esperan botones

```
Bot: "Por favor usa los botones de arriba ☝️"
```

---

### 2. Usuario envía número inválido

```
Bot: 
❌ Monto inválido. Ingresa solo números.

Ejemplo: 100 o 50.50
```

---

### 3. Usuario tarda más de 30 minutos

```
Bot:
⏱️ Por inactividad, tu conversación ha expirado.
Escribe /start para comenzar de nuevo.
```

**Acción del sistema:**
- Eliminar estado de Redis
- Limpiar datos temporales
- Si había orden DRAFT, mantenerla (no eliminar)

---

### 4. Bot deshabilitado por admin

```
Bot:
⚠️ El servicio está temporalmente en mantenimiento.
Un operador te atenderá pronto.

Para urgencias: @ceiba21_soporte
```

---

### 5. Usuario intenta crear nueva orden con una activa

```
Bot:
⚠️ Ya tienes una orden en proceso: ORD-20251204-001

Estado: Verificando pago

¿Deseas:
[📋 Ver estado] [❌ Cancelar orden] [✨ Nueva orden de todas formas]
```

---

### 6. Usuario envía comprobante en formato incorrecto

```
Bot:
❌ Por favor envía una IMAGEN (captura de pantalla).

Formatos válidos: JPG, PNG

No envíes archivos PDF o documentos.
```

---

### 7. Operador toma conversación manualmente

```
Bot (al cliente):
👤 Un operador está revisando tu caso personalmente.

Te responderemos en breve.
```

**Sistema:**
- Estado → `MANUAL_ATTENTION`
- Pausar bot automático para este usuario
- Todos los mensajes siguientes se guardan en tabla `messages`
- Operador ve mensajes en dashboard

---

## 🧪 TESTING

### Script de prueba

Crear: `scripts/test_bot_conversation.py`

**Objetivos del script:**
1. Simular flujo completo sin usuario real
2. Probar transiciones de estados
3. Validar cálculos con CalculatorService
4. Verificar guardado en Redis
5. Comprobar creación de orden DRAFT → PENDING

**Ejemplo básico:**

```python
from app.bot.conversation_handler import ConversationHandler
from app.bot.states import ConversationState
from app.models.user import User

def test_complete_flow():
    # Crear usuario de prueba
    user = User.create_from_channel('telegram', {
        'telegram_id': 123456789,
        'first_name': 'Test',
        'last_name': 'User'
    })
    
    conv = ConversationHandler()
    
    # 1. Start
    response = conv.handle_message(user, '/start', None)
    assert response['text'].startswith('¡Hola!')
    assert 'buttons' in response
    
    # 2. Nueva operación
    response = conv.handle_message(user, 'nueva_operacion', ConversationState.MAIN_MENU)
    assert 'moneda' in response['text'].lower()
    
    # 3. Seleccionar VES
    # ... continuar con todo el flujo
    
    print("✅ Test completo exitoso")

if __name__ == '__main__':
    test_complete_flow()
```

---

## 📌 NOTAS IMPORTANTES

### ✅ Principios a seguir:

1. **Mensajes concisos y claros** - No abrumar al usuario con texto
2. **Emojis para mejor UX** - Usar apropiadamente, no en exceso
3. **Validar cada input** - Antes de avanzar al siguiente estado
4. **Manejar errores gracefully** - Mensajes amigables, no técnicos
5. **Timeout de conversación** - 30 minutos de inactividad → resetear estado

### ⚠️ Restricciones críticas:

1. **REUTILIZAR CalculatorService** - NO reimplementar lógica de cálculo
2. **TODO de base de datos** - NO hardcodear valores de tasas, métodos o monedas
3. **PayPal es el ÚNICO con comisión de plataforma** - Otros métodos NO cobran
4. **Control del bot por admin** - Debe poder detenerlo/activarlo cuando sea necesario
5. **Intervención manual de operadores** - Permitir tomar conversaciones cuando sea necesario

### 🔒 Seguridad:

1. **Validar permisos** - Solo ADMIN puede detener/activar bot
2. **Validar operadores** - Solo operadores registrados pueden usar `/takeover`
3. **Sanitizar inputs** - Limpiar datos antes de guardar
4. **No exponer datos sensibles** - Enmascarar números de cuenta en logs
5. **Rate limiting** - Prevenir spam (opcional, futuro)

---

## 📚 ESTRUCTURA DE DATOS EN REDIS

### Estado de conversación

```
Key: conv_state:{user.id}
Value: "select_currency"
TTL: 3600 segundos (1 hora)
```

### Datos temporales

```
Key: conv_data:{user.id}
Value: {
    "currency_id": 1,
    "payment_method_from_id": 2,
    "amount_usd": 100.00,
    "bank": "Banco Venezuela",
    "account": "01020123456789012345",
    "holder": "Juan Pérez",
    "dni": "V-12345678"
}
TTL: 3600 segundos (1 hora)
```

### Control del bot

```
Key: bot_enabled
Value: "1" (activo) o "0" (detenido)
TTL: Sin expiración
```

### Orden en atención manual

```
Key: manual_order:{order.id}
Value: {operator.id}
TTL: 7200 segundos (2 horas)
```

---

## 🎨 FORMATO DE BOTONES EN TELEGRAM

### Botones inline (InlineKeyboardMarkup)

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Ejemplo: Selección de moneda
buttons = [
    [
        InlineKeyboardButton("🇻🇪 Bolívares VES", callback_data="currency:1"),
        InlineKeyboardButton("🇨🇴 Pesos COP", callback_data="currency:2")
    ],
    [
        InlineKeyboardButton("🇨🇱 Pesos CLP", callback_data="currency:3"),
        InlineKeyboardButton("🇦🇷 Pesos ARS", callback_data="currency:4")
    ]
]

reply_markup = InlineKeyboardMarkup(buttons)
```

### Callback data format

```
Formato: "accion:parametro"

Ejemplos:
- "currency:1" → Seleccionar moneda ID 1 (VES)
- "method_from:2" → Seleccionar método origen ID 2 (PayPal)
- "confirm:yes" → Confirmar cálculo
- "confirm:no" → Rechazar cálculo
```

---

## 🔄 DIAGRAMA DE ESTADOS (FSM)

```
START
  ↓
MAIN_MENU
  ↓
SELECT_CURRENCY
  ↓
SELECT_METHOD_FROM
  ↓
ENTER_AMOUNT
  ↓
CONFIRM_CALCULATION
  ↓ (si confirma)
ENTER_BANK
  ↓
ENTER_ACCOUNT
  ↓
ENTER_HOLDER
  ↓
ENTER_DNI
  ↓
AWAIT_PROOF
  ↓
COMPLETED

Salidas alternativas:
- Desde cualquier estado → MANUAL_ATTENTION (operador interviene)
- Desde CONFIRM_CALCULATION (si rechaza) → ENTER_AMOUNT
- Timeout → START (reiniciar)
```

---

## 📦 DEPENDENCIAS NECESARIAS

Verificar que estén en `requirements.txt`:

```txt
python-telegram-bot==13.15
redis==5.0.1
Pillow==10.1.0  # Para procesar imágenes
```

---

## 🚀 DESPLIEGUE Y CONFIGURACIÓN

### Variables de entorno (.env)

```bash
# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_OPERATORS_CHANNEL_ID=-1001234567890

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# URLs
DASHBOARD_URL=https://ceiba21.com
```

### Iniciar bot

```bash
cd /var/www/cotizaciones
source venv/bin/activate
python -m app.telegram.bot
```

### Verificar Redis

```bash
redis-cli
> GET bot_enabled
"1"
> KEYS conv_state:*
1) "conv_state:123456789"
```

---

## 📊 MÉTRICAS A MONITOREAR

### KPIs del bot:

1. **Tasa de conversión**
   - Usuarios que inician conversación vs. completan orden
   
2. **Tiempo promedio de conversación**
   - Desde /start hasta envío de comprobante
   
3. **Abandonos por etapa**
   - ¿En qué estado los usuarios abandonan más?
   
4. **Errores comunes**
   - Inputs inválidos más frecuentes
   
5. **Intervenciones manuales**
   - Cantidad de veces que operador debe intervenir

### Logs importantes:

```python
import logging

logger = logging.getLogger('bot')

# Registrar eventos clave
logger.info(f"User {user.id} started conversation")
logger.info(f"User {user.id} completed order {order.reference}")
logger.warning(f"User {user.id} sent invalid amount: {message}")
logger.error(f"Failed to calculate: {error}")
```

---

## 🎯 CHECKLIST DE IMPLEMENTACIÓN

### Fase 4a: Estructura base (Día 1)

- [ ] Crear `app/bot/__init__.py`
- [ ] Crear `app/bot/states.py` con ConversationState
- [ ] Crear `app/bot/message_parser.py` con validaciones básicas
- [ ] Crear `app/bot/responses.py` con templates de mensajes
- [ ] Testing: Importar módulos sin errores

### Fase 4b: ConversationHandler (Día 2)

- [ ] Crear clase `ConversationHandler`
- [ ] Implementar `handle_message()`
- [ ] Implementar `transition_to()`
- [ ] Integrar con Redis para estado
- [ ] Testing: Transiciones de estados

### Fase 4c: Integración con servicios (Día 2-3)

- [ ] Integrar `CalculatorService`
- [ ] Integrar `OrderService`
- [ ] Integrar `UserService`
- [ ] Testing: Cálculos correctos

### Fase 4d: Handlers de Telegram (Día 3)

- [ ] Modificar `app/telegram/bot.py`
- [ ] Agregar `start_command`
- [ ] Agregar `message_handler`
- [ ] Agregar `photo_handler`
- [ ] Agregar `button_callback_handler`
- [ ] Testing: Bot responde correctamente

### Fase 4e: Control y gestión (Día 3-4)

- [ ] Implementar `is_bot_enabled()`
- [ ] Agregar comando `/stopbot`
- [ ] Agregar comando `/startbot`
- [ ] Agregar comando `/takeover`
- [ ] Implementar `transfer_to_operator()`
- [ ] Testing: Control de bot funciona

### Fase 4f: Almacenamiento y persistencia (Día 4)

- [ ] Función `save_proof_to_storage()`
- [ ] Guardar mensajes en tabla `messages`
- [ ] Crear órdenes DRAFT
- [ ] Transición DRAFT → PENDING
- [ ] Testing: Órdenes se crean correctamente

### Fase 4g: Notificaciones (Día 4)

- [ ] Notificar operadores cuando llega comprobante
- [ ] Enviar mensaje al canal privado de operadores
- [ ] Botones inline para operadores
- [ ] Testing: Notificaciones llegan

### Fase 4h: Testing completo (Día 5)

- [ ] Crear `scripts/test_bot_conversation.py`
- [ ] Flujo completo con PayPal
- [ ] Flujo completo con Zelle
- [ ] Manejo de errores
- [ ] Timeout de conversación
- [ ] Intervención manual
- [ ] Bot deshabilitado

### Fase 4i: Documentación y despliegue

- [ ] Documentar comandos en README
- [ ] Agregar logs importantes
- [ ] Configurar systemd service (si aplica)
- [ ] Testing en producción con usuarios reales

---

## 🆘 TROUBLESHOOTING

### Bot no responde

**Posibles causas:**
1. Token de Telegram incorrecto → Verificar `.env`
2. Bot no está corriendo → Verificar proceso
3. Redis no está activo → `systemctl status redis`
4. Bot deshabilitado → Verificar `redis-cli GET bot_enabled`

**Solución:**
```bash
# Verificar proceso
ps aux | grep bot

# Revisar logs
tail -f logs/bot.log

# Verificar Redis
redis-cli ping
```

---

### Usuario atascado en un estado

**Causa:** Estado en Redis corrupto o no expira

**Solución:**
```bash
redis-cli
> DEL conv_state:123456789
> DEL conv_data:123456789
```

---

### Cálculos incorrectos

**Causa:** CalculatorService no está funcionando correctamente

**Solución:**
1. Verificar que tasas estén actualizadas en BD
2. Verificar fórmula de PayPal en `payment_methods` table
3. Revisar logs de CalculatorService

---

### Imágenes no se guardan

**Causa:** Permisos de escritura en directorio

**Solución:**
```bash
# Verificar permisos
ls -la /var/www/cotizaciones/static/uploads

# Corregir si es necesario
sudo chown -R webmaster:webmaster /var/www/cotizaciones/static/uploads
sudo chmod 755 /var/www/cotizaciones/static/uploads
```

---

## 📖 REFERENCIAS

### Documentación oficial:

- **python-telegram-bot:** https://docs.python-telegram-bot.org/
- **Telegram Bot API:** https://core.telegram.org/bots/api
- **Redis Python:** https://redis-py.readthedocs.io/
- **Flask:** https://flask.palletsprojects.com/

### Recursos internos:

- Plan completo: `/mnt/user-data/outputs/PLAN_SISTEMA_ORDENES.md`
- Chat de referencia: Buscar conversación "ceiba21.com"
- Calculadora existente: `app/services/calculator_service.py`

---

## ✅ CRITERIOS DE ÉXITO

Al finalizar la Fase 4, el sistema debe:

1. ✅ Usuario puede crear orden completa desde Telegram
2. ✅ Bot calcula correctamente con comisión PayPal
3. ✅ Bot maneja métodos sin comisión (Zelle, USDT)
4. ✅ Usuario recibe instrucciones claras de pago
5. ✅ Usuario puede enviar comprobante (imagen)
6. ✅ Sistema crea orden y notifica a operadores
7. ✅ Admin puede detener/activar bot
8. ✅ Operador puede intervenir manualmente
9. ✅ Conversación expira después de 30 min inactividad
10. ✅ Todo funciona sin hardcodear valores

---

## 🎬 PRÓXIMOS PASOS (FASE 5)

Después de completar la Fase 4, continuaremos con:

**FASE 5: Dashboard de operadores**
- Vista unificada de todas las órdenes
- Chat en vivo con clientes desde dashboard
- Acciones: aprobar, rechazar, contactar
- Notificaciones push con WebSockets

---

**Autor:** Jose (Ceiba21)  
**Asistente:** Claude (Anthropic)  
**Fecha:** Diciembre 2024  
**Versión:** 1.0