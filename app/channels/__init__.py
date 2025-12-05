"""
Canales de comunicación (Strategy Pattern).
ChannelFactory para obtener el canal correcto.
"""
from app.channels.base_channel import BaseChannel
from app.channels.telegram_channel import TelegramChannel
from app.channels.whatsapp_channel import WhatsAppChannel
from app.channels.webchat_channel import WebChatChannel
from typing import Optional, Dict, Any
import os


class ChannelFactory:
    """
    Factory para obtener el canal de comunicación correcto.
    
    Implementa el patrón Strategy permitiendo que NotificationService
    envíe mensajes sin conocer el canal específico.
    
    Uso:
        channel = ChannelFactory.get_channel('telegram')
        channel.send_message(recipient_id, "Hola!")
    """
    
    # Cache de instancias de canales
    _instances: Dict[str, BaseChannel] = {}
    
    @classmethod
    def get_channel(cls, channel_type: str, config: Optional[Dict[str, Any]] = None) -> BaseChannel:
        """
        Obtener canal por tipo.
        
        Args:
            channel_type: Tipo de canal ('telegram', 'whatsapp', 'webchat')
            config: Configuración opcional para el canal
            
        Returns:
            Instancia del canal solicitado
            
        Raises:
            ValueError: Si el canal no existe
        """
        channel_type = channel_type.lower()
        
        # Usar instancia cacheada si existe (singleton por tipo)
        if channel_type in cls._instances and config is None:
            return cls._instances[channel_type]
        
        # Crear nueva instancia según tipo
        channel = None
        
        if channel_type == 'telegram':
            channel = TelegramChannel(config)
        elif channel_type == 'whatsapp':
            channel = WhatsAppChannel(config)
        elif channel_type == 'webchat':
            channel = WebChatChannel(config)
        else:
            raise ValueError(f"Canal desconocido: {channel_type}. Canales disponibles: telegram, whatsapp, webchat")
        
        # Cachear instancia si no tiene config personalizada
        if config is None:
            cls._instances[channel_type] = channel
        
        return channel
    
    @classmethod
    def get_available_channels(cls) -> Dict[str, bool]:
        """
        Obtener estado de disponibilidad de todos los canales.
        
        Returns:
            Dict con canal: disponible
        """
        channels = {}
        
        for channel_type in ['telegram', 'whatsapp', 'webchat']:
            try:
                channel = cls.get_channel(channel_type)
                channels[channel_type] = channel.is_available()
            except Exception as e:
                channels[channel_type] = False
        
        return channels
    
    @classmethod
    def clear_cache(cls):
        """
        Limpiar cache de instancias de canales.
        Útil para testing o reload de configuración.
        """
        cls._instances.clear()


# Exports
__all__ = [
    'BaseChannel',
    'TelegramChannel',
    'WhatsAppChannel',
    'WebChatChannel',
    'ChannelFactory'
]
