"""
Modelo de usuario (cliente) del sistema.
Channel-agnostic: puede interactuar desde Telegram, WhatsApp, WebChat, etc.
"""
from app.models import db
from app.models.base import BaseModel
from typing import Optional, Dict, Any


class User(BaseModel):
    """
    Usuario/Cliente que utiliza el servicio de cambio de divisas.
    
    IMPORTANTE: Este modelo NO asume un canal específico.
    Un mismo usuario puede tener múltiples identidades (telegram_id, whatsapp_id, etc.)
    
    Attributes:
        telegram_id: ID del usuario en Telegram (nullable)
        whatsapp_id: ID del usuario en WhatsApp (nullable)
        webchat_session_id: ID de sesión del WebChat (nullable)
        app_user_id: ID del usuario en app móvil (nullable)
        username: Nombre de usuario (@username en Telegram, etc.)
        first_name: Nombre
        last_name: Apellido
        phone: Teléfono de contacto
        email: Email de contacto
        is_active: Si el usuario está activo
        is_verified: Si el usuario ha sido verificado
        is_blocked: Si el usuario está bloqueado
        total_orders: Total de órdenes realizadas
        total_volume_usd: Volumen total en USD transaccionado
    """
    
    __tablename__ = 'users'
    
    # Identificadores por canal (todos nullable - puede usar uno o varios)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=True, index=True)
    whatsapp_id = db.Column(db.String(50), unique=True, nullable=True, index=True)
    webchat_session_id = db.Column(db.String(100), unique=True, nullable=True)
    app_user_id = db.Column(db.String(100), unique=True, nullable=True)
    
    # Información personal
    username = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    
    # Estado
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)
    
    # Estadísticas (desnormalizadas para performance)
    total_orders = db.Column(db.Integer, default=0, nullable=False)
    total_volume_usd = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    
    # Última actividad
    last_activity_at = db.Column(db.DateTime)
    
    # Relaciones (se definirán cuando existan los modelos)
    # orders = db.relationship('Order', back_populates='user', lazy='dynamic')
    # messages = db.relationship('Message', back_populates='user', lazy='dynamic')
    
    def __repr__(self) -> str:
        """Representación del usuario"""
        return f"<User #{self.id} - {self.get_display_name()}>"
    
    def get_display_name(self) -> str:
        """
        Obtener nombre a mostrar del usuario.
        
        Prioridad: first_name + last_name > username > "Usuario #ID"
        
        Returns:
            str: Nombre a mostrar
            
        Example:
            >>> user = User(first_name='Juan', last_name='Pérez')
            >>> user.get_display_name()
            'Juan Pérez'
        """
        if self.first_name:
            if self.last_name:
                return f"{self.first_name} {self.last_name}"
            return self.first_name
        
        if self.username:
            return self.username
        
        return f"Usuario #{self.id}" if self.id else "Usuario"
    
    def get_contact_id(self, channel: str) -> Optional[str]:
        """
        Obtener ID de contacto según el canal.
        
        Args:
            channel: Canal deseado ('telegram', 'whatsapp', 'webchat', 'app')
            
        Returns:
            ID del usuario en ese canal o None si no existe
            
        Example:
            >>> user.get_contact_id('telegram')
            '123456789'
        """
        channel_map = {
            'telegram': self.telegram_id,
            'whatsapp': self.whatsapp_id,
            'webchat': self.webchat_session_id,
            'app': self.app_user_id
        }
        
        contact_id = channel_map.get(channel.lower())
        return str(contact_id) if contact_id else None
    
    def get_primary_channel(self) -> Optional[str]:
        """
        Obtener canal principal del usuario.
        
        Returns:
            Nombre del canal principal o None
            
        Example:
            >>> user.get_primary_channel()
            'telegram'
        """
        if self.telegram_id:
            return 'telegram'
        if self.whatsapp_id:
            return 'whatsapp'
        if self.app_user_id:
            return 'app'
        if self.webchat_session_id:
            return 'webchat'
        return None
    
    def update_stats(self) -> bool:
        """
        Actualizar estadísticas del usuario.
        Recalcula total_orders y total_volume_usd desde las órdenes.
        
        Returns:
            bool: True si se actualizó exitosamente
        """
        try:
            # Importación tardía para evitar circular import
            from app.models.order import Order, OrderStatus
            
            # Contar órdenes completadas
            completed_orders = Order.query.filter_by(
                user_id=self.id,
                status=OrderStatus.COMPLETED
            ).all()
            
            self.total_orders = len(completed_orders)
            self.total_volume_usd = sum(
                order.amount_usd for order in completed_orders
            )
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error al actualizar estadísticas de User #{self.id}: {str(e)}")
            return False
    
    def block(self, reason: str = None) -> bool:
        """
        Bloquear usuario.
        
        Args:
            reason: Razón del bloqueo (opcional)
            
        Returns:
            bool: True si se bloqueó exitosamente
        """
        self.is_blocked = True
        self.is_active = False
        return self.save()
    
    def unblock(self) -> bool:
        """
        Desbloquear usuario.
        
        Returns:
            bool: True si se desbloqueó exitosamente
        """
        self.is_blocked = False
        self.is_active = True
        return self.save()
    
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convertir usuario a diccionario.
        
        Args:
            include_relationships: Si True, incluye relaciones
            
        Returns:
            Dict con datos del usuario
        """
        data = super().to_dict()
        
        # Agregar campos calculados
        data['display_name'] = self.get_display_name()
        data['primary_channel'] = self.get_primary_channel()
        
        if include_relationships:
            # Importación tardía para evitar circular import
            try:
                from app.models.order import Order
                data['orders_count'] = Order.query.filter_by(user_id=self.id).count()
            except:
                data['orders_count'] = 0
        
        return data
    
    @classmethod
    def find_by_channel(cls, channel: str, channel_id: str) -> Optional['User']:
        """
        Buscar usuario por canal e ID de canal.
        
        Args:
            channel: Nombre del canal ('telegram', 'whatsapp', 'webchat', 'app')
            channel_id: ID del usuario en ese canal
            
        Returns:
            Usuario encontrado o None
            
        Example:
            >>> user = User.find_by_channel('telegram', '123456789')
        """
        channel = channel.lower()
        
        if channel == 'telegram':
            return cls.query.filter_by(telegram_id=int(channel_id)).first()
        elif channel == 'whatsapp':
            return cls.query.filter_by(whatsapp_id=channel_id).first()
        elif channel == 'webchat':
            return cls.query.filter_by(webchat_session_id=channel_id).first()
        elif channel == 'app':
            return cls.query.filter_by(app_user_id=channel_id).first()
        
        return None
    
    @classmethod
    def create_from_channel(cls, channel: str, channel_id: str, 
                           user_data: Dict[str, Any]) -> 'User':
        """
        Crear usuario desde un canal específico.
        
        Args:
            channel: Nombre del canal ('telegram', 'whatsapp', etc.)
            channel_id: ID del usuario en ese canal
            user_data: Diccionario con datos adicionales del usuario
            
        Returns:
            Usuario creado
            
        Example:
            >>> data = {'first_name': 'Juan', 'username': 'juanp'}
            >>> user = User.create_from_channel('telegram', '123456789', data)
        """
        channel = channel.lower()
        
        # Configurar el ID del canal correcto
        if channel == 'telegram':
            user_data['telegram_id'] = int(channel_id)
        elif channel == 'whatsapp':
            user_data['whatsapp_id'] = channel_id
        elif channel == 'webchat':
            user_data['webchat_session_id'] = channel_id
        elif channel == 'app':
            user_data['app_user_id'] = channel_id
        
        # Crear usuario
        user = cls(**user_data)
        user.save()
        
        return user
    
    @classmethod
    def find_or_create_from_channel(cls, channel: str, channel_id: str,
                                   user_data: Dict[str, Any]) -> tuple['User', bool]:
        """
        Buscar usuario por canal, o crearlo si no existe.
        
        Args:
            channel: Nombre del canal
            channel_id: ID del usuario en ese canal
            user_data: Datos del usuario para crear si no existe
            
        Returns:
            Tupla (usuario, created) donde created es True si se creó nuevo
            
        Example:
            >>> data = {'first_name': 'Juan'}
            >>> user, created = User.find_or_create_from_channel('telegram', '123', data)
            >>> if created:
            ...     print("Usuario nuevo creado")
        """
        user = cls.find_by_channel(channel, channel_id)
        
        if user:
            return user, False
        
        user = cls.create_from_channel(channel, channel_id, user_data)
        return user, True
    
    @classmethod
    def get_active_users(cls, limit: Optional[int] = None) -> list['User']:
        """
        Obtener usuarios activos.
        
        Args:
            limit: Máximo número de usuarios (None = todos)
            
        Returns:
            Lista de usuarios activos
        """
        query = cls.query.filter_by(is_active=True, is_blocked=False)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_blocked_users(cls) -> list['User']:
        """
        Obtener usuarios bloqueados.
        
        Returns:
            Lista de usuarios bloqueados
        """
        return cls.query.filter_by(is_blocked=True).all()
    
    @classmethod
    def get_top_users_by_volume(cls, limit: int = 10) -> list['User']:
        """
        Obtener usuarios con mayor volumen transaccionado.
        
        Args:
            limit: Número de usuarios a retornar
            
        Returns:
            Lista de usuarios ordenados por volumen
        """
        return cls.query.filter(
            cls.total_volume_usd > 0
        ).order_by(
            cls.total_volume_usd.desc()
        ).limit(limit).all()
