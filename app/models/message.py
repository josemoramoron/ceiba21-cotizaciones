"""
Modelo de mensaje.
Historial completo de conversaciones entre usuarios, bots y operadores.
"""
from app.models import db
from app.models.base import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List


class Message(BaseModel):
    """
    Mensaje en el sistema.
    
    Un solo lugar para TODO el historial de conversaciones,
    sin importar el canal (Telegram, WhatsApp, WebChat, etc.).
    
    Attributes:
        order_id: ID de la orden asociada (nullable si no hay orden aún)
        user_id: ID del usuario
        channel: Canal de origen (telegram, whatsapp, webchat, app)
        content: Contenido del mensaje
        message_type: Tipo de mensaje (text, image, document, location)
        attachment_url: URL del archivo adjunto (si aplica)
        sender_type: Tipo de remitente (user, bot, operator)
        operator_id: ID del operador si el remitente es operador
        is_read: Si el mensaje ha sido leído
        read_at: Timestamp de lectura
        external_message_id: ID del mensaje en el canal original
    """
    
    __tablename__ = 'messages'
    
    # Relaciones
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Canal de origen
    channel = db.Column(db.String(20), nullable=False)
    
    # Contenido
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text', nullable=False)
    attachment_url = db.Column(db.String(500))
    
    # Quién envió
    sender_type = db.Column(db.String(20), nullable=False)  # user, bot, operator
    operator_id = db.Column(db.Integer, db.ForeignKey('operators.id'), nullable=True)
    
    # Metadata
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime)
    
    # ID del mensaje en el canal original (para referencia)
    external_message_id = db.Column(db.String(100))
    
    # Relaciones
    order = db.relationship('Order', foreign_keys=[order_id], backref='messages')
    user = db.relationship('User', foreign_keys=[user_id], backref='messages')
    operator = db.relationship('Operator', foreign_keys=[operator_id])
    
    def __repr__(self) -> str:
        """Representación del mensaje"""
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"<Message #{self.id} - {self.sender_type}: {preview}>"
    
    def mark_as_read(self) -> bool:
        """
        Marcar mensaje como leído.
        
        Returns:
            bool: True si se marcó exitosamente
        """
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            return self.save()
        return True
    
    def mark_as_unread(self) -> bool:
        """
        Marcar mensaje como no leído.
        
        Returns:
            bool: True si se marcó exitosamente
        """
        self.is_read = False
        self.read_at = None
        return self.save()
    
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convertir mensaje a diccionario.
        
        Args:
            include_relationships: Si True, incluye datos relacionados
            
        Returns:
            Dict con datos del mensaje
        """
        data = super().to_dict()
        
        if include_relationships:
            data['order'] = self.order.to_dict() if self.order else None
            data['user'] = self.user.to_dict() if self.user else None
            data['operator'] = self.operator.to_dict() if self.operator else None
        
        return data
    
    @classmethod
    def create_message(cls, user_id: int, channel: str, content: str,
                      sender_type: str, message_type: str = 'text',
                      order_id: Optional[int] = None,
                      operator_id: Optional[int] = None,
                      attachment_url: Optional[str] = None,
                      external_message_id: Optional[str] = None) -> 'Message':
        """
        Crear un nuevo mensaje.
        
        Args:
            user_id: ID del usuario
            channel: Canal (telegram, whatsapp, etc.)
            content: Contenido del mensaje
            sender_type: Tipo de remitente (user, bot, operator)
            message_type: Tipo de mensaje (text, image, document, location)
            order_id: ID de orden asociada (opcional)
            operator_id: ID del operador (si sender_type='operator')
            attachment_url: URL del adjunto (opcional)
            external_message_id: ID en el canal original (opcional)
            
        Returns:
            Mensaje creado
            
        Example:
            >>> msg = Message.create_message(
            ...     user_id=1,
            ...     channel='telegram',
            ...     content='Hola, quiero hacer un cambio',
            ...     sender_type='user'
            ... )
        """
        message = cls(
            user_id=user_id,
            channel=channel,
            content=content,
            sender_type=sender_type,
            message_type=message_type,
            order_id=order_id,
            operator_id=operator_id,
            attachment_url=attachment_url,
            external_message_id=external_message_id
        )
        message.save()
        return message
    
    @classmethod
    def get_conversation(cls, user_id: int, order_id: Optional[int] = None,
                        limit: Optional[int] = None) -> List['Message']:
        """
        Obtener conversación completa de un usuario.
        
        Args:
            user_id: ID del usuario
            order_id: Filtrar por orden (opcional)
            limit: Máximo de mensajes (None = todos)
            
        Returns:
            Lista de mensajes ordenados cronológicamente
            
        Example:
            >>> messages = Message.get_conversation(user_id=1, order_id=5)
        """
        query = cls.query.filter_by(user_id=user_id)
        
        if order_id is not None:
            query = query.filter_by(order_id=order_id)
        
        query = query.order_by(cls.created_at.asc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_order_messages(cls, order_id: int) -> List['Message']:
        """
        Obtener todos los mensajes de una orden.
        
        Args:
            order_id: ID de la orden
            
        Returns:
            Lista de mensajes de la orden
        """
        return cls.query.filter_by(order_id=order_id).order_by(cls.created_at.asc()).all()
    
    @classmethod
    def get_unread_count(cls, operator_id: Optional[int] = None) -> int:
        """
        Contar mensajes sin leer.
        
        Args:
            operator_id: Filtrar por operador asignado (opcional)
            
        Returns:
            Número de mensajes sin leer
        """
        query = cls.query.filter_by(is_read=False, sender_type='user')
        
        # Si hay operador, solo contar mensajes de órdenes asignadas a ese operador
        if operator_id is not None:
            from app.models.order import Order
            query = query.join(Order).filter(Order.operator_id == operator_id)
        
        return query.count()
    
    @classmethod
    def get_unread_messages(cls, operator_id: Optional[int] = None,
                           limit: Optional[int] = None) -> List['Message']:
        """
        Obtener mensajes sin leer.
        
        Args:
            operator_id: Filtrar por operador asignado (opcional)
            limit: Máximo de mensajes (None = todos)
            
        Returns:
            Lista de mensajes sin leer
        """
        query = cls.query.filter_by(is_read=False, sender_type='user')
        
        if operator_id is not None:
            from app.models.order import Order
            query = query.join(Order).filter(Order.operator_id == operator_id)
        
        query = query.order_by(cls.created_at.asc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_recent_messages(cls, limit: int = 50) -> List['Message']:
        """
        Obtener mensajes recientes.
        
        Args:
            limit: Máximo de mensajes
            
        Returns:
            Lista de mensajes recientes
        """
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_user_last_message(cls, user_id: int) -> Optional['Message']:
        """
        Obtener último mensaje de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Último mensaje del usuario o None
        """
        return cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc()).first()
    
    @classmethod
    def mark_conversation_as_read(cls, user_id: int, order_id: Optional[int] = None) -> int:
        """
        Marcar toda una conversación como leída.
        
        Args:
            user_id: ID del usuario
            order_id: ID de la orden (opcional)
            
        Returns:
            Número de mensajes marcados como leídos
        """
        query = cls.query.filter_by(user_id=user_id, is_read=False)
        
        if order_id is not None:
            query = query.filter_by(order_id=order_id)
        
        messages = query.all()
        count = 0
        
        for msg in messages:
            if msg.mark_as_read():
                count += 1
        
        return count
    
    @classmethod
    def get_messages_by_channel(cls, channel: str, limit: Optional[int] = None) -> List['Message']:
        """
        Obtener mensajes por canal.
        
        Args:
            channel: Canal (telegram, whatsapp, webchat, app)
            limit: Máximo de mensajes (None = todos)
            
        Returns:
            Lista de mensajes del canal
        """
        query = cls.query.filter_by(channel=channel).order_by(cls.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_messages_by_type(cls, message_type: str, limit: Optional[int] = None) -> List['Message']:
        """
        Obtener mensajes por tipo.
        
        Args:
            message_type: Tipo de mensaje (text, image, document, location)
            limit: Máximo de mensajes (None = todos)
            
        Returns:
            Lista de mensajes del tipo
        """
        query = cls.query.filter_by(message_type=message_type).order_by(cls.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def search_messages(cls, search_term: str, limit: int = 50) -> List['Message']:
        """
        Buscar mensajes por contenido.
        
        Args:
            search_term: Término de búsqueda
            limit: Máximo de mensajes
            
        Returns:
            Lista de mensajes que coinciden
        """
        return cls.query.filter(
            cls.content.ilike(f'%{search_term}%')
        ).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_operator_messages(cls, operator_id: int, limit: Optional[int] = None) -> List['Message']:
        """
        Obtener mensajes enviados por un operador.
        
        Args:
            operator_id: ID del operador
            limit: Máximo de mensajes (None = todos)
            
        Returns:
            Lista de mensajes del operador
        """
        query = cls.query.filter_by(
            operator_id=operator_id,
            sender_type='operator'
        ).order_by(cls.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_daily_stats(cls, date_obj: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Obtener estadísticas de mensajes del día.
        
        Args:
            date_obj: Fecha (default: hoy)
            
        Returns:
            Dict con estadísticas del día
        """
        from datetime import date as date_type
        
        if date_obj is None:
            date_obj = date_type.today()
        
        day_start = datetime.combine(date_obj, datetime.min.time())
        day_end = datetime.combine(date_obj, datetime.max.time())
        
        messages = cls.query.filter(
            cls.created_at >= day_start,
            cls.created_at <= day_end
        ).all()
        
        by_sender = {
            'user': sum(1 for m in messages if m.sender_type == 'user'),
            'bot': sum(1 for m in messages if m.sender_type == 'bot'),
            'operator': sum(1 for m in messages if m.sender_type == 'operator')
        }
        
        by_channel = {}
        for m in messages:
            if m.channel not in by_channel:
                by_channel[m.channel] = 0
            by_channel[m.channel] += 1
        
        by_type = {}
        for m in messages:
            if m.message_type not in by_type:
                by_type[m.message_type] = 0
            by_type[m.message_type] += 1
        
        return {
            'date': date_obj.isoformat(),
            'total': len(messages),
            'by_sender': by_sender,
            'by_channel': by_channel,
            'by_type': by_type,
            'read_count': sum(1 for m in messages if m.is_read),
            'unread_count': sum(1 for m in messages if not m.is_read)
        }
