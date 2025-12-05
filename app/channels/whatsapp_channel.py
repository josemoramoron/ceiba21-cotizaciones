"""
Canal de comunicación de WhatsApp (placeholder).
Para implementar en futuras fases.
"""
from app.channels.base_channel import BaseChannel
from typing import Optional, Dict, Any, List


class WhatsAppChannel(BaseChannel):
    """
    Canal de WhatsApp (placeholder para futuras implementaciones).
    
    Posibles integraciones:
    - WhatsApp Business API
    - Twilio WhatsApp
    - Meta Cloud API
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializar canal de WhatsApp.
        
        Args:
            config: Configuración (api_key, phone_number_id, etc.)
        """
        super().__init__(config)
        # TODO: Inicializar cliente de WhatsApp
    
    def send_message(self, recipient_id: str, text: str, **kwargs) -> tuple[bool, str]:
        """
        Enviar mensaje de texto por WhatsApp.
        
        TODO: Implementar con WhatsApp Business API
        """
        return False, "WhatsApp no implementado aún"
    
    def send_image(self, recipient_id: str, image_url: str,
                  caption: Optional[str] = None, **kwargs) -> tuple[bool, str]:
        """
        Enviar imagen por WhatsApp.
        
        TODO: Implementar
        """
        return False, "WhatsApp no implementado aún"
    
    def send_document(self, recipient_id: str, document_url: str,
                     filename: Optional[str] = None, **kwargs) -> tuple[bool, str]:
        """
        Enviar documento por WhatsApp.
        
        TODO: Implementar
        """
        return False, "WhatsApp no implementado aún"
    
    def send_buttons(self, recipient_id: str, text: str,
                    buttons: List[Dict[str, str]], **kwargs) -> tuple[bool, str]:
        """
        Enviar mensaje con botones en WhatsApp.
        
        TODO: Implementar con reply buttons de WhatsApp
        """
        return False, "WhatsApp no implementado aún"
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información del usuario de WhatsApp.
        
        TODO: Implementar
        """
        return None
    
    def is_available(self) -> bool:
        """
        WhatsApp no está disponible aún.
        """
        return False
