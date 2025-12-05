"""
Canal de comunicación de Telegram.
Implementación completa usando python-telegram-bot.
"""
from app.channels.base_channel import BaseChannel
from typing import Optional, Dict, Any, List
import os


class TelegramChannel(BaseChannel):
    """
    Canal de Telegram usando python-telegram-bot.
    
    Usa el bot existente en app/telegram/bot.py
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializar canal de Telegram.
        
        Args:
            config: Configuración (bot_token, etc.)
        """
        super().__init__(config)
        
        # Obtener token del bot
        self.bot_token = config.get('bot_token') if config else None
        if not self.bot_token:
            self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        self.bot = None
        if self.bot_token:
            self._initialize_bot()
    
    def _initialize_bot(self):
        """Inicializar bot de Telegram"""
        try:
            from telegram import Bot
            self.bot = Bot(token=self.bot_token)
        except Exception as e:
            print(f"Error al inicializar Telegram bot: {e}")
            self.bot = None
    
    def send_message(self, recipient_id: str, text: str, **kwargs) -> tuple[bool, str]:
        """
        Enviar mensaje de texto por Telegram.
        
        Args:
            recipient_id: Chat ID de Telegram
            text: Texto del mensaje
            **kwargs: parse_mode, reply_markup, etc.
            
        Returns:
            Tupla (success, message_id_or_error)
        """
        if not self.bot:
            return False, "Bot no inicializado"
        
        try:
            # Parámetros por defecto
            parse_mode = kwargs.get('parse_mode', 'HTML')
            
            message = self.bot.send_message(
                chat_id=recipient_id,
                text=text,
                parse_mode=parse_mode,
                **{k: v for k, v in kwargs.items() if k not in ['parse_mode']}
            )
            return True, str(message.message_id)
        except Exception as e:
            return False, str(e)
    
    def send_image(self, recipient_id: str, image_url: str,
                  caption: Optional[str] = None, **kwargs) -> tuple[bool, str]:
        """
        Enviar imagen por Telegram.
        
        Args:
            recipient_id: Chat ID
            image_url: URL de la imagen
            caption: Caption opcional
            **kwargs: Parámetros adicionales
            
        Returns:
            Tupla (success, message_id_or_error)
        """
        if not self.bot:
            return False, "Bot no inicializado"
        
        try:
            message = self.bot.send_photo(
                chat_id=recipient_id,
                photo=image_url,
                caption=caption,
                **kwargs
            )
            return True, str(message.message_id)
        except Exception as e:
            return False, str(e)
    
    def send_document(self, recipient_id: str, document_url: str,
                     filename: Optional[str] = None, **kwargs) -> tuple[bool, str]:
        """
        Enviar documento por Telegram.
        
        Args:
            recipient_id: Chat ID
            document_url: URL del documento
            filename: Nombre del archivo
            **kwargs: Parámetros adicionales
            
        Returns:
            Tupla (success, message_id_or_error)
        """
        if not self.bot:
            return False, "Bot no inicializado"
        
        try:
            message = self.bot.send_document(
                chat_id=recipient_id,
                document=document_url,
                filename=filename,
                **kwargs
            )
            return True, str(message.message_id)
        except Exception as e:
            return False, str(e)
    
    def send_buttons(self, recipient_id: str, text: str,
                    buttons: List[Dict[str, str]], **kwargs) -> tuple[bool, str]:
        """
        Enviar mensaje con botones inline en Telegram.
        
        Args:
            recipient_id: Chat ID
            text: Texto del mensaje
            buttons: Lista de botones [{"text": "...", "callback_data": "..."}]
            **kwargs: Parámetros adicionales
            
        Returns:
            Tupla (success, message_id_or_error)
        """
        if not self.bot:
            return False, "Bot no inicializado"
        
        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            # Crear botones inline
            keyboard = []
            for button in buttons:
                keyboard.append([
                    InlineKeyboardButton(
                        text=button.get('text', ''),
                        callback_data=button.get('callback_data', '')
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = self.bot.send_message(
                chat_id=recipient_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=kwargs.get('parse_mode', 'HTML')
            )
            return True, str(message.message_id)
        except Exception as e:
            return False, str(e)
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información del usuario de Telegram.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dict con información del usuario
        """
        if not self.bot:
            return None
        
        try:
            chat = self.bot.get_chat(user_id)
            
            return {
                'id': str(chat.id),
                'username': chat.username or '',
                'first_name': chat.first_name or '',
                'last_name': chat.last_name or '',
                'type': chat.type,
                'phone': None  # Telegram no expone el teléfono por API
            }
        except Exception as e:
            print(f"Error al obtener info de usuario Telegram: {e}")
            return None
    
    def is_available(self) -> bool:
        """
        Verificar si Telegram está disponible.
        
        Returns:
            bool: True si el bot está configurado
        """
        return self.bot is not None and self.bot_token is not None
