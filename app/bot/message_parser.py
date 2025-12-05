"""
Parser y validador de mensajes del usuario.
Valida inputs antes de procesarlos en el ConversationHandler.
"""
import re
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal, InvalidOperation


class MessageParser:
    """
    Parser de mensajes con validaciones robustas.
    
    Responsabilidades:
    - Validar montos numéricos
    - Validar números de cuenta bancaria
    - Validar cédulas/DNI
    - Parsear selecciones de botones
    - Sanitizar inputs
    """
    
    # Patrones regex
    AMOUNT_PATTERN = re.compile(r'^\d+(\.\d{1,2})?$')
    ACCOUNT_PATTERN = re.compile(r'^\d{20}$')  # 20 dígitos exactos
    DNI_VENEZUELA_PATTERN = re.compile(r'^[VEve]-?\d{6,9}$', re.IGNORECASE)
    DNI_COLOMBIA_PATTERN = re.compile(r'^\d{6,10}$')
    DNI_CHILE_PATTERN = re.compile(r'^\d{7,8}-[0-9Kk]$')
    DNI_ARGENTINA_PATTERN = re.compile(r'^\d{7,8}$')
    
    # Límites
    MIN_AMOUNT = Decimal('1.00')
    MAX_AMOUNT = Decimal('10000.00')
    
    @classmethod
    def validate_amount(cls, text: str) -> Tuple[bool, Optional[Decimal], Optional[str]]:
        """
        Validar que el texto sea un monto válido.
        
        Args:
            text: Texto ingresado por el usuario
            
        Returns:
            Tupla (es_valido, monto_decimal, mensaje_error)
            
        Ejemplos:
            >>> validate_amount("100")
            (True, Decimal('100.00'), None)
            
            >>> validate_amount("abc")
            (False, None, "Monto inválido. Ingresa solo números.")
        """
        # Limpiar espacios
        text = text.strip()
        
        # Verificar patrón básico
        if not cls.AMOUNT_PATTERN.match(text):
            return False, None, "❌ Monto inválido. Ingresa solo números.\n\nEjemplo: 100 o 50.50"
        
        # Convertir a Decimal
        try:
            amount = Decimal(text)
        except InvalidOperation:
            return False, None, "❌ Monto inválido. Ingresa solo números."
        
        # Verificar límites
        if amount < cls.MIN_AMOUNT:
            return False, None, f"❌ Monto mínimo: ${cls.MIN_AMOUNT}"
        
        if amount > cls.MAX_AMOUNT:
            return False, None, f"❌ Monto máximo: ${cls.MAX_AMOUNT}"
        
        return True, amount, None
    
    @classmethod
    def validate_account(cls, text: str, country_code: str = 'VE') -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validar número de cuenta bancaria.
        
        Args:
            text: Número de cuenta ingresado
            country_code: Código del país (VE, CO, CL, AR)
            
        Returns:
            Tupla (es_valido, cuenta_limpia, mensaje_error)
        """
        # Limpiar espacios, guiones y otros caracteres
        text = text.strip().replace(' ', '').replace('-', '')
        
        # Validar según país
        if country_code == 'VE':
            # Venezuela: 20 dígitos exactos
            if not cls.ACCOUNT_PATTERN.match(text):
                return False, None, "❌ Cuenta inválida. Debe tener 20 dígitos.\n\nEjemplo: 01020123456789012345"
        elif country_code == 'CO':
            # Colombia: 10-16 dígitos
            if not re.match(r'^\d{10,16}$', text):
                return False, None, "❌ Cuenta inválida. Debe tener entre 10 y 16 dígitos."
        elif country_code in ['CL', 'AR']:
            # Chile/Argentina: flexible, al menos 8 dígitos
            if not re.match(r'^\d{8,20}$', text):
                return False, None, "❌ Cuenta inválida. Debe tener al menos 8 dígitos."
        
        return True, text, None
    
    @classmethod
    def validate_holder_name(cls, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validar nombre del titular de cuenta.
        
        Args:
            text: Nombre ingresado
            
        Returns:
            Tupla (es_valido, nombre_limpio, mensaje_error)
        """
        # Limpiar espacios extra
        text = ' '.join(text.strip().split())
        
        # Verificar longitud mínima
        if len(text) < 3:
            return False, None, "❌ Nombre muy corto. Ingresa nombre completo."
        
        # Verificar que tenga al menos nombre y apellido
        parts = text.split()
        if len(parts) < 2:
            return False, None, "❌ Ingresa nombre y apellido completo.\n\nEjemplo: Juan Pérez"
        
        # Verificar que solo contenga letras, espacios y algunos caracteres especiales
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s'.-]+$", text):
            return False, None, "❌ Nombre inválido. Solo letras y espacios."
        
        return True, text, None
    
    @classmethod
    def validate_dni(cls, text: str, country_code: str = 'VE') -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validar cédula/DNI según el país.
        
        Args:
            text: Cédula/DNI ingresado
            country_code: Código del país (VE, CO, CL, AR)
            
        Returns:
            Tupla (es_valido, dni_limpio, mensaje_error)
        """
        text = text.strip().upper()
        
        if country_code == 'VE':
            # Venezuela: V-12345678 o E-12345678
            if not cls.DNI_VENEZUELA_PATTERN.match(text):
                return False, None, "❌ Cédula inválida.\n\nFormato: V-12345678 o E-12345678"
            
            # Normalizar (agregar guion si no lo tiene)
            if '-' not in text:
                text = text[0] + '-' + text[1:]
        
        elif country_code == 'CO':
            # Colombia: solo números
            if not cls.DNI_COLOMBIA_PATTERN.match(text):
                return False, None, "❌ Cédula inválida.\n\nDebe tener entre 6 y 10 dígitos."
        
        elif country_code == 'CL':
            # Chile: formato 12345678-9 o 12345678-K
            if not cls.DNI_CHILE_PATTERN.match(text):
                return False, None, "❌ RUT inválido.\n\nFormato: 12345678-9"
        
        elif country_code == 'AR':
            # Argentina: solo números
            if not cls.DNI_ARGENTINA_PATTERN.match(text):
                return False, None, "❌ DNI inválido.\n\nDebe tener 7 u 8 dígitos."
        
        return True, text, None
    
    @classmethod
    def validate_bank_name(cls, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validar nombre del banco.
        
        Args:
            text: Nombre del banco ingresado
            
        Returns:
            Tupla (es_valido, banco_limpio, mensaje_error)
        """
        text = text.strip()
        
        if len(text) < 3:
            return False, None, "❌ Nombre de banco muy corto."
        
        if len(text) > 100:
            return False, None, "❌ Nombre de banco muy largo."
        
        return True, text, None
    
    @classmethod
    def parse_callback_data(cls, callback_data: str) -> Dict[str, Any]:
        """
        Parsear datos de callback de botones inline.
        
        Args:
            callback_data: String en formato "accion:parametro"
            
        Returns:
            Dict con 'action' y 'value'
            
        Ejemplos:
            >>> parse_callback_data("currency:1")
            {'action': 'currency', 'value': '1'}
            
            >>> parse_callback_data("confirm:yes")
            {'action': 'confirm', 'value': 'yes'}
        """
        parts = callback_data.split(':', 1)
        
        if len(parts) == 2:
            return {
                'action': parts[0],
                'value': parts[1]
            }
        
        return {
            'action': callback_data,
            'value': None
        }
    
    @classmethod
    def sanitize_input(cls, text: str, max_length: int = 500) -> str:
        """
        Sanitizar input del usuario.
        
        Args:
            text: Texto a sanitizar
            max_length: Longitud máxima permitida
            
        Returns:
            Texto sanitizado
        """
        # Limpiar espacios
        text = text.strip()
        
        # Limitar longitud
        if len(text) > max_length:
            text = text[:max_length]
        
        # Remover caracteres de control
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text
    
    @classmethod
    def is_command(cls, text: str) -> bool:
        """
        Verificar si el texto es un comando de Telegram.
        
        Args:
            text: Texto a verificar
            
        Returns:
            bool: True si es comando
        """
        return text.strip().startswith('/')
    
    @classmethod
    def extract_command(cls, text: str) -> Optional[str]:
        """
        Extraer comando de Telegram.
        
        Args:
            text: Texto con comando
            
        Returns:
            Comando sin '/' o None
        """
        text = text.strip()
        if cls.is_command(text):
            # Remover '/' y obtener solo el comando (sin argumentos)
            return text[1:].split()[0].lower()
        return None
