"""
Bot de Telegram para publicación automática de cotizaciones.
Versión síncrona usando requests HTTP para evitar conflicto con event loops.
"""
import os
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime


class TelegramPublisher:
    """
    Maneja la publicación en el canal de Telegram.
    
    IMPORTANTE: Esta clase usa requests HTTP directo en lugar de 
    python-telegram-bot async para evitar conflictos con el event loop
    del bot conversacional que corre en background.
    """
    
    def __init__(self, token, channel_id):
        """
        Inicializar publisher.
        
        Args:
            token: Token del bot de Telegram
            channel_id: ID del canal donde publicar
        """
        self.token = token
        self.channel_id = channel_id
        self.api_base_url = f"https://api.telegram.org/bot{token}"
    
    def _get_default_message(self):
        """Generar mensaje predeterminado con fecha actual"""
        now = datetime.now()
        return f"""🌳 *CEIBA21 - COTIZACIONES ACTUALIZADAS*

📊 *Fecha:* {now.strftime('%d/%m/%Y %H:%M')}

💰 Las mejores tasas del mercado
💸 Cambios rápidos y seguros
⭐ +5 años de experiencia

🌐 *Mas cotizaciones en nuestro sitio web:*"""
    
    def _get_inline_keyboard(self):
        """
        Generar teclado inline con botones.
        
        Returns:
            dict: Estructura del teclado para la API de Telegram
        """
        return {
            'inline_keyboard': [
                [
                    {
                        'text': '🌐 Sitio Web',
                        'url': 'https://ceiba21.com'
                    },
                    {
                        'text': '📱 Instagram',
                        'url': 'https://instagram.com/ceiba21_oficial'
                    }
                ],
                [
                    {
                        'text': '🐦 Twitter/X',
                        'url': 'https://twitter.com/ceiba21_oficial'
                    },
                    {
                        'text': '📘 Facebook',
                        'url': 'https://facebook.com/ceiba21.oficial'
                    }
                ],
                [
                    {
                        'text': '💬 WhatsApp',
                        'url': 'https://wa.me/573022100056'
                    }
                ]
            ]
        }
    
    def publish_quotes_sync(self, image_path, custom_message=None):
        """
        Publicar cotizaciones en el canal (versión síncrona).
        
        Usa requests HTTP directo para evitar conflictos con asyncio.
        Compatible con Flask sin romper el contexto de sesión.
        
        Args:
            image_path: Ruta de la imagen a publicar
            custom_message: Mensaje personalizado (opcional)
        
        Returns:
            dict: Resultado de la publicación con claves:
                - success (bool): Si fue exitosa
                - message_id (int): ID del mensaje (si exitosa)
                - url (str): URL del mensaje en Telegram (si exitosa)
                - error (str): Mensaje de error (si falló)
        """
        try:
            # Preparar URL de la API
            url = f"{self.api_base_url}/sendPhoto"
            
            # Preparar mensaje
            caption = custom_message if custom_message else self._get_default_message()
            
            # Preparar datos del request
            data = {
                'chat_id': self.channel_id,
                'caption': caption,
                'parse_mode': 'Markdown',
                'reply_markup': str(self._get_inline_keyboard()).replace("'", '"')
            }
            
            # Abrir y enviar imagen
            with open(image_path, 'rb') as photo:
                files = {'photo': photo}
                
                # Hacer request HTTP
                response = requests.post(
                    url,
                    data=data,
                    files=files,
                    timeout=30
                )
            
            # Procesar respuesta
            if response.status_code == 200:
                result = response.json()
                
                if result.get('ok'):
                    message_id = result['result']['message_id']
                    return {
                        'success': True,
                        'message_id': message_id,
                        'url': f"https://t.me/ceiba21channel/{message_id}"
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('description', 'Error desconocido')
                    }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except FileNotFoundError:
            return {
                'success': False,
                'error': f'Imagen no encontrada: {image_path}'
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Timeout al conectar con Telegram API'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Error de red: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
