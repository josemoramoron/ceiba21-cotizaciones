"""
Servicio de Verificación de Fraude.

RESPONSABILIDADES:
- Integración con APIs de verificación
- Check de números telefónicos
- Verificación de emails
- Check contra listas de estafadores
- Cálculo de risk score
"""
from app.services.base_service import BaseService
from typing import Dict, Any, Optional
import requests
import os


class FraudCheckService(BaseService):
    """
    Servicio para verificación de fraude usando APIs externas.
    
    APIs soportadas:
    - Numverify (verificación de teléfonos)
    - Twilio Lookup (verificación de teléfonos)
    - Email verification APIs
    - Listas públicas de estafadores
    """
    
    # Configuración de APIs (desde variables de entorno)
    NUMVERIFY_API_KEY = os.getenv('NUMVERIFY_API_KEY')
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    
    # Timeout para requests
    REQUEST_TIMEOUT = 5
    
    # ==========================================
    # MÉTODO PRINCIPAL
    # ==========================================
    
    @classmethod
    def check_all(cls,
                  telegram_id: Optional[int] = None,
                  phone: Optional[str] = None,
                  email: Optional[str] = None) -> Dict[str, Any]:
        """
        Ejecutar todas las verificaciones disponibles.
        
        Args:
            telegram_id: ID de Telegram
            phone: Número de teléfono
            email: Email
            
        Returns:
            {
                'risk_score': 0-100,
                'checks': {
                    'phone': {...},
                    'telegram': {...},
                    'email': {...}
                },
                'flags': [],
                'recommendation': 'allow' | 'review' | 'block'
            }
        """
        result = {
            'risk_score': 0,
            'checks': {},
            'flags': [],
            'recommendation': 'allow'
        }
        
        # Check de teléfono
        if phone:
            phone_check = cls.check_phone(phone)
            result['checks']['phone'] = phone_check
            result['risk_score'] += phone_check.get('risk_points', 0)
            result['flags'].extend(phone_check.get('flags', []))
        
        # Check de Telegram ID (contra listas conocidas)
        if telegram_id:
            telegram_check = cls.check_telegram_id(telegram_id)
            result['checks']['telegram'] = telegram_check
            result['risk_score'] += telegram_check.get('risk_points', 0)
            result['flags'].extend(telegram_check.get('flags', []))
        
        # Check de email
        if email:
            email_check = cls.check_email(email)
            result['checks']['email'] = email_check
            result['risk_score'] += email_check.get('risk_points', 0)
            result['flags'].extend(email_check.get('flags', []))
        
        # Calcular recomendación
        if result['risk_score'] >= 70:
            result['recommendation'] = 'block'
        elif result['risk_score'] >= 40:
            result['recommendation'] = 'review'
        else:
            result['recommendation'] = 'allow'
        
        cls.log_action('fraud_check_completed', {
            'risk_score': result['risk_score'],
            'recommendation': result['recommendation'],
            'flags_count': len(result['flags'])
        })
        
        return result
    
    # ==========================================
    # VERIFICACIÓN DE TELÉFONO
    # ==========================================
    
    @classmethod
    def check_phone(cls, phone: str) -> Dict[str, Any]:
        """
        Verificar número de teléfono usando Numverify o Twilio.
        
        Detecta:
        - Números temporales/desechables
        - Números VOIP
        - País de origen
        - Validez del número
        
        Args:
            phone: Número de teléfono (formato internacional)
            
        Returns:
            {
                'valid': bool,
                'country': str,
                'line_type': str,
                'carrier': str,
                'risk_points': int,
                'flags': list,
                'provider': str
            }
        """
        risk_points = 0
        flags = []
        
        try:
            # Intentar con Numverify primero (API gratuita)
            if cls.NUMVERIFY_API_KEY:
                response = requests.get(
                    'http://apilayer.net/api/validate',
                    params={
                        'access_key': cls.NUMVERIFY_API_KEY,
                        'number': phone,
                        'format': 1
                    },
                    timeout=cls.REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verificar validez
                    if not data.get('valid'):
                        risk_points += 20
                        flags.append('invalid_number')
                    
                    # Verificar tipo de línea
                    line_type = data.get('line_type', '').lower()
                    if line_type == 'mobile':
                        risk_points += 0  # Normal
                    elif line_type in ['voip', 'virtual', 'paging']:
                        risk_points += 30
                        flags.append('voip_number')
                    elif line_type == 'toll_free':
                        risk_points += 50
                        flags.append('toll_free_number')
                    
                    return {
                        'valid': data.get('valid'),
                        'country': data.get('country_name'),
                        'country_code': data.get('country_code'),
                        'line_type': data.get('line_type'),
                        'carrier': data.get('carrier'),
                        'risk_points': risk_points,
                        'flags': flags,
                        'provider': 'numverify'
                    }
            
            # Fallback: Twilio Lookup (requiere cuenta de pago)
            elif cls.TWILIO_ACCOUNT_SID and cls.TWILIO_AUTH_TOKEN:
                try:
                    from twilio.rest import Client
                    client = Client(cls.TWILIO_ACCOUNT_SID, cls.TWILIO_AUTH_TOKEN)
                    
                    phone_number = client.lookups.v1.phone_numbers(phone).fetch(
                        type=['carrier']
                    )
                    
                    # Analizar tipo de portador
                    carrier_type = phone_number.carrier.get('type', '').lower()
                    if carrier_type in ['voip', 'landline']:
                        risk_points += 20
                        flags.append(f'{carrier_type}_number')
                    
                    return {
                        'valid': True,
                        'country': phone_number.country_code,
                        'line_type': carrier_type,
                        'carrier': phone_number.carrier.get('name'),
                        'risk_points': risk_points,
                        'flags': flags,
                        'provider': 'twilio'
                    }
                except Exception as e:
                    cls.log_error('twilio_lookup_failed', {'error': str(e)})
        
        except Exception as e:
            cls.log_error('phone_check_failed', {'error': str(e), 'phone': phone})
        
        # Si falla o no hay API configurada, retornar neutral
        return {
            'valid': None,
            'country': None,
            'line_type': 'unknown',
            'carrier': None,
            'risk_points': 0,
            'flags': ['check_unavailable'],
            'provider': 'none'
        }
    
    # ==========================================
    # VERIFICACIÓN DE TELEGRAM
    # ==========================================
    
    @classmethod
    def check_telegram_id(cls, telegram_id: int) -> Dict[str, Any]:
        """
        Check contra lista local de Telegram IDs conocidos como estafadores.
        
        Args:
            telegram_id: ID de usuario de Telegram
            
        Returns:
            {
                'telegram_id': int,
                'in_scammer_list': bool,
                'risk_points': int,
                'flags': list
            }
        """
        risk_points = 0
        flags = []
        in_scammer_list = False
        
        try:
            # Check contra base de datos local de estafadores conocidos
            # (Implementar tabla scammer_list en el futuro)
            
            # TODO: Integrar con APIs públicas como:
            # - ScamShield
            # - Stop Scam List
            # - Etc.
            
            # Por ahora, solo check básico
            from app.models.blacklist import BlacklistEntry, BlacklistStatus
            
            # Verificar si este telegram_id ya está en blacklist activa
            existing_block = BlacklistEntry.query.filter(
                BlacklistEntry.telegram_id == telegram_id,
                BlacklistEntry.status == BlacklistStatus.ACTIVE
            ).first()
            
            if existing_block:
                risk_points += 100  # Máximo riesgo
                flags.append('already_blacklisted')
                in_scammer_list = True
            
        except Exception as e:
            cls.log_error('telegram_check_failed', {'error': str(e)})
        
        return {
            'telegram_id': telegram_id,
            'in_scammer_list': in_scammer_list,
            'risk_points': risk_points,
            'flags': flags
        }
    
    # ==========================================
    # VERIFICACIÓN DE EMAIL
    # ==========================================
    
    @classmethod
    def check_email(cls, email: str) -> Dict[str, Any]:
        """
        Verificar email.
        
        Detecta:
        - Emails temporales/desechables
        - Emails sospechosos
        - Dominio del email
        
        Args:
            email: Dirección de email
            
        Returns:
            {
                'email': str,
                'domain': str,
                'is_disposable': bool,
                'is_free_provider': bool,
                'risk_points': int,
                'flags': list
            }
        """
        risk_points = 0
        flags = []
        
        try:
            # Extraer dominio
            domain = email.split('@')[-1].lower() if '@' in email else ''
            
            # Lista de dominios temporales conocidos
            temp_domains = [
                'tempmail.com', 'guerrillamail.com', '10minutemail.com',
                'mailinator.com', 'throwaway.email', 'temp-mail.org',
                'maildrop.cc', 'sharklasers.com', 'guerrillamail.info',
                'grr.la', 'guerrillamail.biz', 'guerrillamail.de',
                'yopmail.com', 'cool.fr.nf', 'jetable.fr.nf',
                'nospam.ze.tc', 'nomail.xl.cx', 'mega.zik.dj',
                'speed.1s.fr', 'courriel.fr.nf', 'moncourrier.fr.nf',
                'trashmail.com', 'trash-mail.com', 'spambog.com'
            ]
            
            # Lista de proveedores gratuitos (menor riesgo pero aún relevante)
            free_providers = [
                'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
                'live.com', 'aol.com', 'icloud.com', 'mail.com',
                'protonmail.com', 'zoho.com'
            ]
            
            # Check si es temporal
            is_disposable = domain in temp_domains
            if is_disposable:
                risk_points += 40
                flags.append('disposable_email')
            
            # Check si es proveedor gratuito
            is_free_provider = domain in free_providers
            if is_free_provider:
                risk_points += 5
                flags.append('free_email_provider')
            
            # Check formato sospechoso (muchos números)
            local_part = email.split('@')[0] if '@' in email else email
            digit_count = sum(c.isdigit() for c in local_part)
            if digit_count > len(local_part) * 0.5:  # Más del 50% números
                risk_points += 10
                flags.append('suspicious_format')
            
            # Check contra blacklist de emails
            from app.models.blacklist import BlacklistEntry, BlacklistStatus
            existing_block = BlacklistEntry.query.filter(
                BlacklistEntry.email == email,
                BlacklistEntry.status == BlacklistStatus.ACTIVE
            ).first()
            
            if existing_block:
                risk_points += 100
                flags.append('already_blacklisted')
            
        except Exception as e:
            cls.log_error('email_check_failed', {'error': str(e)})
        
        return {
            'email': email,
            'domain': domain,
            'is_disposable': is_disposable,
            'is_free_provider': is_free_provider,
            'risk_points': risk_points,
            'flags': flags
        }
    
    # ==========================================
    # APIS EXTERNAS (FUTURO)
    # ==========================================
    
    @classmethod
    def check_against_public_scammer_lists(cls, 
                                          phone: Optional[str] = None,
                                          telegram_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Check contra listas públicas de estafadores.
        
        APIs potenciales:
        - https://scamshield.org/
        - https://stopscam.io/
        - Listas de Telegram públicas
        
        TODO: Implementar cuando tengamos acceso a estas APIs
        
        Args:
            phone: Número de teléfono
            telegram_id: ID de Telegram
            
        Returns:
            {
                'found': bool,
                'sources': list,
                'reports_count': int
            }
        """
        # Placeholder para implementación futura
        return {
            'found': False,
            'sources': [],
            'reports_count': 0,
            'provider': 'not_implemented'
        }
    
    @classmethod
    def get_reputation_score(cls, identifier: str, identifier_type: str) -> int:
        """
        Obtener score de reputación de un identificador.
        
        TODO: Implementar sistema de reputación basado en:
        - Historial de transacciones exitosas
        - Cancelaciones
        - Reportes previos
        - Tiempo como cliente
        
        Args:
            identifier: El identificador (phone, email, telegram_id)
            identifier_type: Tipo de identificador
            
        Returns:
            Score de 0-100 (mayor = mejor reputación)
        """
        # Placeholder para implementación futura
        return 50  # Neutral por defecto
    
    # ==========================================
    # UTILIDADES
    # ==========================================
    
    @classmethod
    def is_api_configured(cls, api_name: str) -> bool:
        """
        Verificar si una API está configurada.
        
        Args:
            api_name: 'numverify', 'twilio', etc.
            
        Returns:
            True si la API está configurada
        """
        if api_name == 'numverify':
            return bool(cls.NUMVERIFY_API_KEY)
        elif api_name == 'twilio':
            return bool(cls.TWILIO_ACCOUNT_SID and cls.TWILIO_AUTH_TOKEN)
        return False
    
    @classmethod
    def get_configured_apis(cls) -> list:
        """Obtener lista de APIs configuradas"""
        apis = []
        if cls.is_api_configured('numverify'):
            apis.append('numverify')
        if cls.is_api_configured('twilio'):
            apis.append('twilio')
        return apis
    
    @classmethod
    def calculate_risk_level(cls, risk_score: int) -> str:
        """
        Calcular nivel de riesgo basado en score.
        
        Args:
            risk_score: Score de 0-100
            
        Returns:
            'low', 'medium', 'high', 'critical'
        """
        if risk_score < 20:
            return 'low'
        elif risk_score < 40:
            return 'medium'
        elif risk_score < 70:
            return 'high'
        else:
            return 'critical'