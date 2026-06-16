"""
Inicialización de modelos
Importa todos los modelos para que SQLAlchemy los reconozca
"""
from flask_sqlalchemy import SQLAlchemy

# Crear instancia de base de datos
db = SQLAlchemy()

# Importar modelos existentes
from app.models.currency import Currency
from app.models.payment_method import PaymentMethod
from app.models.quote import Quote
from app.models.quote_history import QuoteHistory
from app.models.exchange_rate import ExchangeRate

# ✨ NUEVOS MODELOS - FASE 1: Sistema de Órdenes
from app.models.base import BaseModel
from app.models.user import User
from app.models.operator import Operator, OperatorRole
from app.models.order import Order, OrderStatus
from app.models.transaction import Transaction, TransactionType
from app.models.message import Message
from app.models.web_user import WebUser

# Pagos (sistema unificado)
from app.models.payment import Payment, PaymentProvider, PaymentStatus, PaypalSubtipo
from app.models.payment_source import PaymentSource

# Configuración del sistema
from app.models.system_config import SystemConfig

# Módulo SMS
from app.models.sim_slot import SimSlot
from app.models.sms_message import SmsMessage, SmsDirection, SmsStatus

# Exportar para facilitar importación
__all__ = [
    'db',
    # Modelos existentes
    'Currency',
    'PaymentMethod',
    'Quote',
    'QuoteHistory',
    'ExchangeRate',
    # Nuevos modelos
    'BaseModel',
    'User',
    'Operator',
    'OperatorRole',
    'Order',
    'OrderStatus',
    'Transaction',
    'TransactionType',
    'Message',
    'WebUser',
    # Pagos (sistema unificado)
    'Payment',
    'PaymentProvider',
    'PaymentStatus',
    'PaypalSubtipo',
    'PaymentSource',
    # Configuración del sistema
    'SystemConfig',
    # Módulo SMS
    'SimSlot',
    'SmsMessage',
    'SmsDirection',
    'SmsStatus',
]
