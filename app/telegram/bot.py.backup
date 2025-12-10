"""
Bot de Telegram para publicación automática de cotizaciones
"""
import os
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from datetime import datetime

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
