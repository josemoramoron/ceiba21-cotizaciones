# SOLUCIÓN AL ERROR DEL BOT DE TELEGRAM

## 🔍 DIAGNÓSTICO DEL PROBLEMA

El error **"Entity namespace for currencies has no property is_active"** es un problema **muy común** cuando mezclas:

1. **Flask-SQLAlchemy** (síncrono)
2. **python-telegram-bot v20+** (asíncrono con async/await)
3. **Objetos SQLAlchemy pasados entre contextos**

---

## ❌ El Problema Raíz

Cuando haces esto:

```python
# En conversation_handler.py
currencies = Currency.query.all()  # Objetos SQLAlchemy
return {
    'currencies': currencies  # ❌ Pasas objetos con lazy loading
}
```

Y luego en el handler asíncrono de Telegram:

```python
async def handle_callback(update, context):
    currencies = response['currencies']
    for c in currencies:
        text = c.name  # ❌ BOOM! Ya no hay sesión DB activa
```

### ¿Por qué falla?

El objeto `Currency` tiene **lazy loading** - no carga todos sus atributos hasta que los accedes. 

Pero cuando los accedes desde el contexto async del bot de Telegram, **la sesión de SQLAlchemy ya no existe**.

---

## ✅ SOLUCIÓN DEFINITIVA (Simple)

La solución NO requiere refactoring masivo. Solo necesitas **serializar los datos antes de salir del contexto de Flask**.

---

## 📝 IMPLEMENTACIÓN PASO A PASO

### Paso 1: Modificar `conversation_handler.py`

```python
# app/bot/conversation_handler.py

def handle_message(self, user, message, current_state):
    """
    CRÍTICO: Retornar SOLO datos primitivos (dict, str, int, bool)
    NUNCA objetos SQLAlchemy
    """
    
    if message == '/start' or current_state is None:
        # ❌ MAL - Retornar objetos
        # currencies = Currency.query.filter_by(is_active=True).all()
        # return {'currencies': currencies}
        
        # ✅ BIEN - Serializar a dict
        currencies = Currency.query.filter_by(is_active=True).all()
        currencies_data = [
            {
                'id': c.id,
                'code': c.code,
                'name': c.name,
                'symbol': c.symbol
            }
            for c in currencies
        ]
        
        return {
            'text': ResponseTemplates.select_currency_message(),
            'buttons': self._format_currency_buttons(currencies_data)
        }
    
    # Para SELECT_CURRENCY
    if current_state == ConversationState.SELECT_CURRENCY:
        # Validar selección
        currency = Currency.query.filter_by(id=int(message)).first()
        
        if not currency:
            return {
                'text': 'Moneda inválida. Intenta de nuevo.',
                'buttons': None
            }
        
        # Guardar en Redis SERIALIZADO
        self._save_conversation_data(user.id, 'currency', {
            'id': currency.id,
            'code': currency.code,
            'name': currency.name
        })
        
        # Obtener métodos de pago y SERIALIZAR
        payment_methods = PaymentMethod.query.filter_by(
            is_active=True,
            is_origin=True
        ).all()
        
        methods_data = [
            {
                'id': pm.id,
                'name': pm.name,
                'type': pm.type
            }
            for pm in payment_methods
        ]
        
        return {
            'text': ResponseTemplates.select_method_message(),
            'buttons': self._format_method_buttons(methods_data)
        }
    
    # Continuar con otros estados...
```

---

### Paso 2: Modificar `responses.py`

```python
# app/bot/responses.py

class ResponseTemplates:
    """
    Templates de mensajes del bot.
    
    REGLA CRÍTICA: NO hacer queries a la BD aquí.
    Solo retornar strings estáticos o con parámetros.
    """
    
    @staticmethod
    def select_currency_message():
        """
        NO hacer queries aquí - solo retornar texto.
        Los datos vienen como parámetro al crear botones.
        """
        return (
            "Excelente! Vamos a crear tu operación.\n\n"
            "¿Qué moneda recibirás?"
        )
    
    @staticmethod
    def select_method_message():
        """
        Mensaje para selección de método de pago.
        """
        return (
            "¿Método de pago de origen?\n\n"
            "Selecciona cómo enviarás el dinero:"
        )
    
    @staticmethod
    def enter_amount_message(payment_method_name):
        """
        Recibe datos ya serializados, NO objetos SQLAlchemy.
        """
        return (
            f"¿Qué cantidad enviarás? 💵\n\n"
            f"Método: {payment_method_name}\n"
            f"Ejemplo: 100"
        )
    
    @staticmethod
    def calculation_summary(calc_data):
        """
        Muestra resumen de cálculo.
        
        calc_data debe ser un dict con:
        - amount_usd
        - fee_usd (si aplica)
        - net_usd
        - amount_local
        - exchange_rate
        - currency_code
        - payment_method_name
        """
        has_fee = calc_data.get('fee_usd', 0) > 0
        
        if has_fee:
            # PayPal u otro con comisión
            text = (
                "📊 RESUMEN\n"
                "━━━━━━━━━━━\n"
                f"Si me envías: ${calc_data['amount_usd']:.2f} USD\n"
                f"Comisión {calc_data['payment_method_name']}: -${calc_data['fee_usd']:.2f} USD\n"
                f"Recibiré: ${calc_data['net_usd']:.2f} USD ({calc_data['payment_method_name']})\n"
                f"Recibirás: {calc_data['amount_local']:,.2f} {calc_data['currency_code']}\n"
                f"Tasa aplicada: {calc_data['exchange_rate']:,.2f} {calc_data['currency_code']}/$\n"
                "━━━━━━━━━━━\n"
                "¿Confirmas?"
            )
        else:
            # Zelle, USDT, etc (sin comisión)
            text = (
                "📊 RESUMEN\n"
                "━━━━━━━━━━━\n"
                f"Si me envías: ${calc_data['amount_usd']:.2f} USD ({calc_data['payment_method_name']})\n"
                f"Recibiré: ${calc_data['net_usd']:.2f} USD\n"
                f"Recibirás: {calc_data['amount_local']:,.2f} {calc_data['currency_code']}\n"
                f"Tasa aplicada: {calc_data['exchange_rate']:,.2f} {calc_data['currency_code']}/$\n"
                "━━━━━━━━━━━\n"
                "⚠️ Nota: Si tu banco cobra comisión, esta corre por tu cuenta.\n"
                "━━━━━━━━━━━\n"
                "¿Confirmas?"
            )
        
        return text
    
    @staticmethod
    def welcome_message():
        """
        Mensaje de bienvenida /start
        """
        return (
            "¡Hola! 👋 Bienvenido a Ceiba21 🌳\n"
            "Cambio de divisas rápido y seguro.\n\n"
            "¿Qué deseas hacer?"
        )
    
    @staticmethod
    def help_message():
        """
        Mensaje de ayuda
        """
        return (
            "💬 AYUDA DE CEIBA21\n\n"
            "Comandos disponibles:\n"
            "/start - Iniciar nueva operación\n"
            "/status - Ver estado de mi orden\n"
            "/cancel - Cancelar conversación actual\n"
            "/help - Ver esta ayuda\n\n"
            "¿Necesitas soporte? Escríbenos a:\n"
            "@ceiba21_soporte"
        )
```

---

### Paso 3: Modificar el handler de Telegram

```python
# app/telegram/bot.py

from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from app.bot.conversation_handler import ConversationHandler as ConvHandler
from app.models.user import User
from flask import current_app

conv_handler = ConvHandler()

def get_or_create_user_from_telegram(telegram_user):
    """
    Obtener o crear usuario desde datos de Telegram.
    
    IMPORTANTE: Llamar DENTRO de app.app_context()
    """
    user = User.query.filter_by(telegram_id=telegram_user.id).first()
    
    if not user:
        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name
        )
        user.save()
    
    return user

def get_user_state(user):
    """
    Obtener estado actual de conversación desde Redis.
    """
    from app import redis_client
    state_str = redis_client.get(f'conv_state:{user.id}')
    
    if state_str:
        from app.bot.states import ConversationState
        return ConversationState(state_str.decode())
    
    return None

def save_user_state(user_id, state):
    """
    Guardar estado de conversación en Redis.
    """
    from app import redis_client
    from app.bot.states import ConversationState
    
    if isinstance(state, ConversationState):
        state = state.value
    
    redis_client.setex(f'conv_state:{user_id}', 3600, state)

async def start_command(update, context):
    """
    Handler asíncrono de Telegram para /start
    
    CRÍTICO: Hacer queries DENTRO del contexto Flask
    """
    telegram_user = update.message.from_user
    
    # DENTRO del contexto Flask
    with current_app.app_context():
        # Obtener o crear usuario
        user = get_or_create_user_from_telegram(telegram_user)
        
        # Obtener respuesta con datos serializados
        response = conv_handler.handle_message(user, '/start', None)
        
        # Guardar estado en Redis
        save_user_state(user.id, 'MAIN_MENU')
    
    # AHORA sí, usar datos fuera del contexto Flask
    await update.message.reply_text(
        response['text'],
        reply_markup=response.get('buttons')
    )

async def message_handler(update, context):
    """
    Handler para mensajes de texto.
    """
    telegram_user = update.message.from_user
    message_text = update.message.text
    
    with current_app.app_context():
        # Verificar si bot está activo
        from app import redis_client
        if redis_client.get('bot_enabled') != b'1':
            await update.message.reply_text(
                '⚠️ El bot está temporalmente deshabilitado.\n'
                'Un operador te atenderá pronto.\n\n'
                'Para contacto inmediato: @ceiba21_soporte'
            )
            return
        
        # Obtener usuario y estado
        user = get_or_create_user_from_telegram(telegram_user)
        current_state = get_user_state(user)
        
        # Procesar mensaje
        response = conv_handler.handle_message(user, message_text, current_state)
        
        # Guardar nuevo estado si aplica
        if 'new_state' in response:
            save_user_state(user.id, response['new_state'])
    
    # Enviar respuesta
    await update.message.reply_text(
        response['text'],
        reply_markup=response.get('buttons')
    )

async def callback_query_handler(update, context):
    """
    Handler para botones inline (callback queries).
    """
    query = update.callback_query
    telegram_user = query.from_user
    callback_data = query.data
    
    await query.answer()
    
    with current_app.app_context():
        user = get_or_create_user_from_telegram(telegram_user)
        current_state = get_user_state(user)
        
        # Procesar callback
        response = conv_handler.handle_message(user, callback_data, current_state)
        
        # Guardar nuevo estado
        if 'new_state' in response:
            save_user_state(user.id, response['new_state'])
    
    # Editar mensaje original con la respuesta
    await query.edit_message_text(
        text=response['text'],
        reply_markup=response.get('buttons')
    )

async def photo_handler(update, context):
    """
    Handler para fotos (comprobantes de pago).
    """
    telegram_user = update.message.from_user
    
    with current_app.app_context():
        user = get_or_create_user_from_telegram(telegram_user)
        current_state = get_user_state(user)
        
        if current_state and current_state.value == 'AWAIT_PROOF':
            # Descargar imagen
            photo = update.message.photo[-1]
            file = await photo.get_file()
            
            # Guardar localmente
            import os
            from datetime import datetime
            filename = f"proof_{user.id}_{datetime.now().timestamp()}.jpg"
            filepath = os.path.join('/var/www/cotizaciones/static/uploads', filename)
            await file.download_to_drive(filepath)
            
            photo_url = f"/static/uploads/{filename}"
            
            # Procesar comprobante
            response = conv_handler.handle_proof(user, photo_url)
            
            if 'new_state' in response:
                save_user_state(user.id, response['new_state'])
        else:
            response = {
                'text': 'No estoy esperando un comprobante en este momento.'
            }
    
    await update.message.reply_text(response['text'])

# Configurar el bot
def setup_bot():
    """
    Configurar handlers del bot.
    """
    from telegram.ext import Application
    import os
    
    # Crear aplicación
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    
    # Registrar handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    application.add_handler(MessageHandler(Filters.photo, photo_handler))
    application.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    
    return application
```

---

## 🎯 REGLA DE ORO

**NUNCA pases objetos SQLAlchemy entre contextos. SIEMPRE serializa a dict/primitivos.**

```python
# ❌ MAL
currencies = Currency.query.all()
return {'data': currencies}

# ✅ BIEN
currencies = Currency.query.all()
return {'data': [c.to_dict() for c in currencies]}

# ✅ MEJOR (más explícito)
currencies = Currency.query.all()
return {
    'data': [
        {'id': c.id, 'code': c.code, 'name': c.name}
        for c in currencies
    ]
}
```

---

## 🔧 ALTERNATIVA: Método `to_dict()` en Modelos

Si quieres hacerlo más elegante, agrega `to_dict()` a tus modelos:

```python
# app/models/currency.py

class Currency(BaseModel):
    """
    Modelo de moneda.
    """
    __tablename__ = 'currencies'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    symbol = db.Column(db.String(10))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self, include_relations=False):
        """
        Serializar a diccionario.
        
        CRÍTICO: Accede a TODOS los atributos aquí,
        mientras la sesión DB está activa.
        """
        data = {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'symbol': self.symbol,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_relations:
            # Si necesitas relaciones, cárgalas aquí
            data['payment_methods'] = [
                pm.to_dict() for pm in self.payment_methods
            ]
        
        return data
```

```python
# app/models/payment_method.py

class PaymentMethod(BaseModel):
    """
    Modelo de método de pago.
    """
    __tablename__ = 'payment_methods'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    is_origin = db.Column(db.Boolean, default=True)
    fee_formula = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self, include_relations=False):
        """
        Serializar a diccionario.
        """
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'is_active': self.is_active,
            'is_origin': self.is_origin,
            'fee_formula': self.fee_formula,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
```

Luego úsalo así:

```python
# En conversation_handler.py
currencies = Currency.query.filter_by(is_active=True).all()
currencies_data = [c.to_dict() for c in currencies]
return {'currencies': currencies_data}
```

---

## ❓ ¿Por Qué Esto Funciona?

1. **Dentro de `app.app_context()`**: La sesión de SQLAlchemy está activa, puedes acceder a lazy attributes
2. **Serializas a dict**: Fuerzas la carga de TODOS los atributos mientras la sesión existe
3. **Sales del contexto**: Ya tienes datos primitivos (dict), no objetos SQLAlchemy
4. **Handler async**: Usa los datos primitivos sin problema

---

## 📊 FLUJO CORRECTO

```
┌─────────────────────────────────────────────────┐
│  Handler Async (Telegram)                       │
│  - Recibe mensaje del usuario                   │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│  with app.app_context():                        │
│    ┌─────────────────────────────────────────┐  │
│    │ Sesión SQLAlchemy ACTIVA                │  │
│    │                                         │  │
│    │ 1. Query a BD                           │  │
│    │    currencies = Currency.query.all()    │  │
│    │                                         │  │
│    │ 2. SERIALIZAR (forzar carga)           │  │
│    │    data = [c.to_dict() for c in currencies] │
│    │                                         │  │
│    │ 3. Lógica de negocio                    │  │
│    │    response = conv_handler.handle()     │  │
│    │                                         │  │
│    │ 4. Guardar estado en Redis             │  │
│    └─────────────────────────────────────────┘  │
│                                                 │
│  # Salimos del contexto con DATOS PRIMITIVOS   │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│  Handler Async (Telegram)                       │
│  - Usa datos primitivos (dict/str/int)          │
│  - await update.message.reply_text()            │
│  - ✅ SIN ERRORES                               │
└─────────────────────────────────────────────────┘
```

---

## 💡 RESUMEN

### El problema NO era arquitectónico profundo

Era simplemente pasar objetos ORM entre contextos.

### La solución es simple

Serializar a dict antes de cruzar fronteras de contexto.

### Tiempo estimado de fix

**30 minutos - 1 hora** (no 8 horas ni 1 semana)

---

## 🔨 PASOS DE IMPLEMENTACIÓN

### 1. Agregar método `to_dict()` a todos los modelos

```python
# app/models/currency.py
def to_dict(self):
    return {
        'id': self.id,
        'code': self.code,
        'name': self.name,
        'symbol': self.symbol,
        'is_active': self.is_active
    }

# app/models/payment_method.py
def to_dict(self):
    return {
        'id': self.id,
        'name': self.name,
        'type': self.type,
        'is_active': self.is_active,
        'is_origin': self.is_origin
    }
```

### 2. Modificar `conversation_handler.py`

- NUNCA retornar objetos SQLAlchemy
- SIEMPRE serializar con `.to_dict()` o list comprehension
- Retornar solo datos primitivos

### 3. Modificar `responses.py`

- NO hacer queries a la BD
- Solo retornar strings (estáticos o con parámetros)
- Recibir datos ya serializados

### 4. Modificar `bot.py`

- TODO dentro de `with app.app_context():`
- Queries + serialización + lógica
- Salir del contexto con datos primitivos
- Usar datos en handlers async

---

## ✅ VERIFICACIÓN

Después de implementar, verifica:

1. ✅ No hay objetos SQLAlchemy en `return` statements fuera de app_context
2. ✅ Todos los modelos tienen método `to_dict()`
3. ✅ `responses.py` no tiene imports de modelos
4. ✅ Todos los handlers están en `async def`
5. ✅ Todas las queries están dentro de `with app.app_context()`

---

## 🎯 PROMPT PARA CLINE

```
Hola Cline,

He encontrado la solución definitiva al problema del bot de Telegram.

El error "Entity namespace for currencies has no property is_active" 
se debe a pasar objetos SQLAlchemy entre contextos async/sync.

SOLUCIÓN:

Lee el documento completo:
/mnt/user-data/outputs/SOLUCION_BOT_TELEGRAM.md

Implementa los siguientes cambios:

1. Agregar método to_dict() a todos los modelos (Currency, PaymentMethod, User, Order)

2. En app/bot/conversation_handler.py:
   - NUNCA retornar objetos SQLAlchemy
   - SIEMPRE usar .to_dict() o serializar manualmente
   - Retornar solo datos primitivos (dict, str, int, bool)

3. En app/bot/responses.py:
   - NO hacer queries a la base de datos
   - Solo retornar strings
   - Recibir datos ya serializados como parámetros

4. En app/telegram/bot.py:
   - TODO dentro de with app.app_context():
   - Hacer queries + serializar + lógica
   - Salir del contexto solo con datos primitivos
   - Usar esos datos en handlers async

REGLA DE ORO:
Nunca pasar objetos SQLAlchemy entre contextos.
Siempre serializar a dict/primitivos ANTES de salir del app_context.

Por favor implementa estos cambios y muéstrame el código resultante.
```

---

**Autor:** Jose (Ceiba21) + Claude (Anthropic)  
**Fecha:** Diciembre 2024  
**Versión:** 1.0 - Solución Definitiva
