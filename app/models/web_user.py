"""
Modelo de usuario web registrado.
Para usuarios que se registran en ceiba21.com (diferente de User que es vía bot).
"""
from app.models import db
from app.models.base import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets


class WebUser(BaseModel, UserMixin):
    """
    Usuario registrado en el sitio web ceiba21.com.
    
    IMPORTANTE: Este modelo es diferente de User (que es cliente vía bot).
    WebUser puede vincularse con User si también usa bot.
    
    Integración con Flask-Login para autenticación web.
    
    Attributes:
        email: Email único (usado para login)
        password_hash: Hash de la contraseña
        first_name: Nombre
        last_name: Apellido
        phone: Teléfono
        user_id: ID del User vinculado (si usa bot también)
        is_verified: Si el email ha sido verificado
        verification_token: Token para verificar email
        verification_sent_at: Timestamp de envío de verificación
        reset_token: Token para resetear contraseña
        reset_token_expires_at: Timestamp de expiración del token
        is_active: Si el usuario está activo
        last_login_at: Última vez que inició sesión
    """
    
    __tablename__ = 'web_users'
    
    # Identificación
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    
    # Vinculación con User (si también usa bot)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Verificación de email
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_token = db.Column(db.String(100), unique=True)
    verification_sent_at = db.Column(db.DateTime)
    
    # Recuperación de contraseña
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expires_at = db.Column(db.DateTime)
    
    # Estado
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime)
    
    # Relación con User (si está vinculado)
    user = db.relationship('User', foreign_keys=[user_id], backref='web_user')
    
    def __repr__(self) -> str:
        """Representación del usuario web"""
        return f"<WebUser #{self.id} - {self.email}>"
    
    # Métodos requeridos por Flask-Login
    
    def get_id(self) -> str:
        """
        Retorna el ID del usuario como string.
        Requerido por Flask-Login.
        """
        return str(self.id)
    
    @property
    def is_authenticated(self) -> bool:
        """
        Retorna True si el usuario está autenticado.
        Requerido por Flask-Login.
        """
        return True
    
    @property
    def is_anonymous(self) -> bool:
        """
        Retorna False ya que no es usuario anónimo.
        Requerido por Flask-Login.
        """
        return False
    
    # Métodos de contraseña
    
    def set_password(self, password: str) -> None:
        """
        Establecer contraseña del usuario (hash).
        
        Args:
            password: Contraseña en texto plano
            
        Example:
            >>> web_user = WebUser(email='juan@example.com')
            >>> web_user.set_password('mi_password_segura')
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """
        Verificar contraseña del usuario.
        
        Args:
            password: Contraseña a verificar
            
        Returns:
            bool: True si la contraseña es correcta
            
        Example:
            >>> if web_user.check_password('mi_password'):
            ...     print("Contraseña correcta")
        """
        return check_password_hash(self.password_hash, password)
    
    # Métodos de verificación de email
    
    def generate_verification_token(self) -> str:
        """
        Generar token de verificación de email.
        
        Returns:
            Token generado
            
        Example:
            >>> token = web_user.generate_verification_token()
            >>> web_user.save()
        """
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_sent_at = datetime.utcnow()
        return self.verification_token
    
    def verify_email(self, token: str) -> bool:
        """
        Verificar email con token.
        
        Args:
            token: Token de verificación
            
        Returns:
            bool: True si el token es válido y se verificó
            
        Example:
            >>> if web_user.verify_email(token):
            ...     print("Email verificado")
        """
        if self.verification_token == token and not self.is_verified:
            self.is_verified = True
            self.verification_token = None
            return self.save()
        return False
    
    # Métodos de recuperación de contraseña
    
    def generate_reset_token(self, expires_in: int = 3600) -> str:
        """
        Generar token para resetear contraseña.
        
        Args:
            expires_in: Tiempo de expiración en segundos (default: 1 hora)
            
        Returns:
            Token generado
            
        Example:
            >>> token = web_user.generate_reset_token()
            >>> web_user.save()
        """
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        return self.reset_token
    
    def verify_reset_token(self, token: str) -> bool:
        """
        Verificar si el token de reset es válido.
        
        Args:
            token: Token a verificar
            
        Returns:
            bool: True si el token es válido y no ha expirado
        """
        if self.reset_token != token:
            return False
        
        if self.reset_token_expires_at and self.reset_token_expires_at < datetime.utcnow():
            return False
        
        return True
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """
        Resetear contraseña con token.
        
        Args:
            token: Token de reset
            new_password: Nueva contraseña
            
        Returns:
            bool: True si se reseteo exitosamente
            
        Example:
            >>> if web_user.reset_password(token, 'nueva_password'):
            ...     print("Contraseña cambiada")
        """
        if not self.verify_reset_token(token):
            return False
        
        self.set_password(new_password)
        self.reset_token = None
        self.reset_token_expires_at = None
        return self.save()
    
    # Métodos de gestión
    
    def get_full_name(self) -> str:
        """
        Obtener nombre completo del usuario.
        
        Returns:
            str: Nombre completo
        """
        return f"{self.first_name} {self.last_name}"
    
    def update_last_login(self) -> bool:
        """
        Actualizar timestamp de último login.
        
        Returns:
            bool: True si se actualizó exitosamente
        """
        self.last_login_at = datetime.utcnow()
        return self.save()
    
    def link_to_user(self, user: 'User') -> bool:
        """
        Vincular WebUser con User (cliente del bot).
        
        Args:
            user: Usuario del bot a vincular
            
        Returns:
            bool: True si se vinculó exitosamente
        """
        self.user_id = user.id
        return self.save()
    
    def unlink_from_user(self) -> bool:
        """
        Desvincular de User.
        
        Returns:
            bool: True si se desvinculó exitosamente
        """
        self.user_id = None
        return self.save()
    
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convertir usuario web a diccionario.
        
        Args:
            include_relationships: Si True, incluye datos relacionados
            
        Returns:
            Dict con datos del usuario (sin password_hash)
        """
        data = super().to_dict()
        
        # Nunca exponer el hash de contraseña
        data.pop('password_hash', None)
        
        # Nunca exponer tokens sensibles
        data.pop('verification_token', None)
        data.pop('reset_token', None)
        
        # Agregar campos calculados
        data['full_name'] = self.get_full_name()
        
        if include_relationships:
            data['user'] = self.user.to_dict() if self.user else None
        
        return data
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional['WebUser']:
        """
        Buscar usuario web por email.
        
        Args:
            email: Email del usuario
            
        Returns:
            Usuario web encontrado o None
            
        Example:
            >>> web_user = WebUser.get_by_email('juan@example.com')
        """
        return cls.query.filter_by(email=email.lower()).first()
    
    @classmethod
    def get_by_verification_token(cls, token: str) -> Optional['WebUser']:
        """
        Buscar usuario web por token de verificación.
        
        Args:
            token: Token de verificación
            
        Returns:
            Usuario web encontrado o None
        """
        return cls.query.filter_by(verification_token=token).first()
    
    @classmethod
    def get_by_reset_token(cls, token: str) -> Optional['WebUser']:
        """
        Buscar usuario web por token de reset.
        
        Args:
            token: Token de reset
            
        Returns:
            Usuario web encontrado o None
        """
        return cls.query.filter_by(reset_token=token).first()
    
    @classmethod
    def authenticate(cls, email: str, password: str) -> Optional['WebUser']:
        """
        Autenticar usuario web con email y password.
        
        Args:
            email: Email del usuario
            password: Contraseña
            
        Returns:
            Usuario web si las credenciales son correctas, None si no
            
        Example:
            >>> web_user = WebUser.authenticate('juan@example.com', 'password123')
            >>> if web_user:
            ...     web_user.update_last_login()
        """
        web_user = cls.get_by_email(email)
        
        if web_user and web_user.is_active and web_user.check_password(password):
            return web_user
        
        return None
    
    @classmethod
    def create_user(cls, email: str, password: str, first_name: str,
                   last_name: str, phone: Optional[str] = None,
                   send_verification: bool = True) -> 'WebUser':
        """
        Crear un nuevo usuario web.
        
        Args:
            email: Email único
            password: Contraseña en texto plano
            first_name: Nombre
            last_name: Apellido
            phone: Teléfono (opcional)
            send_verification: Si se debe generar token de verificación
            
        Returns:
            Usuario web creado
            
        Example:
            >>> web_user = WebUser.create_user(
            ...     'juan@example.com',
            ...     'password123',
            ...     'Juan',
            ...     'Pérez',
            ...     phone='+584121234567'
            ... )
        """
        web_user = cls(
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )
        web_user.set_password(password)
        
        if send_verification:
            web_user.generate_verification_token()
        
        web_user.save()
        return web_user
    
    @classmethod
    def get_unverified_users(cls, limit: Optional[int] = None) -> list['WebUser']:
        """
        Obtener usuarios no verificados.
        
        Args:
            limit: Máximo de usuarios (None = todos)
            
        Returns:
            Lista de usuarios no verificados
        """
        query = cls.query.filter_by(is_verified=False, is_active=True)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @classmethod
    def get_recent_registrations(cls, days: int = 7, limit: int = 10) -> list['WebUser']:
        """
        Obtener registros recientes.
        
        Args:
            days: Número de días atrás
            limit: Máximo de usuarios
            
        Returns:
            Lista de usuarios registrados recientemente
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        return cls.query.filter(
            cls.created_at >= since
        ).order_by(cls.created_at.desc()).limit(limit).all()
