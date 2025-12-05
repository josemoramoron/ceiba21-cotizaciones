"""
Servicio base para todos los servicios del sistema.
Proporciona funcionalidad común y estructura para servicios.
"""
from app.models import db
from typing import Any, Optional, Dict, List


class BaseService:
    """
    Clase base para todos los servicios.
    
    Proporciona:
    - Manejo centralizado de sesiones de BD
    - Métodos de utilidad comunes
    - Logging consistente
    
    Los servicios específicos deben heredar de esta clase.
    """
    
    @staticmethod
    def commit() -> bool:
        """
        Hacer commit de la sesión actual.
        
        Returns:
            bool: True si el commit fue exitoso, False si hubo error
        """
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error en commit: {str(e)}")
            return False
    
    @staticmethod
    def rollback() -> None:
        """
        Hacer rollback de la sesión actual.
        """
        db.session.rollback()
    
    @staticmethod
    def add(instance: Any) -> bool:
        """
        Agregar instancia a la sesión.
        
        Args:
            instance: Instancia del modelo a agregar
            
        Returns:
            bool: True si se agregó exitosamente
        """
        try:
            db.session.add(instance)
            return True
        except Exception as e:
            print(f"Error al agregar instancia: {str(e)}")
            return False
    
    @staticmethod
    def delete(instance: Any) -> bool:
        """
        Eliminar instancia de la sesión.
        
        Args:
            instance: Instancia del modelo a eliminar
            
        Returns:
            bool: True si se eliminó exitosamente
        """
        try:
            db.session.delete(instance)
            return True
        except Exception as e:
            print(f"Error al eliminar instancia: {str(e)}")
            return False
    
    @staticmethod
    def save(instance: Any) -> bool:
        """
        Guardar instancia (add + commit).
        
        Args:
            instance: Instancia del modelo a guardar
            
        Returns:
            bool: True si se guardó exitosamente
        """
        try:
            db.session.add(instance)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error al guardar instancia: {str(e)}")
            return False
    
    @staticmethod
    def save_all(instances: List[Any]) -> bool:
        """
        Guardar múltiples instancias (bulk save).
        
        Args:
            instances: Lista de instancias a guardar
            
        Returns:
            bool: True si se guardaron exitosamente todas
        """
        try:
            db.session.add_all(instances)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error al guardar instancias: {str(e)}")
            return False
    
    @staticmethod
    def success_response(data: Any = None, message: str = "Operación exitosa") -> Dict[str, Any]:
        """
        Crear respuesta de éxito estandarizada.
        
        Args:
            data: Datos a retornar (opcional)
            message: Mensaje de éxito
            
        Returns:
            Dict con formato de respuesta exitosa
        """
        response = {
            'success': True,
            'message': message
        }
        
        if data is not None:
            response['data'] = data
        
        return response
    
    @staticmethod
    def error_response(message: str = "Error en la operación", errors: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Crear respuesta de error estandarizada.
        
        Args:
            message: Mensaje de error
            errors: Lista de errores específicos (opcional)
            
        Returns:
            Dict con formato de respuesta de error
        """
        response = {
            'success': False,
            'message': message
        }
        
        if errors:
            response['errors'] = errors
        
        return response
    
    @staticmethod
    def paginate_query(query: Any, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        Paginar query de SQLAlchemy.
        
        Args:
            query: Query de SQLAlchemy
            page: Número de página (1-indexed)
            per_page: Elementos por página
            
        Returns:
            Dict con datos paginados
        """
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': pagination.page,
            'per_page': pagination.per_page,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    
    @classmethod
    def log_info(cls, message: str) -> None:
        """
        Log de información (placeholder para futuro logging system).
        
        Args:
            message: Mensaje a loggear
        """
        print(f"[INFO] {cls.__name__}: {message}")
    
    @classmethod
    def log_error(cls, message: str, exception: Optional[Exception] = None) -> None:
        """
        Log de error (placeholder para futuro logging system).
        
        Args:
            message: Mensaje de error
            exception: Excepción capturada (opcional)
        """
        error_msg = f"[ERROR] {cls.__name__}: {message}"
        if exception:
            error_msg += f" - {str(exception)}"
        print(error_msg)
    
    @classmethod
    def log_warning(cls, message: str) -> None:
        """
        Log de advertencia (placeholder para futuro logging system).
        
        Args:
            message: Mensaje de advertencia
        """
        print(f"[WARNING] {cls.__name__}: {message}")
