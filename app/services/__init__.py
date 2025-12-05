"""
Servicios de negocio (POO)
"""
# Servicios existentes
from app.services.quote_service import QuoteService
from app.services.exchange_rate_service import ExchangeRateService
from app.services.currency_service import CurrencyService
from app.services.payment_method_service import PaymentMethodService
from app.services.api_service import APIService

# ✨ NUEVOS SERVICIOS - FASE 2: Sistema de Órdenes
from app.services.base_service import BaseService
from app.services.order_service import OrderService
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.services.notification_service import NotificationService
from app.services.cache_service import CacheService

# ✨ FASE 6: Contabilidad Automática
from app.services.accounting_service import AccountingService
from app.services.bot_service import BotService

__all__ = [
    # Servicios existentes
    'QuoteService', 
    'ExchangeRateService', 
    'CurrencyService', 
    'PaymentMethodService',
    'APIService',
    # Nuevos servicios - Fase 2
    'BaseService',
    'OrderService',
    'UserService',
    'AuthService',
    'NotificationService',
    'CacheService',
    # Fase 6 - Contabilidad
    'AccountingService',
    'BotService'
]
