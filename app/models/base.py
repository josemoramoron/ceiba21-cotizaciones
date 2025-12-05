"""
Modelo base abstracto para todos los modelos del sistema.
Proporciona funcionalidad común: timestamps, métodos CRUD básicos.
"""
from app.models import db
from datetime import datetime
from typing import Dict, List, Optional, Any


class BaseModel(db.Model):
    """
    Clase base abstracta para todos los modelos.
    
    Proporciona:
    - Campos comunes: id, created_at, updated_at
    - Métodos CRUD: save(), delete(), update()
    - Métodos de consulta: find_by_id(), find_all()
    - Serialización: to_dict(), from_dict()
    
    Todos los modelos del sistema deben heredar de esta clase.
    """
    
    __abstract__ = True  # No crea tabla en BD
    
    # Campos comunes
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    def save(self) -> bool:
        """
        Guardar el objeto en la base de datos.
        
        Si es nuevo (sin id), hace INSERT.
        Si ya existe, hace UPDATE.
        
        Returns:
            bool: True si se guardó exitosamente, False si hubo error
            
        Example:
            >>> user = User(username='john')
            >>> user.save()
            True
        """
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error al guardar {self.__class__.__name__}: {str(e)}")
            return False
    
    def delete(self) -> bool:
        """
        Eliminar el objeto de la base de datos.
        
        Returns:
            bool: True si se eliminó exitosamente, False si hubo error
            
        Example:
            >>> user = User.find_by_id(1)
            >>> user.delete()
            True
        """
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error al eliminar {self.__class__.__name__}: {str(e)}")
            return False
    
    def update(self, **kwargs) -> bool:
        """
        Actualizar múltiples campos del objeto.
        
        Args:
            **kwargs: Diccionario de campos a actualizar
            
        Returns:
            bool: True si se actualizó exitosamente, False si hubo error
            
        Example:
            >>> user = User.find_by_id(1)
            >>> user.update(first_name='John', last_name='Doe')
            True
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            # updated_at se actualiza automáticamente con onupdate
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error al actualizar {self.__class__.__name__}: {str(e)}")
            return False
    
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convertir el objeto a diccionario.
        
        Este método base serializa los campos básicos.
        Los modelos hijos pueden sobrescribirlo para personalizar.
        
        Args:
            include_relationships: Si True, incluye relaciones (debe implementarse en hijo)
            
        Returns:
            Dict con los campos del objeto
            
        Example:
            >>> user = User.find_by_id(1)
            >>> user.to_dict()
            {'id': 1, 'created_at': '2025-01-01T00:00:00', ...}
        """
        result = {}
        
        # Serializar columnas
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Convertir datetime a ISO format
            if isinstance(value, datetime):
                value = value.isoformat()
            
            # Convertir Decimal a float
            elif hasattr(value, 'to_eng_string'):  # Es un Decimal
                value = float(value)
            
            result[column.name] = value
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """
        Crear instancia desde diccionario.
        
        Args:
            data: Diccionario con los campos del objeto
            
        Returns:
            Nueva instancia del modelo
            
        Example:
            >>> data = {'username': 'john', 'email': 'john@example.com'}
            >>> user = User.from_dict(data)
        """
        # Filtrar solo campos que existen en el modelo
        valid_fields = {key: value for key, value in data.items() 
                       if hasattr(cls, key)}
        
        return cls(**valid_fields)
    
    @classmethod
    def find_by_id(cls, id: int) -> Optional['BaseModel']:
        """
        Buscar registro por ID.
        
        Args:
            id: ID del registro
            
        Returns:
            Instancia del modelo o None si no existe
            
        Example:
            >>> user = User.find_by_id(1)
        """
        return cls.query.get(id)
    
    @classmethod
    def find_all(cls, limit: Optional[int] = None, 
                 offset: int = 0, 
                 order_by: Optional[str] = None) -> List['BaseModel']:
        """
        Obtener todos los registros.
        
        Args:
            limit: Máximo número de registros (None = todos)
            offset: Número de registros a saltar (para paginación)
            order_by: Campo por el cual ordenar (ej: 'created_at', '-created_at' para desc)
            
        Returns:
            Lista de instancias del modelo
            
        Example:
            >>> users = User.find_all(limit=10, order_by='-created_at')
        """
        query = cls.query
        
        # Ordenar
        if order_by:
            if order_by.startswith('-'):  # Orden descendente
                field_name = order_by[1:]
                if hasattr(cls, field_name):
                    query = query.order_by(getattr(cls, field_name).desc())
            else:  # Orden ascendente
                if hasattr(cls, order_by):
                    query = query.order_by(getattr(cls, order_by))
        
        # Paginación
        if offset > 0:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def count(cls) -> int:
        """
        Contar total de registros.
        
        Returns:
            Número total de registros
            
        Example:
            >>> total_users = User.count()
        """
        return cls.query.count()
    
    def __repr__(self) -> str:
        """
        Representación del objeto.
        
        Los modelos hijos pueden sobrescribir este método.
        """
        return f"<{self.__class__.__name__} #{self.id}>"
