"""
Bot de Telegram - VERSIÓN CORREGIDA
Integración async correcta con Flask + SQLAlchemy

SOLUCIÓN AL ERROR:
- TODAS las queries dentro de app.app_context()
- Serializar objetos ANTES de salir del contexto
- Usar datos primitivos en handlers async
"""
import os
import asyncio
import logging
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.constants import ParseMode
from datetime import datetime

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==========================================
# FUNCIONES HELPER (SYNC - DENTRO DE CONTEXTO FLASK)
# ==========================================

def get_or_create_user_from_telegram(telegram_user):
    """
    Obtener o crear usuario desde datos de Telegram.
    
    IMPORTANTE: Llamar SOLO dentro de app.app_context()
    
    Args:
        telegram_user: Usuario de Telegram
        
    Returns:
        User object (será serializado antes de salir del contexto)
    """
    from app.models.user import User
    
    user = User.query.filter_by(telegram_id=telegram_user.id).first()
    
    if not user:
        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            channel='telegram'
        )
        user.save()
    
    return user


def get_user_state(user_id):
    """
    Obtener estado actual de conversación desde Redis.
    
    Args:
        user_id: ID del usuario
        
    Returns:
        ConversationState o None
    """
    from app.bot.conversation_handler import ConversationHandler
    from app.bot.states import ConversationState
    from app import redis_client
    
    state_str = redis_client.get(f'conv_state:{user_id}')
    
    if state_str:
        if isinstance(state_str, bytes):
            state_str = state_str.decode()
        return ConversationState.from_string(state_str)
    
    return None


def save_user_state(user_id, state):
    """
    Guardar estado de conversación en Redis.
    
    Args:
        user_id: ID del usuario
        state: ConversationState
    """
    from app.bot.states import ConversationState
    from app import redis_client
    
    if isinstance(state, ConversationState):
        state = state.value
    
    redis_client.setex(f'conv_state:{user_id}', 1800, state)


def is_bot_enabled():
    """
    Verificar si el bot está activo.
    
    Returns:
        bool
    """
    from app import redis_client
    
    enabled = redis_client.get('bot_enabled')
    if enabled:
        if isinstance(enabled, bytes):
            enabled = enabled.decode()
        return enabled == '1'
    
    # Por defecto, bot activo
    return True


# ==========================================
# HANDLERS ASYNC (SIN QUERIES - SOLO DATOS PRIMITIVOS)
# ==========================================

async def start_command(update: Update, context):
    """
    Handler asíncrono para /start
    
    CRÍTICO: Hacer TODAS las queries dentro de with app.app_context()
    """
    telegram_user = update.message.from_user
    
    # Importar app aquí para evitar circular imports
    from app import create_app
    app = create_app()
    
    # TODO dentro del contexto Flask
    with app.app_context():
        from app.bot.conversation_handler import ConversationHandler
        
        # 1. Obtener o crear usuario
        user = get_or_create_user_from_telegram(telegram_user)
        
        # 2. Procesar con ConversationHandler
        conv_handler = ConversationHandler()
        response = conv_handler.handle_message(user, '/start', None)
        
        # 3. Guardar estado
        save_user_state(user.id, 'MAIN_MENU')
    
    # AHORA sí, fuera del contexto, usar datos primitivos
    from app.bot.responses import Responses
    
    text = response['text']
    buttons = response.get('buttons')
    reply_markup = Responses.format_buttons_for_telegram(buttons)
    
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


async def message_handler(update: Update, context):
    """
    Handler para mensajes de texto.
    """
    telegram_user = update.message.from_user
    message_text = update.message.text
    
    from app import create_app
    app = create_app()
    
    with app.app_context():
        # Verificar si bot está activo
        if not is_bot_enabled():
            from app.bot.responses import Responses
            disabled_response = Responses.bot_disabled_message()
            
            await update.message.reply_text(
                disabled_response['text'],
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        from app.bot.conversation_handler import ConversationHandler
        
        # Obtener usuario
        user = get_or_create_user_from_telegram(telegram_user)
        
        # Obtener estado actual
        current_state = get_user_state(user.id)
        
        # Procesar mensaje
        conv_handler = ConversationHandler()
        response = conv_handler.handle_message(user, message_text, current_state)
        
        # Guardar nuevo estado si aplica
        if 'next_state' in response:
            save_user_state(user.id, response['next_state'])
    
    # Enviar respuesta (fuera del contexto)
    from app.bot.responses import Responses
    
    text = response['text']
    buttons = response.get('buttons')
    reply_markup = Responses.format_buttons_for_telegram(buttons)
    
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


async def callback_query_handler(update: Update, context):
    """
    Handler para botones inline (callback queries).
    """
    query = update.callback_query
    telegram_user = query.from_user
    callback_data = query.data
    
    await query.answer()
    
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from app.bot.conversation_handler import ConversationHandler
        
        user = get_or_create_user_from_telegram(telegram_user)
        current_state = get_user_state(user.id)
        
        # Procesar callback
        conv_handler = ConversationHandler()
        response = conv_handler.handle_message(user, callback_data, current_state)
        
        # Guardar nuevo estado
        if 'next_state' in response:
            save_user_state(user.id, response['next_state'])
    
    # Editar mensaje (fuera del contexto)
    from app.bot.responses import Responses
    
    text = response['text']
    buttons = response.get('buttons')
    reply_markup = Responses.format_buttons_for_telegram(buttons)
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


async def photo_handler(update: Update, context):
    """
    Handler para fotos (comprobantes de pago).
    """
    telegram_user = update.message.from_user
    
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from app.bot.conversation_handler import ConversationHandler
        
        user = get_or_create_user_from_telegram(telegram_user)
        current_state = get_user_state(user.id)
        
        if current_state and current_state.value == 'AWAIT_PROOF':
            # Descargar imagen
            photo = update.message.photo[-1]
            file = await photo.get_file()
            
            # Guardar localmente
            import os
            from datetime import datetime
            filename = f"proof_{user.id}_{datetime.now().timestamp()}.jpg"
            uploads_dir = os.path.join(os.getcwd(), 'app', 'static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            filepath = os.path.join(uploads_dir, filename)
            
            await file.download_to_drive(filepath)
            
            photo_url = f"/static/uploads/{filename}"
            
            # Procesar comprobante
            conv_handler = ConversationHandler()
            response = conv_handler.handle_proof_received(user, photo_url)
            
            if 'next_state' in response:
                save_user_state(user.id, response['next_state'])
        else:
            response = {
                'text': 'No estoy esperando un comprobante en este momento.\n\nEscribe /start para comenzar.',
                'buttons': None
            }
    
    # Enviar respuesta
    await update.message.reply_text(
        response['text'],
        parse_mode=ParseMode.MARKDOWN
    )


async def help_command(update: Update, context):
    """Handler para /help"""
    from app.bot.responses import Responses
    
    response = Responses.help_message()
    
    await update.message.reply_text(
        response['text'],
        parse_mode=ParseMode.MARKDOWN
    )


async def cancel_command(update: Update, context):
    """Handler para /cancel"""
    telegram_user = update.message.from_user
    
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from app.bot.conversation_handler import ConversationHandler
        
        user = get_or_create_user_from_telegram(telegram_user)
        
        conv_handler = ConversationHandler()
        response = conv_handler._handle_cancel(user)
    
    await update.message.reply_text(
        response['text'],
        parse_mode=ParseMode.MARKDOWN
    )


async def status_command(update: Update, context):
    """Handler para /status"""
    telegram_user = update.message.from_user
    
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from app.bot.conversation_handler import ConversationHandler
        
        user = get_or_create_user_from_telegram(telegram_user)
        
        conv_handler = ConversationHandler()
        response = conv_handler._handle_status(user)
    
    await update.message.reply_text(
        response['text'],
        parse_mode=ParseMode.MARKDOWN
    )


# ==========================================
# COMANDOS DE CONTROL (SOLO ADMIN/OPERADORES)
# ==========================================

async def stop_bot_command(update: Update, context):
    """Detener bot (solo ADMIN)"""
    telegram_user = update.message.from_user
    
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from app.models.operator import Operator, OperatorRole
        
        operator = Operator.query.filter_by(telegram_notification_id=telegram_user.id).first()
        
        if not operator or operator.role != OperatorRole.ADMIN:
            await update.message.reply_text('❌ No tienes permisos.')
            return
        
        from app import redis_client
        redis_client.set('bot_enabled', '0')
    
    await update.message.reply_text('🛑 Bot detenido.')


async def start_bot_command(update: Update, context):
    """Activar bot (solo ADMIN)"""
    telegram_user = update.message.from_user
    
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from app.models.operator import Operator, OperatorRole
        
        operator = Operator.query.filter_by(telegram_notification_id=telegram_user.id).first()
        
        if not operator or operator.role != OperatorRole.ADMIN:
            await update.message.reply_text('❌ No tienes permisos.')
            return
        
        from app import redis_client
        redis_client.set('bot_enabled', '1')
    
    await update.message.reply_text('✅ Bot activado.')


async def takeover_command(update: Update, context):
    """Tomar conversación manualmente (OPERADORES)"""
    telegram_user = update.message.from_user
    
    if not context.args:
        await update.message.reply_text('Uso: /takeover ORD-20251204-001')
        return
    
    order_reference = context.args[0]
    
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from app.models.operator import Operator
        from app.models.order import Order
        from app.bot.conversation_handler import ConversationHandler
        
        operator = Operator.query.filter_by(telegram_notification_id=telegram_user.id).first()
        
        if not operator:
            await update.message.reply_text('❌ No estás registrado como operador.')
            return
        
        order = Order.query.filter_by(reference=order_reference).first()
        
        if not order:
            await update.message.reply_text('❌ Orden no encontrada.')
            return
        
        # Transferir a atención manual
        conv_handler = ConversationHandler()
        conv_handler.transfer_to_operator(order, operator)
    
    await update.message.reply_text(f'✅ Atendiendo manualmente orden {order_reference}')


# ==========================================
# CONFIGURACIÓN DEL BOT
# ==========================================

def setup_bot_application():
    """
    Configurar aplicación del bot con todos los handlers.
    
    Returns:
        Application configurada
    """
    # Obtener token desde variable de entorno
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        raise ValueError('TELEGRAM_BOT_TOKEN no configurado')
    
    # Crear aplicación
    application = Application.builder().token(token).build()
    
    # Registrar handlers de comandos
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('cancel', cancel_command))
    application.add_handler(CommandHandler('status', status_command))
    
    # Comandos de control
    application.add_handler(CommandHandler('stopbot', stop_bot_command))
    application.add_handler(CommandHandler('startbot', start_bot_command))
    application.add_handler(CommandHandler('takeover', takeover_command))
    
    # Handlers de mensajes
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    logger.info('Bot configurado correctamente')
    
    return application


# ==========================================
# CLASE PARA PUBLICACIÓN (MANTENER ORIGINAL)
# ==========================================

class TelegramPublisher:
    """Maneja la publicación en el canal de Telegram"""
    
    def __init__(self, token, channel_id):
        self.bot = Bot(token=token)
        self.channel_id = channel_id
        
    async def publish_quotes(self, image_path, custom_message=None):
        """
        Publica cotizaciones en el canal
        
        Args:
            image_path: Ruta de la imagen generada
            custom_message: Mensaje personalizado opcional
        
        Returns:
            dict: Resultado de la publicación
        """
        try:
            # Mensaje predeterminado
            now = datetime.now()
            if not custom_message:
                custom_message = f"""🌳 *CEIBA21 - COTIZACIONES ACTUALIZADAS*
📊 *Fecha:* {now.strftime('%d/%m/%Y %H:%M')}
💰 Las mejores tasas del mercado
💸 Cambios rápidos y seguros
⭐ +5 años de experiencia
🌐 *Mas cotizaciones en nuestro sitio web:*"""
            
            # Botones inline
            keyboard = [
                [
                    InlineKeyboardButton("🌐 Sitio Web", url="https://ceiba21.com"),
                    InlineKeyboardButton("📱 Instagram", url="https://instagram.com/ceiba21_oficial")
                ],
                [
                    InlineKeyboardButton("🐦 Twitter/X", url="https://twitter.com/ceiba21_oficial"),
                    InlineKeyboardButton("📘 Facebook", url="https://facebook.com/ceiba21.oficial")
                ],
                [
                    InlineKeyboardButton("💬 WhatsApp", url="https://wa.me/573022100056")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Publicar imagen con botones
            with open(image_path, 'rb') as photo:
                message = await self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=photo,
                    caption=custom_message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            
            return {
                'success': True,
                'message_id': message.message_id,
                'url': f"https://t.me/ceiba21channel/{message.message_id}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def publish_quotes_sync(self, image_path, custom_message=None):
        """Versión síncrona para usar en Flask"""
        return asyncio.run(self.publish_quotes(image_path, custom_message))


# ==========================================
# MAIN (PARA EJECUTAR BOT STANDALONE)
# ==========================================

if __name__ == '__main__':
    """
    Ejecutar bot en modo standalone (para desarrollo/testing)
    """
    application = setup_bot_application()
    
    logger.info('Iniciando bot...')
    application.run_polling(allowed_updates=Update.ALL_TYPES)
