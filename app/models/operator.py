"""
Modelo de operador del sistema.
Operadores con roles y permisos para gestionar órdenes.
"""
from app.models import db
from app.models.base import BaseModel
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class OperatorRole(Enum):
    """
    Roles de operadores en el sistema.
    
    ADMIN: Acceso total al sistema, puede gestionar operadores y configuración
    OPERATOR: Puede procesar órdenes, responder mensajes, gestionar clientes
    VIEWER: Solo lectura, puede ver órdenes pero no procesarlas
    """
    ADMIN = 'admin'
    OPERATOR = 'operator'
    VIEWER = 'viewer'


class Operator(BaseModel, UserMixin):
    """
    Operador que procesa órdenes en el dashboard.
    
    Hereda UserMixin para Flask-Login:
    - is_authenticated: Siempre True si está en sesión
    - is_active: Retorna self.is_active (campo de BD)
    - is_anonymous: Siempre False
    - get_id(): Retorna str(self.id)
    
    Sistema de permisos granular con JSON para flexibilidad.
    
    Attributes:
        username: Nombre de usuario único
        password_hash: Hash de la contraseña
        full_name: Nombre completo del operador
        email: Email único
        role: Rol del operador (ADMIN, OPERATOR, VIEWER)
        permissions: Diccionario JSON con permisos específicos
        is_active: Si el operador está activo
        is_online: Si el operador está conectado
        last_login_at: Última vez que inició sesión
        orders_processed: Número total de órdenes procesadas
        average_processing_time: Tiempo promedio de procesamiento (segundos)
        telegram_notification_id: ID de Telegram para notificaciones
    """
    
    __tablename__ = 'operators'
    
    # Identificación
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    # Rol y permisos
    role = db.Column(db.Enum(OperatorRole), default=OperatorRole.OPERATOR, nullable=False)
    permissions = db.Column(db.JSON, default=dict, nullable=False)
    
    # Estado
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_online = db.Column(db.Boolean, default=False, nullable=False)
    last_login_at = db.Column(db.DateTime)
    
    # Estadísticas
    orders_processed = db.Column(db.Integer, default=0, nullable=False)
    average_processing_time = db.Column(db.Integer, default=0, nullable=False)  # en segundos
    
    # Notificaciones
    telegram_notification_id = db.Column(db.BigInteger, nullable=True)
    
    # Relaciones (se definirán cuando exista el modelo Order)
    # assigned_orders = db.relationship('Order', back_populates='operator', lazy='dynamic')
    
    def __repr__(self) -> str:
        """Representación del operador"""
        return f"<Operator #{self.id} - {self.username} ({self.role.value})>"
    
    def set_password(self, password: str) -> None:
        """
        Establecer contraseña del operador (hash).
        
        Args:
            password: Contraseña en texto plano
            
        Example:
            >>> operator = Operator(username='admin')
            >>> operator.set_password('mi_password_segura')
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """
        Verificar contraseña del operador.
        
        Args:
            password: Contraseña a verificar
            
        Returns:
            bool: True si la contraseña es correcta
            
        Example:
            >>> if operator.check_password('mi_password'):
            ...     print("Contraseña correcta")
        """
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission: str) -> bool:
        """
        Verificar si el operador tiene un permiso específico.
        
        ADMIN siempre tiene todos los permisos.
        
        Args:
            permission: Nombre del permiso a verificar
                       (ej: 'view_orders', 'approve_orders', 'cancel_orders')
            
        Returns:
            bool: True si tiene el permiso
            
        Example:
            >>> if operator.has_permission('approve_orders'):
            ...     order.approve()
        """
        # Admin tiene todos los permisos
        if self.role == OperatorRole.ADMIN:
            return True
        
        # Verificar en permisos JSON
        return self.permissions.get(permission, False)
    
    def set_permission(self, permission: str, value: bool) -> bool:
        """
        Establecer un permiso específico.
        
        Args:
            permission: Nombre del permiso
            value: True para otorgar, False para denegar
            
        Returns:
            bool: True si se guardó exitosamente
            
        Example:
            >>> operator.set_permission('approve_orders', True)
        """
        if self.permissions is None:
            self.permissions = {}
        
        self.permissions[permission] = value
        # Forzar actualización del campo JSON
        db.session.query(Operator).filter_by(id=self.id).update(
            {'permissions': self.permissions},
            synchronize_session=False
        )
        return self.save()
    
    def get_all_permissions(self) -> Dict[str, bool]:
        """
        Obtener todos los permisos del operador.
        
        Returns:
            Dict con todos los permisos
        """
        if self.role == OperatorRole.ADMIN:
            # Admin tiene todos los permisos
            return {
                'view_orders': True,
                'take_orders': True,
                'approve_orders': True,
                'cancel_orders': True,
                'view_reports': True,
                'manage_operators': True,
                'edit_rates': True,
                'manage_users': True,
                'view_messages': True,
                'send_messages': True
            }
        
        # Permisos base para todos
        default_permissions = {
            'view_orders': True,
            'take_orders': True,
            'approve_orders': False,
            'cancel_orders': False,
            'view_reports': False,
            'manage_operators': False,
            'edit_rates': False,
            'manage_users': False,
            'view_messages': True,
            'send_messages': True
        }
        
        # Viewer solo puede ver
        if self.role == OperatorRole.VIEWER:
            return {
                'view_orders': True,
                'take_orders': False,
                'approve_orders': False,
                'cancel_orders': False,
                'view_reports': True,
                'manage_operators': False,
                'edit_rates': False,
                'manage_users': False,
                'view_messages': True,
                'send_messages': False
            }
        
        # Combinar permisos por defecto con personalizados
        if self.permissions:
            default_permissions.update(self.permissions)
        
        return default_permissions
    
    def set_online(self) -> bool:
        """
        Marcar operador como online.
        
        Returns:
            bool: True si se actualizó exitosamente
        """
        self.is_online = True
        self.last_login_at = datetime.utcnow()
        return self.save()
    
    def set_offline(self) -> bool:
        """
        Marcar operador como offline.
        
        Returns:
            bool: True si se actualizó exitosamente
        """
        self.is_online = False
        return self.save()
    
    def update_last_login(self) -> bool:
        """
        Actualizar fecha y hora del último login.
        Llamado automáticamente al hacer login exitoso.
        
        Returns:
            bool: True si se actualizó exitosamente
        """
        self.last_login_at = datetime.utcnow()
        return self.save()
    
    def update_stats(self, processing_time: Optional[int] = None) -> bool:
        """
        Actualizar estadísticas del operador.
        
        Args:
            processing_time: Tiempo de procesamiento de última orden (segundos)
            
        Returns:
            bool: True si se actualizó exitosamente
        """
        try:
            # Importación tardía para evitar circular import
            from app.models.order import Order, OrderStatus
            
            # Contar órdenes procesadas
            self.orders_processed = Order.query.filter_by(
                operator_id=self.id,
                status=OrderStatus.COMPLETED
            ).count()
            
            # Calcular tiempo promedio si se proporciona
            if processing_time is not None:
                if self.average_processing_time == 0:
                    self.average_processing_time = processing_time
                else:
                    # Promedio ponderado
                    self.average_processing_time = int(
                        (self.average_processing_time * 0.8) + (processing_time * 0.2)
                    )
            
            return self.save()
        except Exception as e:
            print(f"Error al actualizar estadísticas de Operator #{self.id}: {str(e)}")
            return False
    
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convertir operador a diccionario.
        
        Args:
            include_relationships: Si True, incluye relaciones
            
        Returns:
            Dict con datos del operador (sin password_hash)
        """
        data = super().to_dict()
        
        # Nunca exponer el hash de contraseña
        data.pop('password_hash', None)
        
        # Convertir role enum a string
        data['role'] = self.role.value
        
        # Agregar permisos completos
        data['all_permissions'] = self.get_all_permissions()
        
        if include_relationships:
            try:
                from app.models.order import Order
                data['assigned_orders_count'] = Order.query.filter_by(
                    operator_id=self.id
                ).count()
            except:
                data['assigned_orders_count'] = 0
        
        return data
    
    @classmethod
    def get_available_operators(cls) -> List['Operator']:
        """
        Obtener operadores disponibles (activos y online).
        
        Returns:
            Lista de operadores disponibles
            
        Example:
            >>> operators = Operator.get_available_operators()
        """
        return cls.query.filter_by(
            is_active=True,
            is_online=True
        ).filter(
            cls.role.in_([OperatorRole.ADMIN, OperatorRole.OPERATOR])
        ).all()
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional['Operator']:
        """
        Buscar operador por username.
        
        Args:
            username: Nombre de usuario
            
        Returns:
            Operador encontrado o None
            
        Example:
            >>> operator = Operator.get_by_username('admin')
        """
        return cls.query.filter_by(username=username).first()
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional['Operator']:
        """
        Buscar operador por email.
        
        Args:
            email: Email del operador
            
        Returns:
            Operador encontrado o None
        """
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional['Operator']:
        """
        Autenticar operador con username y password.
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            
        Returns:
            Operador si las credenciales son correctas, None si no
            
        Example:
            >>> operator = Operator.authenticate('admin', 'password123')
            >>> if operator:
            ...     operator.set_online()
        """
        operator = cls.get_by_username(username)
        
        if operator and operator.is_active and operator.check_password(password):
            return operator
        
        return None
    
    @classmethod
    def create_operator(cls, username: str, password: str, full_name: str,
                       email: str, role: OperatorRole = OperatorRole.OPERATOR,
                       permissions: Optional[Dict[str, bool]] = None) -> 'Operator':
        """
        Crear un nuevo operador.
        
        Args:
            username: Nombre de usuario único
            password: Contraseña en texto plano
            full_name: Nombre completo
            email: Email único
            role: Rol del operador
            permissions: Permisos personalizados (opcional)
            
        Returns:
            Operador creado
            
        Example:
            >>> operator = Operator.create_operator(
            ...     'juan',
            ...     'password123',
            ...     'Juan Pérez',
            ...     'juan@ceiba21.com',
            ...     role=OperatorRole.OPERATOR
            ... )
        """
        operator = cls(
            username=username,
            full_name=full_name,
            email=email,
            role=role,
            permissions=permissions or {}
        )
        operator.set_password(password)
        operator.save()
        
        return operator
    
    @classmethod
    def get_online_count(cls) -> int:
        """
        Obtener número de operadores online.
        
        Returns:
            Número de operadores online
        """
        return cls.query.filter_by(is_active=True, is_online=True).count()
    
    @classmethod
    def get_top_performers(cls, limit: int = 5) -> List['Operator']:
        """
        Obtener operadores con mejor desempeño.
        
        Args:
            limit: Número de operadores a retornar
            
        Returns:
            Lista de operadores ordenados por órdenes procesadas
        """
        return cls.query.filter(
            cls.orders_processed > 0
        ).order_by(
            cls.orders_processed.desc()
        ).limit(limit).all()
