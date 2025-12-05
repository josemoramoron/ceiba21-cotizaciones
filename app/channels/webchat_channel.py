"""
Canal de comunicación de WebChat (placeholder).
Para implementar en futuras fases con WebSockets.
"""
from app.channels.base_channel import BaseChannel
from typing import Optional, Dict, Any, List


class WebChatChannel(BaseChannel):
    """
    Canal de WebChat (placeholder para futuras implementaciones).
    
    Implementación futura:
    - Flask-SocketIO para comunicación en tiempo real
    - Chat integrado en el dashboard web
    - Notificaciones push al navegador
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializar canal de WebChat.
        
        Args:
            config: Configuración (socketio instance, etc.)
        """
        super().__init__(config)
        # TODO: Obtener instancia de SocketIO
        self.socketio = None
    
    def send_message(self, recipient_id: str, text: str, **kwargs) -> tuple[bool, str]:
        """
        Enviar mensaje de texto por WebChat.
        
        TODO: Implementar con Flask-SocketIO
        Emitir evento 'new_message' al socket del usuario
        """
        return False, "WebChat no implementado aún"
    
    def send_image(self, recipient_id: str, image_url: str,
                  caption: Optional[str] = None, **kwargs) -> tuple[bool, str]:
        """
        Enviar imagen por WebChat.
        
        TODO: Implementar
        """
        return False, "WebChat no implementado aún"
    
    def send_document(self, recipient_id: str, document_url: str,
                     filename: Optional[str] = None, **kwargs) -> tuple[bool, str]:
        """
        Enviar documento por WebChat.
        
        TODO: Implementar
        """
        return False, "WebChat no implementado aún"
    
    def send_buttons(self, recipient_id: str, text: str,
                    buttons: List[Dict[str, str]], **kwargs) -> tuple[bool, str]:
        """
        Enviar mensaje con botones en WebChat.
        
        TODO: Implementar con botones HTML
        """
        return False, "WebChat no implementado aún"
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información del usuario de WebChat.
        
        TODO: Consultar sesión del usuario web
        """
        return None
    
    def is_available(self) -> bool:
        """
        WebChat no está disponible aún.
        """
        return False
