"""
Servicio de autenticación y autorización.
Maneja login, permisos y seguridad de operadores.
"""
from app.services.base_service import BaseService
from app.models import Operator, OperatorRole
from typing import Optional, Dict, Any, Tuple


class AuthService(BaseService):
    """
    Servicio para autenticación y autorización de operadores.
    
    Responsabilidades:
    - Autenticar operadores
    - Verificar permisos
    - Gestionar sesiones
    """
    
    @classmethod
    def authenticate_operator(cls, username: str, password: str) -> Optional[Operator]:
        """
        Autenticar operador con username y password.
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            
        Returns:
            Objeto Operator si autenticación exitosa, None si falla
        """
        try:
            operator = Operator.authenticate(username, password)
            
            if operator:
                # Actualizar último login
                operator.set_online()
                
                cls.log_info(f"Operador {username} autenticado exitosamente")
                
                return operator
            else:
                cls.log_warning(f"Intento de login fallido para: {username}")
                return None
                
        except Exception as e:
            cls.log_error("Error al autenticar operador", e)
            return None
    
    @classmethod
    def logout_operator(cls, operator_id: int) -> Tuple[bool, str]:
        """
        Cerrar sesión de operador.
        
        Args:
            operator_id: ID del operador
            
        Returns:
            Tupla (success, message)
        """
        try:
            operator = Operator.find_by_id(operator_id)
            if not operator:
                return False, "Operador no encontrado"
            
            operator.set_offline()
            cls.log_info(f"Operador {operator.username} cerró sesión")
            
            return True, "Sesión cerrada exitosamente"
            
        except Exception as e:
            cls.log_error("Error al cerrar sesión", e)
            return False, f"Error al cerrar sesión: {str(e)}"
    
    @classmethod
    def check_permission(cls, operator_id: int, permission: str) -> bool:
        """
        Verificar si un operador tiene un permiso específico.
        
        Args:
            operator_id: ID del operador
            permission: Nombre del permiso a verificar
            
        Returns:
            bool: True si tiene el permiso
        """
        try:
            operator = Operator.find_by_id(operator_id)
            if not operator or not operator.is_active:
                return False
            
            return operator.has_permission(permission)
            
        except Exception as e:
            cls.log_error("Error al verificar permiso", e)
            return False
    
    @classmethod
    def get_operator_permissions(cls, operator_id: int) -> Optional[Dict[str, bool]]:
        """
        Obtener todos los permisos de un operador.
        
        Args:
            operator_id: ID del operador
            
        Returns:
            Dict con todos los permisos o None
        """
        try:
            operator = Operator.find_by_id(operator_id)
            if not operator:
                return None
            
            return operator.get_all_permissions()
            
        except Exception as e:
            cls.log_error("Error al obtener permisos", e)
            return None
    
    @classmethod
    def create_operator(cls, username: str, password: str, full_name: str,
                       email: str, role: OperatorRole = OperatorRole.OPERATOR,
                       permissions: Optional[Dict[str, bool]] = None,
                       created_by_id: Optional[int] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Crear un nuevo operador.
        
        Args:
            username: Nombre de usuario único
            password: Contraseña
            full_name: Nombre completo
            email: Email único
            role: Rol del operador
            permissions: Permisos personalizados (opcional)
            created_by_id: ID del operador que crea (para auditoría)
            
        Returns:
            Tupla (success, message, operator_data)
        """
        try:
            # Verificar que el operador creador tiene permisos
            if created_by_id:
                if not cls.check_permission(created_by_id, 'manage_operators'):
                    return False, "No tienes permisos para crear operadores", None
            
            # Verificar que username no existe
            if Operator.get_by_username(username):
                return False, "El username ya existe", None
            
            # Verificar que email no existe
            if Operator.get_by_email(email):
                return False, "El email ya existe", None
            
            # Crear operador
            operator = Operator.create_operator(
                username=username,
                password=password,
                full_name=full_name,
                email=email,
                role=role,
                permissions=permissions
            )
            
            cls.log_info(f"Operador {username} creado exitosamente")
            
            return True, "Operador creado exitosamente", operator.to_dict()
            
        except Exception as e:
            cls.log_error("Error al crear operador", e)
            return False, f"Error al crear operador: {str(e)}", None
    
    @classmethod
    def update_operator_role(cls, operator_id: int, new_role: OperatorRole,
                            updated_by_id: int) -> Tuple[bool, str]:
        """
        Actualizar rol de un operador.
        
        Args:
            operator_id: ID del operador a actualizar
            new_role: Nuevo rol
            updated_by_id: ID del operador que actualiza
            
        Returns:
            Tupla (success, message)
        """
        try:
            # Verificar permisos
            if not cls.check_permission(updated_by_id, 'manage_operators'):
                return False, "No tienes permisos para cambiar roles"
            
            operator = Operator.find_by_id(operator_id)
            if not operator:
                return False, "Operador no encontrado"
            
            old_role = operator.role
            operator.role = new_role
            
            if cls.commit():
                cls.log_info(f"Rol de operador {operator.username} cambiado de {old_role.value} a {new_role.value}")
                return True, "Rol actualizado exitosamente"
            else:
                return False, "Error al actualizar rol"
                
        except Exception as e:
            cls.log_error("Error al actualizar rol", e)
            return False, f"Error al actualizar rol: {str(e)}"
    
    @classmethod
    def set_operator_permission(cls, operator_id: int, permission: str,
                               value: bool, updated_by_id: int) -> Tuple[bool, str]:
        """
        Establecer un permiso específico para un operador.
        
        Args:
            operator_id: ID del operador
            permission: Nombre del permiso
            value: True para otorgar, False para denegar
            updated_by_id: ID del operador que actualiza
            
        Returns:
            Tupla (success, message)
        """
        try:
            # Verificar permisos
            if not cls.check_permission(updated_by_id, 'manage_operators'):
                return False, "No tienes permisos para gestionar permisos"
            
            operator = Operator.find_by_id(operator_id)
            if not operator:
                return False, "Operador no encontrado"
            
            if operator.set_permission(permission, value):
                action = "otorgado" if value else "denegado"
                cls.log_info(f"Permiso '{permission}' {action} para operador {operator.username}")
                return True, f"Permiso {action} exitosamente"
            else:
                return False, "Error al establecer permiso"
                
        except Exception as e:
            cls.log_error("Error al establecer permiso", e)
            return False, f"Error al establecer permiso: {str(e)}"
    
    @classmethod
    def deactivate_operator(cls, operator_id: int, deactivated_by_id: int) -> Tuple[bool, str]:
        """
        Desactivar un operador.
        
        Args:
            operator_id: ID del operador a desactivar
            deactivated_by_id: ID del operador que desactiva
            
        Returns:
            Tupla (success, message)
        """
        try:
            # Verificar permisos
            if not cls.check_permission(deactivated_by_id, 'manage_operators'):
                return False, "No tienes permisos para desactivar operadores"
            
            # No permitir auto-desactivación
            if operator_id == deactivated_by_id:
                return False, "No puedes desactivarte a ti mismo"
            
            operator = Operator.find_by_id(operator_id)
            if not operator:
                return False, "Operador no encontrado"
            
            operator.is_active = False
            operator.is_online = False
            
            if cls.commit():
                cls.log_warning(f"Operador {operator.username} desactivado")
                return True, "Operador desactivado exitosamente"
            else:
                return False, "Error al desactivar operador"
                
        except Exception as e:
            cls.log_error("Error al desactivar operador", e)
            return False, f"Error al desactivar operador: {str(e)}"
    
    @classmethod
    def activate_operator(cls, operator_id: int, activated_by_id: int) -> Tuple[bool, str]:
        """
        Activar un operador.
        
        Args:
            operator_id: ID del operador a activar
            activated_by_id: ID del operador que activa
            
        Returns:
            Tupla (success, message)
        """
        try:
            # Verificar permisos
            if not cls.check_permission(activated_by_id, 'manage_operators'):
                return False, "No tienes permisos para activar operadores"
            
            operator = Operator.find_by_id(operator_id)
            if not operator:
                return False, "Operador no encontrado"
            
            operator.is_active = True
            
            if cls.commit():
                cls.log_info(f"Operador {operator.username} activado")
                return True, "Operador activado exitosamente"
            else:
                return False, "Error al activar operador"
                
        except Exception as e:
            cls.log_error("Error al activar operador", e)
            return False, f"Error al activar operador: {str(e)}"
    
    @classmethod
    def change_password(cls, operator_id: int, old_password: str,
                       new_password: str) -> Tuple[bool, str]:
        """
        Cambiar contraseña de un operador.
        
        Args:
            operator_id: ID del operador
            old_password: Contraseña actual
            new_password: Nueva contraseña
            
        Returns:
            Tupla (success, message)
        """
        try:
            operator = Operator.find_by_id(operator_id)
            if not operator:
                return False, "Operador no encontrado"
            
            # Verificar contraseña actual
            if not operator.check_password(old_password):
                return False, "Contraseña actual incorrecta"
            
            # Establecer nueva contraseña
            operator.set_password(new_password)
            
            if cls.commit():
                cls.log_info(f"Contraseña cambiada para operador {operator.username}")
                return True, "Contraseña cambiada exitosamente"
            else:
                return False, "Error al cambiar contraseña"
                
        except Exception as e:
            cls.log_error("Error al cambiar contraseña", e)
            return False, f"Error al cambiar contraseña: {str(e)}"
    
    @classmethod
    def get_available_operators(cls) -> list[Dict[str, Any]]:
        """
        Obtener operadores disponibles (activos y online).
        
        Returns:
            Lista de operadores disponibles
        """
        operators = Operator.get_available_operators()
        return [op.to_dict() for op in operators]
    
    @classmethod
    def get_operator_stats(cls) -> Dict[str, Any]:
        """
        Obtener estadísticas de operadores.
        
        Returns:
            Dict con estadísticas
        """
        total = Operator.count()
        online = Operator.get_online_count()
        top_performers = Operator.get_top_performers(5)
        
        return {
            'total_operators': total,
            'online_count': online,
            'offline_count': total - online,
            'top_performers': [op.to_dict() for op in top_performers]
        }
