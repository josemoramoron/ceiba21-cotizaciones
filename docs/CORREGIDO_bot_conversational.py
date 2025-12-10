"""
Bot conversacional de Telegram con FSM (python-telegram-bot v20+).
Maneja conversaciones completas para crear órdenes.

VERSIÓN CORREGIDA - SOLUCIÓN AL ERROR:
- TODAS las queries dentro de app.app_context()
- Serialización de objetos ANTES de salir del contexto
- Uso de datos primitivos en handlers async
"""
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from telegram.constants import ParseMode
from app import create_app
from app.bot.conversation_handler import ConversationHandler
from app.bot.responses import Responses
from app.models.user import User
from app.models.operator import Operator, OperatorRole
from app.models.order import Order
import redis

# Crear app Flask para contexto
flask_app = create_app()

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
        return True


def get_or_create_user_from_telegram(telegram_user) -> User:
    """
    Buscar o crear usuario desde datos de Telegram.
    
    IMPORTANTE: Llamar SOLO dentro de app.app_context()
    """
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
        'username': telegram_user.username,
        'first_name': telegram_user.first_name,
        'last_name': telegram_user.last_name
    }
    
    user = User.create_from_channel('telegram', str(telegram_user.id), user_data)
    logger.info(f"New user created: {user.id} - @{telegram_user.username}")
    
    return user


async def save_proof_to_storage(photo_file, order_reference: str) -> str:
    """Guardar comprobante en almacenamiento local"""
    proofs_dir = os.path.join('app', 'static', 'proofs')
    os.makedirs(proofs_dir, exist_ok=True)
    
    filename = f"{order_reference}_{photo_file.file_unique_id}.jpg"
    filepath = os.path.join(proofs_dir, filename)
    
    await photo_file.download_to_drive(filepath)
    
    return f"/static/proofs/{filename}"


# ==========================================
# HANDLERS DE COMANDOS
# ==========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler para /start
    
    CRÍTICO: TODO dentro de with flask_app.app_context()
    """
    try:
        # ✅ TODO dentro del contexto Flask
        with flask_app.app_context():
            user = get_or_create_user_from_telegram(update.message.from_user)
            
            conv_handler = ConversationHandler()
            response = conv_handler.handle_message(user, '/start')
        
        # ✅ Usar datos primitivos fuera del contexto
        reply_markup = Responses.format_buttons_for_telegram(response.get('buttons'))
        
        await update.message.reply_text(
            response['text'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in start_command: {str(e)}", exc_info=True)
        await update.message.reply_text(
            '❌ Error al iniciar. Intenta de nuevo o contacta a soporte.'
        )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /cancel"""
    try:
        with flask_app.app_context():
            user = get_or_create_user_from_telegram(update.message.from_user)
            
            conv_handler = ConversationHandler()
            response = conv_handler.handle_message(user, '/cancel')
        
        await update.message.reply_text(response['text'])
        
    except Exception as e:
        logger.error(f"Error in cancel_command: {str(e)}", exc_info=True)
        await update.message.reply_text('❌ Error al cancelar.')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /help"""
    try:
        with flask_app.app_context():
            user = get_or_create_user_from_telegram(update.message.from_user)
            
            conv_handler = ConversationHandler()
            response = conv_handler.handle_message(user, '/help')
        
        await update.message.reply_text(
            response['text'],
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}", exc_info=True)
        await update.message.reply_text('❌ Error al mostrar ayuda.')


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /status"""
    try:
        with flask_app.app_context():
            user = get_or_create_user_from_telegram(update.message.from_user)
            
            conv_handler = ConversationHandler()
            response = conv_handler.handle_message(user, '/status')
        
        await update.message.reply_text(
            response['text'],
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in status_command: {str(e)}", exc_info=True)
        await update.message.reply_text('❌ Error al consultar estado.')


# ==========================================
# COMANDOS ADMIN
# ==========================================

async def stopbot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /stopbot (solo ADMIN)"""
    try:
        telegram_id = update.message.from_user.id
        
        with flask_app.app_context():
            operator = Operator.query.filter_by(
                telegram_notification_id=str(telegram_id)
            ).first()
            
            if not operator or operator.role != OperatorRole.ADMIN:
                await update.message.reply_text('❌ No tienes permisos para este comando.')
                return
            
            # Serializar nombre del operador
            operator_name = operator.name
        
        # Fuera del contexto, usar datos primitivos
        redis_client.set('bot_enabled', '0')
        
        await update.message.reply_text('🛑 **Bot detenido.**\n\nLas conversaciones se pausarán.')
        logger.info(f"Bot stopped by admin: {operator_name}")
        
    except Exception as e:
        logger.error(f"Error in stopbot_command: {str(e)}", exc_info=True)
        await update.message.reply_text('❌ Error al detener bot.')


async def startbot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /startbot (solo ADMIN)"""
    try:
        telegram_id = update.message.from_user.id
        
        with flask_app.app_context():
            operator = Operator.query.filter_by(
                telegram_notification_id=str(telegram_id)
            ).first()
            
            if not operator or operator.role != OperatorRole.ADMIN:
                await update.message.reply_text('❌ No tienes permisos para este comando.')
                return
            
            # Serializar nombre del operador
            operator_name = operator.name
        
        # Fuera del contexto
        redis_client.set('bot_enabled', '1')
        
        await update.message.reply_text('✅ **Bot activado.**\n\nLas conversaciones se reanudarán.')
        logger.info(f"Bot started by admin: {operator_name}")
        
    except Exception as e:
        logger.error(f"Error in startbot_command: {str(e)}", exc_info=True)
        await update.message.reply_text('❌ Error al activar bot.')


async def takeover_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /takeover ORDER_ID (operadores)"""
    try:
        telegram_id = update.message.from_user.id
        
        if len(context.args) < 1:
            await update.message.reply_text('Uso: `/takeover ORD-20251204-001`')
            return
        
        order_reference = context.args[0]
        
        with flask_app.app_context():
            operator = Operator.query.filter_by(
                telegram_notification_id=str(telegram_id)
            ).first()
            
            if not operator:
                await update.message.reply_text('❌ No estás registrado como operador.')
                return
            
            order = Order.query.filter_by(reference=order_reference).first()
            
            if not order:
                await update.message.reply_text(f'❌ Orden `{order_reference}` no encontrada.')
                return
            
            conv_handler = ConversationHandler()
            conv_handler.transfer_to_operator(order, operator)
            
            # Serializar nombre del operador
            operator_name = operator.name
        
        # Fuera del contexto
        await update.message.reply_text(
            f'✅ **Atendiendo manualmente orden `{order_reference}`**\n\n'
            f'El bot automático se ha deshabilitado para este usuario.'
        )
        
        logger.info(f"Order {order_reference} taken over by {operator_name}")
        
    except Exception as e:
        logger.error(f"Error in takeover_command: {str(e)}", exc_info=True)
        await update.message.reply_text('❌ Error al tomar orden.')


# ==========================================
# HANDLERS DE MENSAJES
# ==========================================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler para mensajes de texto
    
    CRÍTICO: Queries dentro de app_context
    """
    try:
        # Verificar si bot está habilitado (sin contexto, solo Redis)
        if not is_bot_enabled():
            response = Responses.bot_disabled_message()
            await update.message.reply_text(response['text'])
            return
        
        # ✅ TODO dentro del contexto Flask
        with flask_app.app_context():
            user = get_or_create_user_from_telegram(update.message.from_user)
            message_text = update.message.text
            
            conv_handler = ConversationHandler()
            response = conv_handler.handle_message(user, message_text)
        
        # ✅ Usar datos primitivos fuera del contexto
        reply_markup = Responses.format_buttons_for_telegram(response.get('buttons'))
        
        await update.message.reply_text(
            response['text'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in message_handler: {str(e)}", exc_info=True)
        await update.message.reply_text(
            '❌ Error al procesar mensaje. Intenta de nuevo o escribe /cancel.'
        )


async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler para botones inline (callbacks)
    
    CRÍTICO: Queries dentro de app_context
    """
    try:
        query = update.callback_query
        await query.answer()
        
        # Verificar si bot está habilitado
        if not is_bot_enabled():
            response = Responses.bot_disabled_message()
            await query.message.reply_text(response['text'])
            return
        
        # ✅ TODO dentro del contexto Flask
        with flask_app.app_context():
            user = get_or_create_user_from_telegram(query.from_user)
            callback_data = query.data
            
            conv_handler = ConversationHandler()
            response = conv_handler.handle_message(user, callback_data)
        
        # ✅ Usar datos primitivos fuera del contexto
        reply_markup = Responses.format_buttons_for_telegram(response.get('buttons'))
        
        await query.message.reply_text(
            response['text'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in button_callback_handler: {str(e)}", exc_info=True)
        await query.message.reply_text('❌ Error al procesar selección.')


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler para fotos (comprobantes de pago)
    
    CRÍTICO: Queries dentro de app_context
    """
    try:
        # ✅ TODO dentro del contexto Flask
        with flask_app.app_context():
            user = get_or_create_user_from_telegram(update.message.from_user)
            
            conv_handler = ConversationHandler()
            current_state = conv_handler.get_state(user)
            
            from app.bot.states import ConversationState
            
            if current_state != ConversationState.AWAIT_PROOF:
                await update.message.reply_text(
                    '📸 Envía primero /start para crear una operación.'
                )
                return
            
            data = conv_handler.get_data(user)
            order_reference = data.get('order_reference')
            
            if not order_reference:
                await update.message.reply_text('❌ Error: No se encontró orden activa.')
                return
        
        # ✅ Salir del contexto antes de operaciones async de Telegram
        # Descargar foto (fuera del contexto)
        photo_file = await update.message.photo[-1].get_file()
        proof_url = await save_proof_to_storage(photo_file, order_reference)
        
        # ✅ Volver a entrar al contexto para procesar
        with flask_app.app_context():
            user = get_or_create_user_from_telegram(update.message.from_user)
            conv_handler = ConversationHandler()
            response = conv_handler.handle_proof_received(user, proof_url)
        
        # ✅ Usar datos primitivos fuera del contexto
        await update.message.reply_text(
            response['text'],
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"Proof received for order {order_reference}")
        
    except Exception as e:
        logger.error(f"Error in photo_handler: {str(e)}", exc_info=True)
        await update.message.reply_text(
            '❌ Error al procesar comprobante. Intenta de nuevo.'
        )


# ==========================================
# INICIALIZACIÓN DEL BOT
# ==========================================

def start_conversational_bot():
    """Iniciar bot conversacional (v20+ con Application)"""
    token = os.getenv('TELEGRAM_CONVERSATIONAL_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_CONVERSATIONAL_BOT_TOKEN not found in environment variables")
        return
    
    # Crear application
    application = Application.builder().token(token).build()
    
    # Registrar handlers de comandos
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('cancel', cancel_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('status', status_command))
    
    # Comandos admin/operadores
    application.add_handler(CommandHandler('stopbot', stopbot_command))
    application.add_handler(CommandHandler('startbot', startbot_command))
    application.add_handler(CommandHandler('takeover', takeover_command))
    
    # Handlers de contenido
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        message_handler
    ))
    
    # Inicializar bot como habilitado
    redis_client.set('bot_enabled', '1')
    
    logger.info("Bot conversational started!")
    
    # Iniciar polling
    application.run_polling()


if __name__ == '__main__':
    start_conversational_bot()
