"""
Templates de respuestas del bot.
Todos los mensajes que el bot envía a los usuarios.

REGLA DE ORO: NO hacer queries a la base de datos aquí.
Solo retornar strings y recibir datos ya serializados.

SOLUCIÓN AL ERROR: Recibir SOLO datos primitivos (dict, str, int)
NUNCA objetos SQLAlchemy.
"""
from typing import Dict, Any, List


class Responses:
    """
    Clase con todos los templates de mensajes del bot.
    
    Cada método retorna un dict con:
    - 'text': Mensaje a enviar
    - 'buttons': Lista de botones (opcional)
    
    IMPORTANTE: Todos los parámetros deben ser datos primitivos,
    NUNCA objetos SQLAlchemy.
    """
    
    @staticmethod
    def welcome_message(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mensaje de bienvenida con menú principal
        
        Args:
            user_data: Dict con datos del usuario ya serializados
                {'id': 1, 'first_name': 'Juan', 'display_name': 'Juan'}
        """
        name = user_data.get('first_name', user_data.get('display_name', 'Amigo'))
        
        text = f'''¡Hola {name}! 👋 Bienvenido a **Ceiba21** 🌳

Cambio de divisas rápido y seguro.

¿Qué deseas hacer?'''
        
        buttons = [
            [
                {'text': '💱 Nueva operación', 'callback_data': 'action:new_operation'}
            ],
            [
                {'text': '📊 Ver cotizaciones', 'url': 'https://ceiba21.com/cotizaciones'}
            ],
            [
                {'text': '🧮 Calculadora', 'url': 'https://ceiba21.com/calculadora'}
            ],
            [
                {'text': '📋 Condiciones de uso', 'url': 'https://ceiba21.com/condiciones'}
            ],
            [
                {'text': '💬 Ayuda', 'callback_data': 'action:help'}
            ]
        ]
        
        return {'text': text, 'buttons': buttons}
    
    @staticmethod
    def main_menu_message() -> Dict[str, Any]:
        """Mostrar menú principal nuevamente"""
        text = '''¿Qué deseas hacer?'''
        
        buttons = [
            [
                {'text': '💱 Nueva operación', 'callback_data': 'action:new_operation'}
            ],
            [
                {'text': '📊 Ver cotizaciones', 'url': 'https://ceiba21.com/cotizaciones'},
                {'text': '🧮 Calculadora', 'url': 'https://ceiba21.com/calculadora'}
            ],
            [
                {'text': '💬 Ayuda', 'callback_data': 'action:help'}
            ]
        ]
        
        return {'text': text, 'buttons': buttons}
    
    @staticmethod
    def help_message() -> Dict[str, Any]:
        """Mensaje de ayuda"""
        text = '''**Ceiba21 - Ayuda** 💬

**Comandos disponibles:**
• `/start` - Iniciar conversación
• `/cancel` - Cancelar operación actual
• `/status` - Ver estado de última orden
• `/help` - Ver esta ayuda

**¿Cómo hacer una operación?**
1. Selecciona la moneda que recibirás
2. Elige tu método de pago
3. Ingresa el monto a enviar
4. Confirma el cálculo
5. Proporciona tus datos bancarios
6. Realiza el pago
7. Envía el comprobante

**Soporte:**
📧 Email: ceiba21.oficial@gmail.com
📱 WhatsApp: +57 302 210 0056
🌐 Web: ceiba21.com

Escribe `/start` para comenzar.'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def paginate_items(items: List[Any], page: int, items_per_page: int = 6) -> tuple:
        """
        Paginar lista de items.
        
        Args:
            items: Lista de items a paginar
            page: Número de página (empezando en 0)
            items_per_page: Items por página (default: 6)
            
        Returns:
            tuple: (items_page, total_pages)
        """
        if not items:
            return [], 0
        
        total_pages = (len(items) + items_per_page - 1) // items_per_page
        # Asegurar que page esté en rango válido
        page = max(0, min(page, total_pages - 1))
        
        start = page * items_per_page
        end = start + items_per_page
        return items[start:end], total_pages
    
    @staticmethod
    def select_currency_message(currencies_list: List[Dict[str, Any]], page: int = 0) -> Dict[str, Any]:
        """
        Solicitar selección de moneda con paginación.
        
        Args:
            currencies_list: Lista de diccionarios con datos de monedas SERIALIZADOS
                [{'id': 1, 'code': 'VES', 'name': 'Bolívares'}, ...]
            page: Número de página actual (default: 0)
                
        IMPORTANTE: currencies_list debe contener SOLO datos primitivos,
        NO objetos Currency.
        """
        # Paginar monedas (6 por página)
        currencies_page, total_pages = Responses.paginate_items(currencies_list, page, items_per_page=6)
        
        text = '''Perfecto! Vamos a crear tu operación.

**¿Qué moneda recibirás?** 💰'''
        
        # Mapeo de íconos de banderas
        flag_map = {
            'VES': '🇻🇪',
            'COP': '🇨🇴',
            'CLP': '🇨🇱',
            'ARS': '🇦🇷',
            'BRL': '🇧🇷',
            'MXN': '🇲🇽',
            'PEN': '🇵🇪',
            'UYU': '🇺🇾',
            'EUR': '🇪🇺',
            'USD': '🇺🇸'
        }
        
        # Crear botones (2 por fila)
        buttons = []
        row = []
        for currency in currencies_page:
            flag = flag_map.get(currency['code'], '💵')
            row.append({
                'text': f"{flag} {currency['name']}",
                'callback_data': f"currency:{currency['id']}"
            })
            if len(row) == 2:
                buttons.append(row)
                row = []
        
        # Agregar última fila si quedó algo
        if row:
            buttons.append(row)
        
        # Agregar botones de navegación si hay múltiples páginas
        if total_pages > 1:
            nav_buttons = []
            
            # Botón "Anterior" (si no es la primera página)
            if page > 0:
                nav_buttons.append({
                    'text': '⬅️ Anterior',
                    'callback_data': 'currency_page:prev'
                })
            
            # Indicador de página
            nav_buttons.append({
                'text': f'📄 {page + 1}/{total_pages}',
                'callback_data': 'page_info:ignore'
            })
            
            # Botón "Siguiente" (si no es la última página)
            if page < total_pages - 1:
                nav_buttons.append({
                    'text': 'Siguiente ➡️',
                    'callback_data': 'currency_page:next'
                })
            
            buttons.append(nav_buttons)
        
        return {'text': text, 'buttons': buttons}
    
    @staticmethod
    def select_payment_method_message(currency_code: str, currency_name: str, methods_list: List[Dict[str, Any]], page: int = 0) -> Dict[str, Any]:
        """
        Solicitar método de pago con paginación.
        
        Args:
            currency_code: Código de moneda (VES, COP, etc.) - STRING
            currency_name: Nombre de moneda - STRING
            methods_list: Lista de diccionarios con datos de métodos SERIALIZADOS
                [{'id': 1, 'name': 'PayPal', 'code': 'PAYPAL'}, ...]
            page: Número de página actual (default: 0)
        """
        # Paginar métodos (6 por página)
        methods_page, total_pages = Responses.paginate_items(methods_list, page, items_per_page=6)
        
        flag_map = {'VES': '🇻🇪', 'COP': '🇨🇴', 'CLP': '🇨🇱', 'ARS': '🇦🇷', 'BRL': '🇧🇷', 'MXN': '🇲🇽'}
        flag = flag_map.get(currency_code, '💵')
        
        text = f'''Excelente! Recibirás **{currency_name}** {flag}

**¿Con qué método de pago enviarás?** 💳'''
        
        # Íconos de métodos
        icon_map = {
            'PayPal': '💳',
            'Zelle': '💵',
            'USDT': '₿',
            'Wise': '🌍',
            'Zinli': '💰',
            'REF': '🏦',
            'Binance': '🔶',
            'Venmo': '💸',
            'Airtm': '🔷',
            'Payoneer': '🎯'
        }
        
        # Crear botones (2 por fila)
        buttons = []
        row = []
        for method in methods_page:
            icon = icon_map.get(method['name'], '💳')
            row.append({
                'text': f'{icon} {method["name"]}',
                'callback_data': f'method:{method["id"]}'
            })
            if len(row) == 2:
                buttons.append(row)
                row = []
        
        # Agregar última fila si quedó algo
        if row:
            buttons.append(row)
        
        # Agregar botones de navegación si hay múltiples páginas
        if total_pages > 1:
            nav_buttons = []
            
            # Botón "Anterior"
            if page > 0:
                nav_buttons.append({
                    'text': '⬅️ Anterior',
                    'callback_data': 'method_page:prev'
                })
            
            # Indicador de página
            nav_buttons.append({
                'text': f'📄 {page + 1}/{total_pages}',
                'callback_data': 'page_info:ignore'
            })
            
            # Botón "Siguiente"
            if page < total_pages - 1:
                nav_buttons.append({
                    'text': 'Siguiente ➡️',
                    'callback_data': 'method_page:next'
                })
            
            buttons.append(nav_buttons)
        
        # Botón para volver
        buttons.append([{
            'text': '🔙 Cambiar moneda',
            'callback_data': 'back:select_currency'
        }])
        
        return {'text': text, 'buttons': buttons}
    
    @staticmethod
    def enter_amount_message(method_name: str) -> Dict[str, Any]:
        """
        Solicitar monto a enviar
        
        Args:
            method_name: Nombre del método (STRING)
        """
        icon_map = {'PayPal': '💳', 'Zelle': '💵', 'USDT': '₿', 'Wise': '🌍', 'Zinli': '💰'}
        icon = icon_map.get(method_name, '💳')
        
        text = f'''Método seleccionado: **{method_name}** {icon}

**¿Qué cantidad ENVIARÁS?** 💵

Ingresa el monto en USD (dólares).

**Ejemplo:** 100'''
        
        # Si es PayPal, agregar nota sobre comisión
        if method_name == 'PayPal':
            text += '''\n\n⚠️ **Nota importante:**
PayPal cobra una comisión de plataforma (5.4% + $0.30).
Te mostraremos el monto neto que recibiremos y calcularemos tu pago basado en eso.'''
        else:
            text += '''\n\n⚠️ **Nota:** Si tu banco o plataforma cobra comisión por la transferencia, esta corre por tu cuenta. Solo te pagaremos el monto neto que recibamos.'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def confirm_calculation_message(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mostrar resumen del cálculo y pedir confirmación
        
        Args:
            data: Dict con TODOS los datos primitivos:
                {
                    'amount_usd': 100.0,
                    'payment_method_from_name': 'PayPal',
                    'calculation': {
                        'fee_usd': 5.70,
                        'net_usd': 94.30,
                        'exchange_rate': 305.50,
                        'amount_local': 28808.65,
                        'currency_code': 'VES'
                    }
                }
        """
        calc = data['calculation']
        method_name = data.get('payment_method_from_name', 'N/A')
        
        # Formatear números
        amount_usd = f"{data['amount_usd']:.2f}"
        fee_usd = f"{calc['fee_usd']:.2f}"
        net_usd = f"{calc['net_usd']:.2f}"
        exchange_rate = f"{calc['exchange_rate']:.2f}"
        amount_local = f"{calc['amount_local']:,.2f}"
        currency_code = calc['currency_code']
        
        # Verificar si tiene comisión
        has_fee = calc['fee_usd'] > 0
        
        text = f'''📊 **RESUMEN**
━━━━━━━━━━━'''
        
        if has_fee:
            # PayPal (con comisión)
            text += f'''
**Si me envías:** ${amount_usd} USD
**Comisión {method_name}:** -${fee_usd} USD
**Recibiré:** ${net_usd} USD ({method_name})
**Recibirás:** {amount_local} {currency_code}
**Tasa aplicada:** {exchange_rate} {currency_code}/$'''
        else:
            # Otros métodos (sin comisión)
            text += f'''
**Si me envías:** ${amount_usd} USD ({method_name})
**Recibiré:** ${net_usd} USD
**Recibirás:** {amount_local} {currency_code}
**Tasa aplicada:** {exchange_rate} {currency_code}/$'''
        
        text += '''
━━━━━━━━━━━

**¿Confirmas?**'''
        
        buttons = [
            [
                {'text': '✅ Sí, confirmo', 'callback_data': 'confirm:yes'},
                {'text': '❌ No, cambiar monto', 'callback_data': 'confirm:no'}
            ]
        ]
        
        return {'text': text, 'buttons': buttons}
    
    @staticmethod
    def enter_bank_message() -> Dict[str, Any]:
        """Solicitar nombre del banco"""
        text = '''Excelente! ✅

**Para que te enviemos los bolívares/pesos, necesito:**

📌 **Datos de tu cuenta:**
1. Banco
2. Número de cuenta
3. Titular
4. Cédula/DNI

**Empecemos: ¿Cuál es tu banco?**

**Ejemplo:** Banco Venezuela'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def enter_account_message() -> Dict[str, Any]:
        """Solicitar número de cuenta"""
        text = '''**¿Número de cuenta?** 🏦

Ingresa los 20 dígitos sin espacios ni guiones.

**Ejemplo:** 01020123456789012345'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def enter_holder_message() -> Dict[str, Any]:
        """Solicitar nombre del titular"""
        text = '''**¿Nombre completo del titular de la cuenta?** 👤

**Ejemplo:** Juan Pérez'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def enter_dni_message(currency_code: str) -> Dict[str, Any]:
        """
        Solicitar cédula/DNI del titular
        
        Args:
            currency_code: Código de moneda (STRING)
        """
        # Personalizar según país
        if currency_code == 'VES':
            text = '''**¿Cédula o DNI del titular?** 🪪

**Formato:** V-12345678 o E-12345678

**Ejemplo:** V-12345678'''
        elif currency_code == 'COP':
            text = '''**¿Cédula del titular?** 🪪

Ingresa tu número de cédula (6-10 dígitos).

**Ejemplo:** 12345678'''
        elif currency_code == 'CLP':
            text = '''**¿RUT del titular?** 🪪

**Formato:** 12345678-9

**Ejemplo:** 12345678-9'''
        elif currency_code == 'ARS':
            text = '''**¿DNI del titular?** 🪪

Ingresa tu DNI (7-8 dígitos).

**Ejemplo:** 12345678'''
        else:
            text = '''**¿Documento de identidad del titular?** 🪪

**Ejemplo:** 12345678'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def payment_instructions_message(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Instrucciones de pago
        
        Args:
            data: Dict con datos primitivos
        """
        method_name = data.get('payment_method_from_name', 'N/A')
        amount_usd = data.get('amount_usd', 0)
        order_reference = data.get('order_reference', 'N/A')
        
        text = f'''Perfecto! ✅ **Datos verificados**

📋 **ORDEN:** {order_reference}

**Ahora envía tu pago:**
━━━━━━━━━━━'''
        
        # Instrucciones específicas por método
        if method_name == 'PayPal':
            text += f'''
💳 **PayPal:** ceiba21@paypal.com
💰 **Monto EXACTO:** ${amount_usd:.2f} USD
📝 **Referencia:** {order_reference}
━━━━━━━━━━━

⚠️ **IMPORTANTE:**
• Verifica el monto exacto
• Envía como "Bienes y Servicios" o "Amigos y Familia"
• Guarda el comprobante'''
        
        elif method_name == 'Zelle':
            text += f'''
💵 **Zelle:** ceiba21@zelle.com
💰 **Monto:** ${amount_usd:.2f} USD
📝 **Nota:** {order_reference}
━━━━━━━━━━━

⚠️ **IMPORTANTE:**
• Verifica el monto exacto
• Incluye la referencia en la nota
• Guarda el comprobante'''
        
        elif method_name == 'USDT':
            text += f'''
₿ **USDT (TRC20):**
`TXyz123...` (copia la dirección completa)
💰 **Monto:** ${amount_usd:.2f} USDT
📝 **Memo:** {order_reference}
━━━━━━━━━━━

⚠️ **IMPORTANTE:**
• Verifica que sea red TRC20
• Envía el monto exacto
• Guarda el hash de transacción'''
        
        else:
            text += f'''
💳 **Método:** {method_name}
💰 **Monto:** ${amount_usd:.2f} USD
📝 **Referencia:** {order_reference}
━━━━━━━━━━━

⚠️ **IMPORTANTE:**
• Verifica el monto exacto
• Guarda el comprobante'''
        
        text += f'''\n\nUna vez realizado el pago, **envía la captura de pantalla del comprobante.**

📸 El comprobante debe mostrar:
• Monto exacto
• Fecha y hora
• Estado: Completado/Exitoso'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def proof_received_success_message(order_reference: str) -> Dict[str, Any]:
        """
        Confirmación de comprobante recibido
        
        Args:
            order_reference: Referencia de orden (STRING)
        """
        text = f'''✅ **¡Comprobante recibido!**

📋 **Orden:** {order_reference}
⏳ **Estado:** Verificando pago

Un operador verificará tu pago y realizará la transferencia en breve.
Te notificaremos cuando tus fondos estén en camino.

⏱️ **Tiempo estimado:** 10-30 minutos

**Gracias por usar Ceiba21** 💚

Para nueva operación: /start'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def bot_disabled_message() -> Dict[str, Any]:
        """Mensaje cuando el bot está deshabilitado"""
        text = '''⚠️ **El bot está temporalmente en mantenimiento.**

Un operador te atenderá pronto.

📞 **Para contacto inmediato:**
• WhatsApp: +57 302 210 0056
• Email: ceiba21.oficial@gmail.com
• Telegram: @ceiba21_soporte

Disculpa las molestias.'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def transferred_to_operator_message() -> Dict[str, Any]:
        """Mensaje cuando se transfiere a operador"""
        text = '''👤 **Un operador está revisando tu caso personalmente.**

Te responderemos en breve.

Gracias por tu paciencia. 💚'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def format_buttons_for_telegram(buttons: List[List[Dict]]):
        """
        Convertir lista de botones a formato de Telegram InlineKeyboardMarkup.
        
        Args:
            buttons: Lista de filas de botones (datos primitivos)
            
        Returns:
            InlineKeyboardMarkup de python-telegram-bot
        """
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        if not buttons:
            return None
        
        keyboard = []
        for row in buttons:
            keyboard_row = []
            for button in row:
                if 'url' in button:
                    keyboard_row.append(
                        InlineKeyboardButton(button['text'], url=button['url'])
                    )
                elif 'callback_data' in button:
                    keyboard_row.append(
                        InlineKeyboardButton(button['text'], callback_data=button['callback_data'])
                    )
            keyboard.append(keyboard_row)
        
        return InlineKeyboardMarkup(keyboard)
