"""
Modelo de Blacklist - Sistema de bloqueo de clientes.

RESPONSABILIDADES:
- Registro de usuarios bloqueados
- Historial de bloqueos/desbloqueos
- Sistema de apelaciones
- Auditoría completa
"""
from app.models import db
from app.models.base import BaseModel
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import or_


class BlacklistType(Enum):
    """Tipos de bloqueo"""
    PERMANENT = 'permanent'      # Bloqueo permanente
    TEMPORARY = 'temporary'      # Bloqueo temporal (con fecha de expiración)
    SUSPENDED = 'suspended'      # Suspensión (revisión pendiente)


class BlacklistCategory(Enum):
    """Categorías de bloqueo"""
    FRAUD = 'fraud'                           # Fraude confirmado
    CHARGEBACK = 'chargeback'                 # Contracargo
    FAKE_PAYMENT = 'fake_payment'             # Comprobante falso
    ABUSE = 'abuse'                           # Abuso verbal/maltrato
    SCAM = 'scam'                             # Intento de estafa
    SUSPICIOUS = 'suspicious'                 # Actividad sospechosa
    REPEATED_CANCELS = 'repeated_cancels'     # Cancelaciones reiteradas
    IDENTITY_THEFT = 'identity_theft'         # Robo de identidad
    OTHER = 'other'                           # Otra razón


class BlacklistStatus(Enum):
    """Estados de bloqueo"""
    ACTIVE = 'active'              # Bloqueo activo
    EXPIRED = 'expired'            # Bloqueo temporal expirado
    APPEALED = 'appealed'          # Bajo revisión (apelación)
    REVOKED = 'revoked'            # Revocado/desbloqueado


class AppealStatus(Enum):
    """Estados de apelación"""
    PENDING = 'pending'        # Pendiente de revisión
    REVIEWING = 'reviewing'    # En revisión
    APPROVED = 'approved'      # Aprobada (usuario desbloqueado)
    REJECTED = 'rejected'      # Rechazada
    MORE_INFO = 'more_info'    # Se requiere más información


class BlacklistEntry(BaseModel):
    """
    Entrada de Blacklist - Registro de bloqueo.
    
    Permite:
    - Bloqueos preventivos (sin user_id)
    - Múltiples bloqueos del mismo usuario
    - Auditoría completa
    - Bloqueos temporales/permanentes
    """
    
    __tablename__ = 'blacklist'
    
    # Usuario (puede ser NULL si es preventivo antes de crear cuenta)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    
    # Datos identificatorios (para bloqueos preventivos)
    telegram_id = db.Column(db.BigInteger, index=True)
    phone = db.Column(db.String(20), index=True)
    email = db.Column(db.String(120), index=True)
    dni = db.Column(db.String(50), index=True)
    full_name = db.Column(db.String(200))
    
    # Información geográfica
    country = db.Column(db.String(100))  # País
    state = db.Column(db.String(100))    # Estado/Región
    
    # Información de transacción
    transaction_type = db.Column(db.String(100))  # Ej: "PayPal -> VES"
    bank_info = db.Column(db.String(500))         # Datos bancarios
    additional_info = db.Column(db.Text)          # Información adicional
    
    # Evidencia multimedia
    photo_url = db.Column(db.String(500))         # URL de foto (optimizada)
    scam_links = db.Column(db.Text)               # JSON array de enlaces maliciosos
    
    # Reporte
    reporter_name = db.Column(db.String(100))     # Nombre de quien reporta (ej: "ceiba21")
    
    # Tipo y categoría
    block_type = db.Column(db.Enum(BlacklistType), nullable=False)
    category = db.Column(db.Enum(BlacklistCategory), nullable=False)
    status = db.Column(db.Enum(BlacklistStatus), default=BlacklistStatus.ACTIVE, nullable=False)
    
    # Razón y detalles
    reason = db.Column(db.String(500), nullable=False)
    detailed_notes = db.Column(db.Text)
    
    # Operador responsable
    blocked_by_operator_id = db.Column(db.Integer, db.ForeignKey('operators.id'))
    
    # Fechas
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime)  # Solo para TEMPORARY
    
    # Desbloqueo
    unblocked_at = db.Column(db.DateTime)
    unblocked_by_operator_id = db.Column(db.Integer, db.ForeignKey('operators.id'))
    unblock_reason = db.Column(db.String(500))
    
    # Auditoría de ediciones
    last_edited_at = db.Column(db.DateTime)
    last_edited_by_operator_id = db.Column(db.Integer, db.ForeignKey('operators.id'))
    
    # Severidad (1-5)
    severity = db.Column(db.Integer, default=3, nullable=False)
    
    # Evidencia
    evidence_urls = db.Column(db.Text)  # JSON array de URLs
    order_references = db.Column(db.String(500))  # ORD-XXX, ORD-YYY
    
    # Verificación de fraude (APIs externas)
    fraud_check_result = db.Column(db.JSON)  # Resultado de APIs
    risk_score = db.Column(db.Integer)  # 0-100
    
    # Relaciones
    user = db.relationship('User', backref='blacklist_entries', foreign_keys=[user_id])
    blocked_by = db.relationship('Operator', foreign_keys=[blocked_by_operator_id], backref='blocked_users')
    unblocked_by = db.relationship('Operator', foreign_keys=[unblocked_by_operator_id], backref='unblocked_users')
    last_edited_by = db.relationship('Operator', foreign_keys=[last_edited_by_operator_id])
    
    def __repr__(self) -> str:
        return f"<BlacklistEntry #{self.id} - {self.full_name or self.phone or self.email}>"
    
    def is_active_block(self) -> bool:
        """
        Verificar si el bloqueo está actualmente activo.
        
        Returns:
            True si el bloqueo es válido y no ha expirado
        """
        if self.status != BlacklistStatus.ACTIVE:
            return False
        
        # Si es temporal, verificar expiración
        if self.block_type == BlacklistType.TEMPORARY:
            if self.expires_at and self.expires_at < datetime.utcnow():
                return False
        
        return True
    
    def get_display_name(self) -> str:
        """Obtener nombre a mostrar"""
        if self.user:
            return self.user.get_display_name()
        elif self.full_name:
            return self.full_name
        elif self.phone:
            return f"Teléfono: {self.phone}"
        elif self.email:
            return f"Email: {self.email}"
        elif self.telegram_id:
            return f"Telegram: {self.telegram_id}"
        return f"Reporte #{self.id}"
    
    def get_identifiers(self) -> Dict[str, Any]:
        """Obtener todos los identificadores disponibles"""
        identifiers = {}
        
        if self.telegram_id:
            identifiers['telegram_id'] = self.telegram_id
        if self.phone:
            identifiers['phone'] = self.phone
        if self.email:
            identifiers['email'] = self.email
        if self.dni:
            identifiers['dni'] = self.dni
        if self.user_id:
            identifiers['user_id'] = self.user_id
        
        return identifiers
    
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """Convertir a diccionario"""
        data = super().to_dict()
        
        # Convertir enums a strings
        data['block_type'] = self.block_type.value if self.block_type else None
        data['category'] = self.category.value if self.category else None
        data['status'] = self.status.value if self.status else None
        
        # Agregar datos calculados
        data['display_name'] = self.get_display_name()
        data['is_active'] = self.is_active_block()
        data['identifiers'] = self.get_identifiers()
        
        if include_relationships:
            if self.user:
                data['user'] = self.user.to_dict()
            if self.blocked_by:
                data['blocked_by'] = {
                    'id': self.blocked_by.id,
                    'name': self.blocked_by.full_name
                }
            if self.unblocked_by:
                data['unblocked_by'] = {
                    'id': self.unblocked_by.id,
                    'name': self.unblocked_by.full_name
                }
        
        return data


class BlacklistAppeal(BaseModel):
    """
    Apelación de Blacklist - Usuario solicita revisión.
    
    Permite a usuarios bloqueados solicitar que se revise su caso.
    """
    
    __tablename__ = 'blacklist_appeals'
    
    # Relación con blacklist
    blacklist_id = db.Column(db.Integer, db.ForeignKey('blacklist.id'), nullable=False)
    
    # Datos del apelante (pueden ser diferentes al bloqueado)
    appellant_name = db.Column(db.String(200), nullable=False)
    appellant_email = db.Column(db.String(120), nullable=False)
    appellant_phone = db.Column(db.String(20))
    
    # Apelación
    appeal_text = db.Column(db.Text, nullable=False)
    additional_evidence = db.Column(db.Text)  # URLs separadas por comas
    
    # Estado
    status = db.Column(db.Enum(AppealStatus), default=AppealStatus.PENDING, nullable=False)
    
    # Fechas
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = db.Column(db.DateTime)
    
    # Revisión por operador
    reviewed_by_operator_id = db.Column(db.Integer, db.ForeignKey('operators.id'))
    review_notes = db.Column(db.Text)
    decision = db.Column(db.String(20))  # 'approved', 'rejected'
    decision_reason = db.Column(db.String(500))
    
    # Seguimiento
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    
    # Relaciones
    blacklist_entry = db.relationship('BlacklistEntry', backref='appeals')
    reviewed_by = db.relationship('Operator')
    
    def __repr__(self) -> str:
        return f"<BlacklistAppeal #{self.id} - {self.appellant_name}>"
    
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """Convertir a diccionario"""
        data = super().to_dict()
        
        # Convertir enums
        data['status'] = self.status.value if self.status else None
        
        if include_relationships:
            if self.blacklist_entry:
                data['blacklist_entry'] = self.blacklist_entry.to_dict()
            if self.reviewed_by:
                data['reviewed_by'] = {
                    'id': self.reviewed_by.id,
                    'name': self.reviewed_by.full_name
                }
        
        return data