"""
Servicio de gestión de usuarios.
Maneja usuarios (clientes) que usan el sistema desde diferentes canales.
"""
from app.services.base_service import BaseService
from app.models import User
from typing import Optional, Dict, Any, List, Tuple


class UserService(BaseService):
    """
    Servicio para gestión de usuarios (clientes).
    
    Responsabilidades:
    - Crear/buscar usuarios desde canales
    - Actualizar información de usuarios
    - Gestionar bloqueos
    - Estadísticas de usuarios
    """
    
    @classmethod
    def get_or_create_user_from_channel(cls, channel: str, channel_id: str,
                                       user_data: Dict[str, Any]) -> Tuple[User, bool]:
        """
        Obtener usuario existente o crear uno nuevo desde un canal.
        
        Args:
            channel: Canal (telegram, whatsapp, webchat, app)
            channel_id: ID del usuario en ese canal
            user_data: Datos adicionales del usuario
            
        Returns:
            Tupla (user, created) donde created es True si se creó nuevo
        """
        try:
            user, created = User.find_or_create_from_channel(channel, channel_id, user_data)
            
            if created:
                cls.log_info(f"Usuario nuevo creado desde {channel}: {channel_id}")
            else:
                cls.log_info(f"Usuario existente encontrado: {user.id}")
            
            return user, created
            
        except Exception as e:
            cls.log_error("Error al obtener/crear usuario", e)
            raise
    
    @classmethod
    def get_user_by_id(cls, user_id: int, include_relationships: bool = False) -> Optional[Dict[str, Any]]:
        """
        Obtener usuario por ID.
        
        Args:
            user_id: ID del usuario
            include_relationships: Si se incluyen datos relacionados
            
        Returns:
            Dict con datos del usuario o None
        """
        user = User.find_by_id(user_id)
        if user:
            return user.to_dict(include_relationships=include_relationships)
        return None
    
    @classmethod
    def get_user_by_channel(cls, channel: str, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Buscar usuario por canal e ID.
        
        Args:
            channel: Canal (telegram, whatsapp, etc.)
            channel_id: ID en ese canal
            
        Returns:
            Dict con datos del usuario o None
        """
        user = User.find_by_channel(channel, channel_id)
        if user:
            return user.to_dict(include_relationships=True)
        return None
    
    @classmethod
    def update_user_info(cls, user_id: int, **kwargs) -> Tuple[bool, str]:
        """
        Actualizar información del usuario.
        
        Args:
            user_id: ID del usuario
            **kwargs: Campos a actualizar
            
        Returns:
            Tupla (success, message)
        """
        try:
            user = User.find_by_id(user_id)
            if not user:
                return False, "Usuario no encontrado"
            
            if user.update(**kwargs):
                cls.log_info(f"Usuario {user_id} actualizado")
                return True, "Usuario actualizado exitosamente"
            else:
                return False, "Error al actualizar usuario"
                
        except Exception as e:
            cls.log_error("Error al actualizar usuario", e)
            return False, f"Error al actualizar usuario: {str(e)}"
    
    @classmethod
    def block_user(cls, user_id: int, reason: str) -> Tuple[bool, str]:
        """
        Bloquear usuario.
        
        Args:
            user_id: ID del usuario
            reason: Razón del bloqueo
            
        Returns:
            Tupla (success, message)
        """
        try:
            user = User.find_by_id(user_id)
            if not user:
                return False, "Usuario no encontrado"
            
            if user.block(reason):
                cls.log_warning(f"Usuario {user_id} bloqueado: {reason}")
                return True, "Usuario bloqueado exitosamente"
            else:
                return False, "Error al bloquear usuario"
                
        except Exception as e:
            cls.log_error("Error al bloquear usuario", e)
            return False, f"Error al bloquear usuario: {str(e)}"
    
    @classmethod
    def unblock_user(cls, user_id: int) -> Tuple[bool, str]:
        """
        Desbloquear usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Tupla (success, message)
        """
        try:
            user = User.find_by_id(user_id)
            if not user:
                return False, "Usuario no encontrado"
            
            if user.unblock():
                cls.log_info(f"Usuario {user_id} desbloqueado")
                return True, "Usuario desbloqueado exitosamente"
            else:
                return False, "Error al desbloquear usuario"
                
        except Exception as e:
            cls.log_error("Error al desbloquear usuario", e)
            return False, f"Error al desbloquear usuario: {str(e)}"
    
    @classmethod
    def get_active_users(cls, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtener usuarios activos.
        
        Args:
            limit: Máximo de usuarios (None = todos)
            
        Returns:
            Lista de usuarios activos
        """
        users = User.get_active_users(limit)
        return [user.to_dict() for user in users]
    
    @classmethod
    def get_blocked_users(cls) -> List[Dict[str, Any]]:
        """
        Obtener usuarios bloqueados.
        
        Returns:
            Lista de usuarios bloqueados
        """
        users = User.get_blocked_users()
        return [user.to_dict() for user in users]
    
    @classmethod
    def get_top_users_by_volume(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtener usuarios con mayor volumen transaccionado.
        
        Args:
            limit: Número de usuarios a retornar
            
        Returns:
            Lista de usuarios ordenados por volumen
        """
        users = User.get_top_users_by_volume(limit)
        return [user.to_dict() for user in users]
    
    @classmethod
    def update_user_stats(cls, user_id: int) -> Tuple[bool, str]:
        """
        Actualizar estadísticas del usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Tupla (success, message)
        """
        try:
            user = User.find_by_id(user_id)
            if not user:
                return False, "Usuario no encontrado"
            
            if user.update_stats():
                return True, "Estadísticas actualizadas"
            else:
                return False, "Error al actualizar estadísticas"
                
        except Exception as e:
            cls.log_error("Error al actualizar estadísticas", e)
            return False, f"Error al actualizar estadísticas: {str(e)}"
    
    @classmethod
    def get_user_summary(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtener resumen completo del usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Dict con resumen del usuario
        """
        user = User.find_by_id(user_id)
        if not user:
            return None
        
        # Obtener datos relacionados
        from app.models import Order, Message
        
        orders_count = Order.query.filter_by(user_id=user_id).count()
        messages_count = Message.query.filter_by(user_id=user_id).count()
        
        summary = user.to_dict(include_relationships=False)
        summary['orders_count'] = orders_count
        summary['messages_count'] = messages_count
        
        return summary
