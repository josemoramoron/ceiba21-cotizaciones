"""
Templates de respuestas del bot.
Todos los mensajes que el bot envía a los usuarios.

REGLA DE ORO: NO hacer queries a la base de datos aquí.
Solo retornar strings y recibir datos ya serializados.

SOLUCIÓN AL ERROR: Recibir SOLO datos primitivos (dict, str, int)
NUNCA objetos SQLAlchemy.

FORMATO: HTML (más simple y robusto que Markdown V2)
"""
from typing import Dict, Any, List


class Responses:
    """
    Clase con todos los templates de mensajes del bot.
    
    Cada método retorna un dict con:
    - 'text': Mensaje a enviar (en formato HTML)
    - 'buttons': Lista de botones (opcional)
    
    IMPORTANTE: Todos los parámetros deben ser datos primitivos,
    NUNCA objetos SQLAlchemy.
    """
    
    @staticmethod
    def welcome_message(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mensaje de bienvenida con menú principal"""
        name = user_data.get('first_name', user_data.get('display_name', 'Amigo'))
        
        text = f'''¡Hola {name}! 👋 Bienvenido a <b>Ceiba21</b> 🌳

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
        text = '''<b>Ceiba21 - Ayuda</b> 💬

<b>Comandos disponibles:</b>
• /start - Iniciar conversación
• /cancel - Cancelar operación actual
• /status - Ver estado de última orden
• /help - Ver esta ayuda

<b>¿Cómo hacer una operación?</b>
1. Selecciona la moneda que recibirás
2. Elige tu método de pago
3. Ingresa el monto a enviar
4. Confirma el cálculo
5. Proporciona tus datos bancarios
6. Realiza el pago
7. Envía el comprobante

<b>Soporte:</b>
📧 Email: ceiba21.oficial@gmail.com
📱 WhatsApp: +57 302 210 0056
🌐 Web: ceiba21.com

Escribe /start para comenzar.'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def paginate_items(items: List[Any], page: int, items_per_page: int = 6) -> tuple:
        """Paginar lista de items."""
        if not items:
            return [], 0
        
        total_pages = (len(items) + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages - 1))
        
        start = page * items_per_page
        end = start + items_per_page
        return items[start:end], total_pages
    
    @staticmethod
    def select_currency_message(currencies_list: List[Dict[str, Any]], page: int = 0) -> Dict[str, Any]:
        """Solicitar selección de moneda con paginación."""
        currencies_page, total_pages = Responses.paginate_items(currencies_list, page, items_per_page=6)
        
        text = '''Perfecto! Vamos a crear tu operación.

<b>¿Qué moneda recibirás?</b> 💰'''
        
        flag_map = {
            'VES': '🇻🇪', 'COP': '🇨🇴', 'CLP': '🇨🇱', 'ARS': '🇦🇷',
            'BRL': '🇧🇷', 'MXN': '🇲🇽', 'PEN': '🇵🇪', 'UYU': '🇺🇾',
            'EUR': '🇪🇺', 'USD': '🇺🇸'
        }
        
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
        
        if row:
            buttons.append(row)
        
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append({'text': '⬅️ Anterior', 'callback_data': 'currency_page:prev'})
            nav_buttons.append({'text': f'📄 {page + 1}/{total_pages}', 'callback_data': 'page_info:ignore'})
            if page < total_pages - 1:
                nav_buttons.append({'text': 'Siguiente ➡️', 'callback_data': 'currency_page:next'})
            buttons.append(nav_buttons)
        
        return {'text': text, 'buttons': buttons}
    
    @staticmethod
    def select_payment_method_message(currency_code: str, currency_name: str, methods_list: List[Dict[str, Any]], page: int = 0) -> Dict[str, Any]:
        """Solicitar método de pago con paginación."""
        methods_page, total_pages = Responses.paginate_items(methods_list, page, items_per_page=6)
        
        flag_map = {'VES': '🇻🇪', 'COP': '🇨🇴', 'CLP': '🇨🇱', 'ARS': '🇦🇷', 'BRL': '🇧🇷', 'MXN': '🇲🇽'}
        flag = flag_map.get(currency_code, '💵')
        
        text = f'''Excelente! Recibirás <b>{currency_name}</b> {flag}

<b>¿Con qué método de pago enviarás?</b> 💳'''
        
        icon_map = {
            'PayPal': '💳', 'Zelle': '💵', 'USDT': '₿', 'Wise': '🌍',
            'Zinli': '💰', 'REF': '🏦', 'Binance': '🔶',
            'Venmo': '💸', 'Airtm': '🔷', 'Payoneer': '🎯'
        }
        
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
        
        if row:
            buttons.append(row)
        
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append({'text': '⬅️ Anterior', 'callback_data': 'method_page:prev'})
            nav_buttons.append({'text': f'📄 {page + 1}/{total_pages}', 'callback_data': 'page_info:ignore'})
            if page < total_pages - 1:
                nav_buttons.append({'text': 'Siguiente ➡️', 'callback_data': 'method_page:next'})
            buttons.append(nav_buttons)
        
        buttons.append([{'text': '🔙 Cambiar moneda', 'callback_data': 'back:select_currency'}])
        
        return {'text': text, 'buttons': buttons}
    
    @staticmethod
    def enter_amount_message(method_name: str) -> Dict[str, Any]:
        """Solicitar monto a enviar"""
        icon_map = {'PayPal': '💳', 'Zelle': '💵', 'USDT': '₿', 'Wise': '🌍', 'Zinli': '💰'}
        icon = icon_map.get(method_name, '💳')
        
        text = f'''Método seleccionado: <b>{method_name}</b> {icon}

<b>¿Qué cantidad ENVIARÁS?</b> 💵

Ingresa el monto en USD (dólares).

<b>Ejemplo:</b> 100'''
        
        if method_name == 'PayPal':
            text += '''\n\n⚠️ <b>Nota importante:</b>
PayPal cobra una comisión de plataforma (5.4% + $0.30).
Te mostraremos el monto neto que recibiremos y calcularemos tu pago basado en eso.'''
        else:
            text += '''\n\n⚠️ <b>Nota:</b> Si tu banco o plataforma cobra comisión por la transferencia, esta corre por tu cuenta. Solo te pagaremos el monto neto que recibamos.'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def confirm_calculation_message(data: Dict[str, Any]) -> Dict[str, Any]:
        """Mostrar resumen del cálculo y pedir confirmación"""
        calc = data['calculation']
        method_name = data.get('payment_method_from_name', 'N/A')
        
        # Formatear números (sin escape necesario en HTML)
        amount_usd = f"{data['amount_usd']:.2f}"
        fee_usd = f"{calc['fee_usd']:.2f}"
        net_usd = f"{calc['net_usd']:.2f}"
        exchange_rate = f"{calc['exchange_rate']:.2f}"
        amount_local = f"{calc['amount_local']:,.2f}"
        currency_code = calc['currency_code']
        
        has_fee = calc['fee_usd'] > 0
        
        text = '''📊 <b>RESUMEN</b>
━━━━━━━━━━━'''
        
        if has_fee:
            text += f'''
<b>Si me envías:</b> ${amount_usd} USD
<b>Comisión {method_name}:</b> -${fee_usd} USD
<b>Recibiré:</b> ${net_usd} USD ({method_name})
<b>Recibirás:</b> {amount_local} {currency_code}
<b>Tasa aplicada:</b> {exchange_rate} {currency_code}/$'''
        else:
            text += f'''
<b>Si me envías:</b> ${amount_usd} USD ({method_name})
<b>Recibiré:</b> ${net_usd} USD
<b>Recibirás:</b> {amount_local} {currency_code}
<b>Tasa aplicada:</b> {exchange_rate} {currency_code}/$'''
        
        text += '''
━━━━━━━━━━━

<b>¿Confirmas?</b>'''
        
        buttons = [
            [
                {'text': '✅ Sí, confirmo', 'callback_data': 'confirm:yes'},
                {'text': '❌ No, cambiar monto', 'callback_data': 'confirm:no'}
            ]
        ]
        
        return {'text': text, 'buttons': buttons}
    
    @staticmethod
    def enter_bank_message() -> Dict[str, Any]:
        """Solicitar nombre del banco con opción de envío completo"""
        text = '''Excelente! ✅

Para que te enviemos los bolívares/pesos, necesito:

📌 <b>Datos de tu cuenta:</b>
1. Banco
2. Número de cuenta (20 dígitos)
3. Titular (nombre completo)
4. Cédula/DNI (acepta v/V minúscula/mayúscula)
5. Teléfono móvil (04XX-XXXXXXX)

💡 <b>Puedes enviar de DOS formas:</b>

<b>Opción 1:</b> Todo junto en 5 líneas ⚡

<b>Ejemplo:</b>
Banco Venezuela
01020123456789012345
Juan Pérez
V-22333444
04121234567

<b>Opción 2:</b> Uno por uno (te iré preguntando cada dato) 📝

<b>Empecemos:</b> ¿Cuál es tu banco? (o envía todo)'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def enter_account_message() -> Dict[str, Any]:
        """Solicitar número de cuenta"""
        text = '''<b>¿Número de cuenta?</b> 🏦

Ingresa los 20 dígitos sin espacios ni guiones.

<b>Ejemplo:</b> 01020123456789012345'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def enter_holder_message() -> Dict[str, Any]:
        """Solicitar nombre del titular"""
        text = '''<b>¿Nombre completo del titular de la cuenta?</b> 👤

<b>Ejemplo:</b> Juan Pérez'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def enter_dni_message(currency_code: str) -> Dict[str, Any]:
        """Solicitar cédula/DNI del titular"""
        if currency_code == 'VES':
            text = '''<b>¿Cédula o DNI del titular?</b> 🪪

<b>Formato:</b> V-12345678 o E-12345678
(Se acepta v minúscula)

<b>Ejemplo:</b> V-12345678'''
        elif currency_code == 'COP':
            text = '''<b>¿Cédula del titular?</b> 🪪

Ingresa tu número de cédula (6-10 dígitos).

<b>Ejemplo:</b> 12345678'''
        elif currency_code == 'CLP':
            text = '''<b>¿RUT del titular?</b> 🪪

<b>Formato:</b> 12345678-9

<b>Ejemplo:</b> 12345678-9'''
        elif currency_code == 'ARS':
            text = '''<b>¿DNI del titular?</b> 🪪

Ingresa tu DNI (7-8 dígitos).

<b>Ejemplo:</b> 12345678'''
        else:
            text = '''<b>¿Documento de identidad del titular?</b> 🪪

<b>Ejemplo:</b> 12345678'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def enter_phone_message(currency_code: str) -> Dict[str, Any]:
        """Solicitar teléfono móvil del titular"""
        if currency_code == 'VES':
            text = '''<b>¿Teléfono móvil?</b> 📱

<b>Formato:</b> 04XX-XXXXXXX (11 dígitos)

<b>Ejemplo:</b> 04121234567'''
        elif currency_code == 'COP':
            text = '''<b>¿Teléfono móvil?</b> 📱

<b>Formato:</b> 3XX-XXXXXXX (10 dígitos, inicia con 3)

<b>Ejemplo:</b> 3001234567'''
        elif currency_code == 'CLP':
            text = '''<b>¿Teléfono móvil?</b> 📱

<b>Formato:</b> 9XXXXXXXX (9 dígitos, inicia con 9)

<b>Ejemplo:</b> 912345678'''
        elif currency_code == 'ARS':
            text = '''<b>¿Teléfono móvil?</b> 📱

<b>Formato:</b> 10 dígitos

<b>Ejemplo:</b> 1112345678'''
        else:
            text = '''<b>¿Teléfono móvil?</b> 📱

<b>Ejemplo:</b> 04121234567'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def confirm_data_message(data: Dict[str, Any]) -> Dict[str, Any]:
        """Vista previa de los datos aportados, antes de crear la orden."""
        calc = data.get('calculation', {})
        method_name = data.get('payment_method_from_name', 'N/A')
        amount_usd = data.get('amount_usd', 0)
        amount_local = calc.get('amount_local', 0)
        currency_code = calc.get('currency_code', data.get('currency_code', ''))

        text = f'''📝 <b>Revisa tus datos</b>

<b>Operación</b>
💳 Método: {method_name}
💵 Envías: ${amount_usd:.2f} USD
💰 Recibes: {amount_local:,.2f} {currency_code}

<b>Cuenta destino</b>
🏦 Banco: {data.get('bank', '')}
🔢 Cuenta: {data.get('account', '')}
👤 Titular: {data.get('holder', '')}
🪪 Cédula: {data.get('dni', '')}
📱 Teléfono: {data.get('phone', '')}

¿Todo correcto?'''

        buttons = [
            [
                {'text': '✅ Confirmar', 'callback_data': 'confirm:yes'},
                {'text': '❌ Cancelar', 'callback_data': 'confirm:no'}
            ]
        ]

        return {'text': text, 'buttons': buttons}

    @staticmethod
    def payment_instructions_message(data: Dict[str, Any]) -> Dict[str, Any]:
        """Instrucciones de pago.

        Los datos de cobro (correo, wallet, cuenta) provienen del método de pago
        en la base de datos (`PaymentMethod.datos_receptor`), no de código.
        """
        method_name = data.get('payment_method_from_name', 'N/A')
        amount_usd = data.get('amount_usd', 0)
        order_reference = data.get('order_reference', 'N/A')
        datos_receptor = (data.get('datos_receptor') or '').strip()

        text = f'''Perfecto! ✅ <b>Datos verificados</b>

📋 <b>ORDEN:</b> {order_reference}

<b>Ahora envía tu pago:</b>
━━━━━━━━━━━
💳 <b>Método:</b> {method_name}
💰 <b>Monto EXACTO:</b> ${amount_usd:.2f} USD
📝 <b>Referencia:</b> {order_reference}'''

        if datos_receptor:
            text += f'''

<b>Datos para el pago:</b>
{datos_receptor}'''
        else:
            text += '''

⚠️ Un operador te enviará enseguida los datos de pago.'''

        text += '''
━━━━━━━━━━━

⚠️ <b>IMPORTANTE:</b>
• Verifica el monto exacto
• Incluye la referencia
• Guarda el comprobante

Una vez realizado el pago, <b>envía la captura de pantalla del comprobante.</b>

📸 <b>El comprobante debe mostrar:</b>
• Monto exacto
• Fecha y hora
• Estado: Completado/Exitoso'''

        return {'text': text, 'buttons': None}
    
    @staticmethod
    def proof_received_success_message(order_reference: str) -> Dict[str, Any]:
        """Confirmación de comprobante recibido"""
        text = f'''✅ <b>¡Comprobante recibido!</b>

📋 <b>Orden:</b> {order_reference}
⏳ <b>Estado:</b> Verificando pago

Un operador verificará tu pago y realizará la transferencia en breve.
Te notificaremos cuando tus fondos estén en camino.

⏱️ <b>Tiempo estimado:</b> 10-30 minutos

<b>¡Gracias por usar Ceiba21!</b> 💚

Para nueva operación: /start'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def bot_disabled_message() -> Dict[str, Any]:
        """Mensaje cuando el bot está deshabilitado"""
        text = '''⚠️ <b>El bot está temporalmente en mantenimiento.</b>

Un operador te atenderá pronto.

📞 <b>Para contacto inmediato:</b>
• WhatsApp: +57 302 210 0056
• Email: ceiba21.oficial@gmail.com
• Telegram: @ceiba21_soporte

Disculpa las molestias.'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def transferred_to_operator_message() -> Dict[str, Any]:
        """Mensaje cuando se transfiere a operador"""
        text = '''👤 <b>Un operador está revisando tu caso personalmente.</b>

Te responderemos en breve.

Gracias por tu paciencia. 💚'''
        
        return {'text': text, 'buttons': None}
    
    @staticmethod
    def format_buttons_for_telegram(buttons: List[List[Dict]]):
        """Convertir lista de botones a formato de Telegram InlineKeyboardMarkup."""
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
