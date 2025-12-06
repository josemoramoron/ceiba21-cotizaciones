"""
Bot conversacional de Telegram con FSM.
Maneja conversaciones completas para crear órdenes.
"""
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, CallbackQueryHandler,
    Filters, CallbackContext
)
from telegram.constants import ParseMode
from app.bot.conversation_handler import ConversationHandler
from app.bot.responses import Responses
from app.models.user import User
from app.models.operator import Operator, OperatorRole
from app.models.order import Order
from app import db
import redis

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Redis client
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def is_bot_enabled() -> bool:
    """Verificar si el bot está habilitado"""
    try:
        status = redis_client.get('bot_enabled')
        return status == '1'
    except:
        return True  # Por defecto habilitado si Redis falla


def get_or_create_user_from_telegram(telegram_user) -> User:
    """
    Buscar o crear usuario desde datos de Telegram.
    
    Args:
        telegram_user: Objeto de telegram (from_user)
        
    Returns:
        User creado o encontrado
    """
    # Buscar por telegram_id
    user = User.query.filter_by(telegram_id=str(telegram_user.id)).first()
    
    if user:
        # Actualizar datos si cambiaron
        if telegram_user.first_name and user.first_name != telegram_user.first_name:
            user.first_name = telegram_user.first_name
        if telegram_user.last_name and user.last_name != telegram_user.last_name:
            user.last_name = telegram_user.last_name
        if telegram_user.username and user.username != telegram_user.username:
            user.username = telegram_user.username
        user.save()
        return user
    
    # Crear nuevo usuario
    user_data = {
        'telegram_id': str(telegram_user.id),
        'telegram_username': telegram_user.username,
        'first_name': telegram_user.first_name,
        'last_name': telegram_user.last_name
    }
    
    user = User.create_from_channel('telegram', user_data)
    logger.info(f"New user created: {user.id} - @{telegram_user.username}")
    
    return user


def save_proof_to_storage(photo_file, order_reference: str) -> str:
    """
    Guardar comprobante en almacenamiento local.
    
    Args:
        photo_file: Archivo de foto de Telegram
        order_reference: Referencia de la orden
        
    Returns:
        URL pública del comprobante
    """
    # Directorio de comprobantes
    proofs_dir = os.path.join('app', 'static', 'proofs')
    os.makedirs(proofs_dir, exist_ok=True)
    
    # Nombre del archivo
    filename = f"{order_reference}_{photo_file.file_unique_id}.jpg"
    filepath = os.path.join(proofs_dir, filename)
    
    # Descargar archivo
    photo_file.download(filepath)
    
    # Retornar URL relativa
    return f"/static/proofs/{filename}"


# ==========================================
# HANDLERS DE COMANDOS
# ==========================================

def start_command(update: Update, context: CallbackContext):
    """Handler para /start"""
    try:
        user = get_or_create_user_from_telegram(update.message.from_user)
        
        # Inicializar ConversationHandler
        conv_handler = ConversationHandler()
        response = conv_handler.handle_message(user, '/start')
        
        # Formatear botones
        reply_markup = Responses.format_buttons_for_telegram(response.get('buttons'))
        
        # Enviar respuesta
        update.message.reply_text(
            response['text'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in start_command: {str(e)}")
        update.message.reply_text(
            '❌ Error al iniciar. Intenta de nuevo o contacta a soporte.'
        )


def cancel_command(update: Update, context: CallbackContext):
    """Handler para /cancel"""
    try:
        user = get_or_create_user_from_telegram(update.message.from_user)
        
        conv_handler = ConversationHandler()
        response = conv_handler.handle_message(user, '/cancel')
        
        update.message.reply_text(response['text'])
        
    except Exception as e:
        logger.error(f"Error in cancel_command: {str(e)}")
        update.message.reply_text('❌ Error al cancelar.')


def help_command(update: Update, context: CallbackContext):
    """Handler para /help"""
    try:
        user = get_or_create_user_from_telegram(update.message.from_user)
        
        conv_handler = ConversationHandler()
        response = conv_handler.handle_message(user, '/help')
        
        update.message.reply_text(
            response['text'],
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}")
        update.message.reply_text('❌ Error al mostrar ayuda.')


def status_command(update: Update, context: CallbackContext):
    """Handler para /status"""
    try:
        user = get_or_create_user_from_telegram(update.message.from_user)
        
        conv_handler = ConversationHandler()
        response = conv_handler.handle_message(user, '/status')
        
        update.message.reply_text(
            response['text'],
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in status_command: {str(e)}")
        update.message.reply_text('❌ Error al consultar estado.')


# ==========================================
# COMANDOS ADMIN
# ==========================================

def stopbot_command(update: Update, context: CallbackContext):
    """Handler para /stopbot (solo ADMIN)"""
    try:
        telegram_id = update.message.from_user.id
        operator = Operator.query.filter_by(
            telegram_notification_id=str(telegram_id)
        ).first()
        
        if not operator or operator.role != OperatorRole.ADMIN:
            update.message.reply_text('❌ No tienes permisos para este comando.')
            return
        
        # Deshabilitar bot
        redis_client.set('bot_enabled', '0')
        
        update.message.reply_text('🛑 **Bot detenido.**\n\nLas conversaciones se pausarán.')
        logger.info(f"Bot stopped by admin: {operator.name}")
        
    except Exception as e:
        logger.error(f"Error in stopbot_command: {str(e)}")
        update.message.reply_text('❌ Error al detener bot.')


def startbot_command(update: Update, context: CallbackContext):
    """Handler para /startbot (solo ADMIN)"""
    try:
        telegram_id = update.message.from_user.id
        operator = Operator.query.filter_by(
            telegram_notification_id=str(telegram_id)
        ).first()
        
        if not operator or operator.role != OperatorRole.ADMIN:
            update.message.reply_text('❌ No tienes permisos para este comando.')
            return
        
        # Habilitar bot
        redis_client.set('bot_enabled', '1')
        
        update.message.reply_text('✅ **Bot activado.**\n\nLas conversaciones se reanudarán.')
        logger.info(f"Bot started by admin: {operator.name}")
        
    except Exception as e:
        logger.error(f"Error in startbot_command: {str(e)}")
        update.message.reply_text('❌ Error al activar bot.')


def takeover_command(update: Update, context: CallbackContext):
    """Handler para /takeover ORDER_ID (operadores)"""
    try:
        telegram_id = update.message.from_user.id
        operator = Operator.query.filter_by(
            telegram_notification_id=str(telegram_id)
        ).first()
        
        if not operator:
            update.message.reply_text('❌ No estás registrado como operador.')
            return
        
        # Verificar que se proporcionó la orden
        if len(context.args) < 1:
            update.message.reply_text('Uso: `/takeover ORD-20251204-001`')
            return
        
        order_reference = context.args[0]
        order = Order.query.filter_by(reference=order_reference).first()
        
        if not order:
            update.message.reply_text(f'❌ Orden `{order_reference}` no encontrada.')
            return
        
        # Transferir a atención manual
        conv_handler = ConversationHandler()
        conv_handler.transfer_to_operator(order, operator)
        
        update.message.reply_text(
            f'✅ **Atendiendo manualmente orden `{order_reference}`**\n\n'
            f'El bot automático se ha deshabilitado para este usuario.'
        )
        
        logger.info(f"Order {order_reference} taken over by {operator.name}")
        
    except Exception as e:
        logger.error(f"Error in takeover_command: {str(e)}")
        update.message.reply_text('❌ Error al tomar orden.')


# ==========================================
# HANDLERS DE MENSAJES
# ==========================================

def message_handler(update: Update, context: CallbackContext):
    """Handler para mensajes de texto"""
    try:
        # Verificar si bot está activo
        if not is_bot_enabled():
            response = Responses.bot_disabled_message()
            update.message.reply_text(response['text'])
            return
        
        user = get_or_create_user_from_telegram(update.message.from_user)
        message_text = update.message.text
        
        # Procesar mensaje con ConversationHandler
        conv_handler = ConversationHandler()
        response = conv_handler.handle_message(user, message_text)
        
        # Formatear botones si existen
        reply_markup = Responses.format_buttons_for_telegram(response.get('buttons'))
        
        # Enviar respuesta
        update.message.reply_text(
            response['text'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in message_handler: {str(e)}")
        update.message.reply_text(
            '❌ Error al procesar mensaje. Intenta de nuevo o escribe /cancel.'
        )


def button_callback_handler(update: Update, context: CallbackContext):
    """Handler para botones inline (callbacks)"""
    try:
        query = update.callback_query
        query.answer()  # Responder al callback
        
        # Verificar si bot está activo
        if not is_bot_enabled():
            response = Responses.bot_disabled_message()
            query.message.reply_text(response['text'])
            return
        
        user = get_or_create_user_from_telegram(query.from_user)
        callback_data = query.data
        
        # Procesar callback con ConversationHandler
        conv_handler = ConversationHandler()
        response = conv_handler.handle_message(user, callback_data)
        
        # Formatear botones
        reply_markup = Responses.format_buttons_for_telegram(response.get('buttons'))
        
        # Enviar respuesta
        query.message.reply_text(
            response['text'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in button_callback_handler: {str(e)}")
        query.message.reply_text('❌ Error al procesar selección.')


def photo_handler(update: Update, context: CallbackContext):
    """Handler para fotos (comprobantes de pago)"""
    try:
        user = get_or_create_user_from_telegram(update.message.from_user)
        
        # Obtener estado actual del usuario
        conv_handler = ConversationHandler()
        current_state = conv_handler.get_state(user)
        
        from app.bot.states import ConversationState
        
        # Verificar que esté esperando comprobante
        if current_state != ConversationState.AWAIT_PROOF:
            update.message.reply_text(
                '📸 Envía primero /start para crear una operación.'
            )
            return
        
        # Obtener datos de conversación
        data = conv_handler.get_data(user)
        order_reference = data.get('order_reference')
        
        if not order_reference:
            update.message.reply_text('❌ Error: No se encontró orden activa.')
            return
        
        # Obtener la foto de mayor resolución
        photo_file = update.message.photo[-1].get_file()
        
        # Guardar comprobante
        proof_url = save_proof_to_storage(photo_file, order_reference)
        
        # Procesar comprobante recibido
        response = conv_handler.handle_proof_received(user, proof_url)
        
        update.message.reply_text(
            response['text'],
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"Proof received for order {order_reference}")
        
    except Exception as e:
        logger.error(f"Error in photo_handler: {str(e)}")
        update.message.reply_text(
            '❌ Error al procesar comprobante. Intenta de nuevo.'
        )


# ==========================================
# INICIALIZACIÓN DEL BOT
# ==========================================

def start_conversational_bot():
    """
    Iniciar bot conversacional.
    
    NOTA: Esto inicia el bot en modo polling (desarrollo).
    Para producción, usar webhooks.
    """
    # Obtener token
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return
    
    # Crear updater
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher
    
    # Registrar handlers de comandos
    dispatcher.add_handler(CommandHandler('start', start_command))
    dispatcher.add_handler(CommandHandler('cancel', cancel_command))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('status', status_command))
    
    # Comandos admin/operadores
    dispatcher.add_handler(CommandHandler('stopbot', stopbot_command))
    dispatcher.add_handler(CommandHandler('startbot', startbot_command))
    dispatcher.add_handler(CommandHandler('takeover', takeover_command))
    
    # Handlers de contenido
    dispatcher.add_handler(CallbackQueryHandler(button_callback_handler))
    dispatcher.add_handler(MessageHandler(Filters.photo, photo_handler))
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command,
        message_handler
    ))
    
    # Inicializar bot como habilitado
    redis_client.set('bot_enabled', '1')
    
    logger.info("Bot conversational started!")
    
    # Iniciar polling
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    # Ejecutar bot si se llama directamente
    start_conversational_bot()
