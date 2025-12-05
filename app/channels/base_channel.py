"""
Canal de comunicación base (interfaz abstracta).
Todos los canales deben heredar de esta clase.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class BaseChannel(ABC):
    """
    Interfaz abstracta para todos los canales de comunicación.
    
    Implementa el patrón Strategy para que NotificationService
    pueda enviar mensajes sin conocer el canal específico.
    
    Canales soportados:
    - TelegramChannel
    - WhatsAppChannel
    - WebChatChannel
    - AppChannel
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializar canal con configuración.
        
        Args:
            config: Configuración específica del canal
        """
        self.config = config or {}
        self.name = self.__class__.__name__
    
    @abstractmethod
    def send_message(self, recipient_id: str, text: str, **kwargs) -> tuple[bool, str]:
        """
        Enviar mensaje de texto.
        
        Args:
            recipient_id: ID del destinatario en este canal
            text: Texto del mensaje
            **kwargs: Parámetros adicionales específicos del canal
            
        Returns:
            Tupla (success, message_id_or_error)
        """
        pass
    
    @abstractmethod
    def send_image(self, recipient_id: str, image_url: str, 
                  caption: Optional[str] = None, **kwargs) -> tuple[bool, str]:
        """
        Enviar imagen con caption opcional.
        
        Args:
            recipient_id: ID del destinatario
            image_url: URL de la imagen
            caption: Texto descriptivo (opcional)
            **kwargs: Parámetros adicionales
            
        Returns:
            Tupla (success, message_id_or_error)
        """
        pass
    
    @abstractmethod
    def send_document(self, recipient_id: str, document_url: str,
                     filename: Optional[str] = None, **kwargs) -> tuple[bool, str]:
        """
        Enviar documento.
        
        Args:
            recipient_id: ID del destinatario
            document_url: URL del documento
            filename: Nombre del archivo (opcional)
            **kwargs: Parámetros adicionales
            
        Returns:
            Tupla (success, message_id_or_error)
        """
        pass
    
    @abstractmethod
    def send_buttons(self, recipient_id: str, text: str,
                    buttons: List[Dict[str, str]], **kwargs) -> tuple[bool, str]:
        """
        Enviar mensaje con botones interactivos.
        
        Args:
            recipient_id: ID del destinatario
            text: Texto del mensaje
            buttons: Lista de botones [{"text": "...", "callback_data": "..."}]
            **kwargs: Parámetros adicionales
            
        Returns:
            Tupla (success, message_id_or_error)
        """
        pass
    
    @abstractmethod
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información del usuario desde el canal.
        
        Args:
            user_id: ID del usuario en este canal
            
        Returns:
            Dict con información del usuario o None si no se encuentra
            
        Campos esperados:
            - id: ID en el canal
            - username: Nombre de usuario (si existe)
            - first_name: Nombre
            - last_name: Apellido (opcional)
            - phone: Teléfono (opcional)
        """
        pass
    
    def is_available(self) -> bool:
        """
        Verificar si el canal está disponible y configurado correctamente.
        
        Returns:
            bool: True si el canal está listo para usar
        """
        return True  # Por defecto asumimos que está disponible
    
    def __str__(self) -> str:
        """Representación en string del canal"""
        return f"<{self.name}>"
    
    def __repr__(self) -> str:
        """Representación detallada del canal"""
        return f"<{self.name} available={self.is_available()}>"
