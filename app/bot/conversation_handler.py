"""
Conversation Handler - Cerebro del bot conversacional.
Gestiona el flujo de conversación usando FSM (Finite State Machine).

SOLUCIÓN AL ERROR: Serializar TODOS los objetos SQLAlchemy a dict
ANTES de salir del contexto de Flask.
"""
from app.bot.states import ConversationState
from app.bot.message_parser import MessageParser
from app.services.calculator_service import CalculatorService
from app.services.order_service import OrderService
from app.services.user_service import UserService
from app.models.currency import Currency
from app.models.payment_method import PaymentMethod
from app.models.order import Order, OrderStatus
from app.models.user import User
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
import redis
import json
from datetime import datetime


class ConversationHandler:
    """
    Manejador de conversaciones del bot.
    
    RESPONSABILIDADES:
    - Gestionar estados de conversación (FSM)
    - Procesar inputs del usuario
    - Validar datos
    - Crear órdenes
    - Integrar con servicios
    
    REGLA CRÍTICA:
    NUNCA retornar objetos SQLAlchemy.
    SIEMPRE serializar a dict/primitivos.
    """
    
    # Redis client (compartido)
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True
    )
    
    # Timeout de conversación (30 minutos)
    CONVERSATION_TIMEOUT = 1800
    
    def __init__(self):
        """Inicializar handler"""
        self.parser = MessageParser()
    
    # ==========================================
    # MANEJO DE ESTADO EN REDIS
    # ==========================================
    
    def get_state(self, user: User) -> Optional[ConversationState]:
        """
        Obtener estado actual del usuario desde Redis.
        
        Args:
            user: Usuario
            
        Returns:
            ConversationState o None
        """
        state_str = self.redis_client.get(f'conv_state:{user.id}')
        if state_str:
            return ConversationState.from_string(state_str)
        return None
    
    def set_state(self, user: User, state: ConversationState):
        """
        Guardar estado del usuario en Redis.
        
        Args:
            user: Usuario
            state: Nuevo estado
        """
        self.redis_client.setex(
            f'conv_state:{user.id}',
            self.CONVERSATION_TIMEOUT,
            state.value
        )
    
    def get_data(self, user: User) -> Dict[str, Any]:
        """
        Obtener datos temporales de conversación desde Redis.
        
        Args:
            user: Usuario
            
        Returns:
            Dict con datos o dict vacío
        """
        data_str = self.redis_client.get(f'conv_data:{user.id}')
        if data_str:
            return json.loads(data_str)
        return {}
    
    def set_data(self, user: User, data: Dict[str, Any]):
        """
        Guardar datos temporales en Redis.
        
        Args:
            user: Usuario
            data: Datos a guardar
        """
        self.redis_client.setex(
            f'conv_data:{user.id}',
            self.CONVERSATION_TIMEOUT,
            json.dumps(data)
        )
    
    def clear_conversation(self, user: User):
        """
        Limpiar estado y datos de conversación.
        
        Args:
            user: Usuario
        """
        self.redis_client.delete(f'conv_state:{user.id}')
        self.redis_client.delete(f'conv_data:{user.id}')
    
    # ==========================================
    # PROCESAMIENTO DE MENSAJES
    # ==========================================
    
    def handle_message(self, user: User, message: str, current_state: Optional[ConversationState] = None) -> Dict[str, Any]:
        """
        Procesar mensaje del usuario según el estado actual.
        
        CRÍTICO: Este método DEBE ser llamado dentro de app.app_context()
        y SOLO retornar datos primitivos (dict, str, int, bool).
        
        Args:
            user: Usuario
            message: Mensaje recibido
            current_state: Estado actual (opcional, se obtiene de Redis si no se provee)
            
        Returns:
            Dict con respuesta: {'text': str, 'buttons': list, 'next_state': ConversationState}
        """
        # Obtener estado si no se proveyó
        if current_state is None:
            current_state = self.get_state(user)
        
        # Si no hay estado, iniciar conversación
        if current_state is None:
            current_state = ConversationState.START
        
        # Verificar si es comando
        if self.parser.is_command(message):
            command = self.parser.extract_command(message)
            
            if command == 'start':
                return self._handle_start(user)
            elif command == 'cancel':
                return self._handle_cancel(user)
            elif command == 'help':
                return self._handle_help(user)
            elif command == 'status':
                return self._handle_status(user)
        
        # Procesar según estado actual
        handlers = {
            ConversationState.START: self._handle_start,
            ConversationState.MAIN_MENU: self._handle_main_menu,
            ConversationState.SELECT_CURRENCY: self._handle_select_currency,
            ConversationState.SELECT_METHOD_FROM: self._handle_select_method_from,
            ConversationState.ENTER_AMOUNT: self._handle_enter_amount,
            ConversationState.CONFIRM_CALCULATION: self._handle_confirm_calculation,
            ConversationState.ENTER_BANK: self._handle_enter_bank,
            ConversationState.ENTER_ACCOUNT: self._handle_enter_account,
            ConversationState.ENTER_HOLDER: self._handle_enter_holder,
            ConversationState.ENTER_DNI: self._handle_enter_dni,
            ConversationState.AWAIT_PROOF: self._handle_await_proof,
        }
        
        handler = handlers.get(current_state)
        if handler:
            return handler(user, message)
        
        # Estado no manejado
        return {
            'text': '⚠️ Estado desconocido. Escribe /start para reiniciar.',
            'buttons': None
        }
    
    # ==========================================
    # HELPERS DE SERIALIZACIÓN
    # ==========================================
    
    @staticmethod
    def _serialize_currency(currency: Currency) -> Dict[str, Any]:
        """
        Serializar Currency a dict.
        
        CRÍTICO: Acceder a TODOS los atributos AQUÍ,
        mientras la sesión SQLAlchemy está activa.
        """
        return {
            'id': currency.id,
            'code': currency.code,
            'name': currency.name,
            'active': currency.active
        }
    
    @staticmethod
    def _serialize_payment_method(method: PaymentMethod) -> Dict[str, Any]:
        """
        Serializar PaymentMethod a dict.
        """
        return {
            'id': method.id,
            'name': method.name,
            'code': method.code if hasattr(method, 'code') else method.name.upper(),
            'active': method.active
        }
    
    @staticmethod
    def _serialize_user(user: User) -> Dict[str, Any]:
        """
        Serializar User a dict (solo datos necesarios).
        """
        return {
            'id': user.id,
            'first_name': user.first_name if hasattr(user, 'first_name') else '',
            'display_name': user.get_display_name() if hasattr(user, 'get_display_name') else str(user.id)
        }
    
    # ==========================================
    # HANDLERS POR ESTADO
    # ==========================================
    
    def _handle_start(self, user: User, message: str = None) -> Dict[str, Any]:
        """
        Handler para /start o estado START
        
        IMPORTANTE: Serializar datos de user AQUÍ
        """
        from app.bot.responses import Responses
        
        # Limpiar conversación anterior
        self.clear_conversation(user)
        
        # Transicionar a MAIN_MENU
        self.set_state(user, ConversationState.MAIN_MENU)
        
        # Serializar user a dict
        user_data = self._serialize_user(user)
        
        return Responses.welcome_message(user_data)
    
    def _handle_main_menu(self, user: User, message: str) -> Dict[str, Any]:
        """Handler para MAIN_MENU"""
        from app.bot.responses import Responses
        
        # Si el mensaje es un callback de botón
        if message.startswith('action:'):
            action = message.split(':', 1)[1]
            
            if action == 'new_operation':
                # Iniciar nueva operación
                self.set_state(user, ConversationState.SELECT_CURRENCY)
                
                # ✅ SOLUCIÓN: Obtener currencies y SERIALIZAR inmediatamente
                currencies = Currency.query.filter_by(active=True).order_by(Currency.id).all()
                
                # Serializar mientras la sesión está activa
                currencies_list = [self._serialize_currency(c) for c in currencies]
                
                return Responses.select_currency_message(currencies_list)
            
            elif action == 'help':
                return Responses.help_message()
        
        # Si no es una acción válida
        return Responses.main_menu_message()
    
    def _handle_select_currency(self, user: User, message: str) -> Dict[str, Any]:
        """Handler para SELECT_CURRENCY"""
        from app.bot.responses import Responses
        
        # Parsear callback data
        callback = self.parser.parse_callback_data(message)
        
        if callback['action'] == 'currency':
            currency_id = int(callback['value'])
            currency = Currency.query.get(currency_id)
            
            if currency and currency.active:
                # ✅ SERIALIZAR currency inmediatamente
                currency_data = self._serialize_currency(currency)
                
                # Guardar en datos de conversación
                data = self.get_data(user)
                data['currency_id'] = currency_data['id']
                data['currency_code'] = currency_data['code']
                data['currency_name'] = currency_data['name']
                self.set_data(user, data)
                
                # Transicionar a selección de método
                self.set_state(user, ConversationState.SELECT_METHOD_FROM)
                
                # ✅ Obtener métodos y SERIALIZAR
                methods = PaymentMethod.query.filter_by(active=True).order_by(PaymentMethod.id).all()
                methods_list = [self._serialize_payment_method(m) for m in methods]
                
                return Responses.select_payment_method_message(
                    currency_code=currency_data['code'],
                    currency_name=currency_data['name'],
                    methods_list=methods_list
                )
        
        # Si no es válido, volver a preguntar
        currencies = Currency.query.filter_by(active=True).order_by(Currency.id).all()
        currencies_list = [self._serialize_currency(c) for c in currencies]
        
        return Responses.select_currency_message(currencies_list)
    
    def _handle_select_method_from(self, user: User, message: str) -> Dict[str, Any]:
        """Handler para SELECT_METHOD_FROM"""
        from app.bot.responses import Responses
        
        callback = self.parser.parse_callback_data(message)
        
        if callback['action'] == 'method':
            method_id = int(callback['value'])
            method = PaymentMethod.query.get(method_id)
            
            if method and method.active:
                # ✅ SERIALIZAR method
                method_data = self._serialize_payment_method(method)
                
                # Guardar método seleccionado
                data = self.get_data(user)
                data['payment_method_from_id'] = method_data['id']
                data['payment_method_from_name'] = method_data['name']
                self.set_data(user, data)
                
                # Transicionar a ingresar monto
                self.set_state(user, ConversationState.ENTER_AMOUNT)
                return Responses.enter_amount_message(method_name=method_data['name'])
        
        # Volver a preguntar
        data = self.get_data(user)
        methods = PaymentMethod.query.filter_by(active=True).order_by(PaymentMethod.id).all()
        methods_list = [self._serialize_payment_method(m) for m in methods]
        
        return Responses.select_payment_method_message(
            currency_code=data.get('currency_code', 'VES'),
            currency_name=data.get('currency_name', 'Bolívares'),
            methods_list=methods_list
        )
    
    def _handle_enter_amount(self, user: User, message: str) -> Dict[str, Any]:
        """Handler para ENTER_AMOUNT"""
        from app.bot.responses import Responses
        
        # Validar monto
        is_valid, amount, error_msg = self.parser.validate_amount(message)
        
        if not is_valid:
            return {
                'text': error_msg,
                'buttons': None
            }
        
        # Obtener datos de conversación
        data = self.get_data(user)
        currency_id = data.get('currency_id')
        method_id = data.get('payment_method_from_id')
        
        # Calcular con CalculatorService
        try:
            calculation = CalculatorService.calculate_exchange(
                amount_usd=amount,
                currency_id=currency_id,
                payment_method_id=method_id
            )
            
            # ✅ CONVERTIR Decimals a float para JSON
            data['amount_usd'] = float(amount)
            data['calculation'] = {
                'fee_usd': float(calculation['fee_usd']),
                'net_usd': float(calculation['net_usd']),
                'exchange_rate': float(calculation['exchange_rate']),
                'amount_local': float(calculation['amount_local']),
                'currency_code': calculation['currency_code']
            }
            self.set_data(user, data)
            
            # Transicionar a confirmación
            self.set_state(user, ConversationState.CONFIRM_CALCULATION)
            
            return Responses.confirm_calculation_message(data)
            
        except Exception as e:
            return {
                'text': f'❌ Error al calcular: {str(e)}\n\nIntenta de nuevo.',
                'buttons': None
            }
    
    def _handle_confirm_calculation(self, user: User, message: str) -> Dict[str, Any]:
        """Handler para CONFIRM_CALCULATION"""
        from app.bot.responses import Responses
        
        callback = self.parser.parse_callback_data(message)
        
        if callback['action'] == 'confirm':
            if callback['value'] == 'yes':
                # Usuario confirmó, pedir datos bancarios
                self.set_state(user, ConversationState.ENTER_BANK)
                return Responses.enter_bank_message()
            
            elif callback['value'] == 'no':
                # Usuario rechazó, volver a ingresar monto
                self.set_state(user, ConversationState.ENTER_AMOUNT)
                data = self.get_data(user)
                method_name = data.get('payment_method_from_name', 'PayPal')
                return Responses.enter_amount_message(method_name=method_name)
        
        # Si no es válido
        data = self.get_data(user)
        return Responses.confirm_calculation_message(data)
    
    def _handle_enter_bank(self, user: User, message: str) -> Dict[str, Any]:
        """Handler para ENTER_BANK"""
        from app.bot.responses import Responses
        
        # Validar nombre del banco
        is_valid, bank_name, error_msg = self.parser.validate_bank_name(message)
        
        if not is_valid:
            return {
                'text': error_msg,
                'buttons': None
            }
        
        # Guardar banco
        data = self.get_data(user)
        data['bank'] = bank_name
        self.set_data(user, data)
        
        # Transicionar a número de cuenta
        self.set_state(user, ConversationState.ENTER_ACCOUNT)
        return Responses.enter_account_message()
    
    def _handle_enter_account(self, user: User, message: str) -> Dict[str, Any]:
        """Handler para ENTER_ACCOUNT"""
        from app.bot.responses import Responses
        
        # Obtener país para validación
        data = self.get_data(user)
        currency_code = data.get('currency_code', 'VES')
        
        # Mapear moneda a país
        country_map = {
            'VES': 'VE',
            'COP': 'CO',
            'CLP': 'CL',
            'ARS': 'AR'
        }
        country = country_map.get(currency_code, 'VE')
        
        # Validar cuenta
        is_valid, account, error_msg = self.parser.validate_account(message, country)
        
        if not is_valid:
            return {
                'text': error_msg,
                'buttons': None
            }
        
        # Guardar cuenta
        data['account'] = account
        self.set_data(user, data)
        
        # Transicionar a titular
        self.set_state(user, ConversationState.ENTER_HOLDER)
        return Responses.enter_holder_message()
    
    def _handle_enter_holder(self, user: User, message: str) -> Dict[str, Any]:
        """Handler para ENTER_HOLDER"""
        from app.bot.responses import Responses
        
        # Validar nombre del titular
        is_valid, holder_name, error_msg = self.parser.validate_holder_name(message)
        
        if not is_valid:
            return {
                'text': error_msg,
                'buttons': None
            }
        
        # Guardar titular
        data = self.get_data(user)
        data['holder'] = holder_name
        self.set_data(user, data)
        
        # Transicionar a DNI
        self.set_state(user, ConversationState.ENTER_DNI)
        return Responses.enter_dni_message(data.get('currency_code', 'VES'))
    
    def _handle_enter_dni(self, user: User, message: str) -> Dict[str, Any]:
        """Handler para ENTER_DNI"""
        from app.bot.responses import Responses
        
        # Obtener país
        data = self.get_data(user)
        currency_code = data.get('currency_code', 'VES')
        country_map = {'VES': 'VE', 'COP': 'CO', 'CLP': 'CL', 'ARS': 'AR'}
        country = country_map.get(currency_code, 'VE')
        
        # Validar DNI
        is_valid, dni, error_msg = self.parser.validate_dni(message, country)
        
        if not is_valid:
            return {
                'text': error_msg,
                'buttons': None
            }
        
        # Guardar DNI
        data['dni'] = dni
        self.set_data(user, data)
        
        # CREAR ORDEN (estado DRAFT)
        try:
            order = self._create_order_draft(user, data)
            
            # ✅ SERIALIZAR order antes de guardar
            data['order_id'] = order.id
            data['order_reference'] = order.reference
            self.set_data(user, data)
            
            # Transicionar a esperar comprobante
            self.set_state(user, ConversationState.AWAIT_PROOF)
            
            return Responses.payment_instructions_message(data)
            
        except Exception as e:
            return {
                'text': f'❌ Error al crear orden: {str(e)}\n\nContacta a soporte.',
                'buttons': None
            }
    
    def _handle_await_proof(self, user: User, message: str) -> Dict[str, Any]:
        """Handler para AWAIT_PROOF (se llama cuando se recibe imagen)"""
        # Este handler se llama desde el photo_handler en bot.py
        # Aquí solo retornamos el mensaje de espera
        return {
            'text': '📸 Envía la captura de pantalla del comprobante de pago.',
            'buttons': None
        }
    
    def handle_proof_received(self, user: User, proof_url: str) -> Dict[str, Any]:
        """
        Procesar comprobante recibido.
        
        IMPORTANTE: Llamar dentro de app.app_context()
        
        Args:
            user: Usuario
            proof_url: URL del comprobante guardado
            
        Returns:
            Dict con respuesta
        """
        from app.bot.responses import Responses
        
        # Obtener datos
        data = self.get_data(user)
        order_id = data.get('order_id')
        
        if not order_id:
            return {
                'text': '❌ Error: No se encontró la orden. Escribe /start para reiniciar.',
                'buttons': None
            }
        
        # Actualizar orden
        try:
            order = Order.query.get(order_id)
            if order:
                # Guardar comprobante
                order.payment_proof_url = proof_url
                
                # Transicionar orden a PENDING
                success, msg = order.transition_to(OrderStatus.PENDING)
                
                if success:
                    order.save()
                    
                    # ✅ SERIALIZAR order.reference AHORA
                    order_reference = order.reference
                    
                    # Notificar operadores
                    from app.services.notification_service import NotificationService
                    NotificationService.notify_new_order(order)
                    
                    # Limpiar conversación
                    self.set_state(user, ConversationState.COMPLETED)
                    self.clear_conversation(user)
                    
                    return Responses.proof_received_success_message(order_reference=order_reference)
                else:
                    return {
                        'text': f'❌ Error: {msg}',
                        'buttons': None
                    }
        except Exception as e:
            return {
                'text': f'❌ Error al procesar: {str(e)}',
                'buttons': None
            }
    
    # ==========================================
    # COMANDOS ESPECIALES
    # ==========================================
    
    def _handle_cancel(self, user: User) -> Dict[str, Any]:
        """Handler para /cancel"""
        self.clear_conversation(user)
        return {
            'text': '❌ Conversación cancelada.\n\nEscribe /start para comenzar de nuevo.',
            'buttons': None
        }
    
    def _handle_help(self, user: User) -> Dict[str, Any]:
        """Handler para /help"""
        from app.bot.responses import Responses
        return Responses.help_message()
    
    def _handle_status(self, user: User) -> Dict[str, Any]:
        """
        Handler para /status - Ver última orden
        
        IMPORTANTE: Serializar datos de order
        """
        # Buscar última orden del usuario
        last_order = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).first()
        
        if not last_order:
            return {
                'text': '📋 No tienes órdenes registradas.\n\nEscribe /start para crear una.',
                'buttons': None
            }
        
        # ✅ SERIALIZAR atributos de order AHORA
        order_reference = last_order.reference
        order_amount = float(last_order.amount_usd)
        order_status = last_order.status
        order_created = last_order.created_at.strftime('%d/%m/%Y %H:%M')
        
        status_text = {
            OrderStatus.DRAFT: 'Borrador',
            OrderStatus.PENDING: 'Verificando pago ⏳',
            OrderStatus.IN_PROCESS: 'En proceso 🔄',
            OrderStatus.COMPLETED: 'Completada ✅',
            OrderStatus.CANCELLED: 'Cancelada ❌'
        }
        
        return {
            'text': f'''📋 **Última orden:** {order_reference}

💰 Monto: ${order_amount:.2f} USD
📊 Estado: {status_text.get(order_status, 'Desconocido')}
📅 Creada: {order_created}

Para nueva operación: /start''',
            'buttons': None
        }
    
    # ==========================================
    # CREACIÓN DE ÓRDENES
    # ==========================================
    
    def _create_order_draft(self, user: User, data: Dict[str, Any]) -> Order:
        """
        Crear orden en estado DRAFT.
        
        Args:
            user: Usuario
            data: Datos de conversación
            
        Returns:
            Order creada
        """
        calc = data['calculation']
        
        # Preparar datos de pago del cliente
        client_payment_data = {
            'bank': data['bank'],
            'account': data['account'],
            'holder': data['holder'],
            'dni': data['dni']
        }
        
        # Crear orden con OrderService
        order = OrderService.create_order(
            user_id=user.id,
            currency_id=data['currency_id'],
            payment_method_from_id=data['payment_method_from_id'],
            payment_method_to_id=data['payment_method_from_id'],  # Por ahora el mismo
            amount_usd=Decimal(str(data['amount_usd'])),
            client_payment_data=client_payment_data,
            channel='telegram',
            channel_chat_id=str(user.telegram_id) if hasattr(user, 'telegram_id') else None
        )
        
        return order
    
    # ==========================================
    # INTERVENCIÓN MANUAL
    # ==========================================
    
    def transfer_to_operator(self, order: Order, operator):
        """
        Transferir conversación a atención manual de operador.
        
        Args:
            order: Orden a transferir
            operator: Operador que toma la conversación
        """
        # Cambiar estado de orden
        order.transition_to(OrderStatus.MANUAL_ATTENTION, operator=operator)
        
        # Marcar en Redis
        self.redis_client.setex(
            f'manual_order:{order.id}',
            7200,  # 2 horas
            operator.id
        )
        
        # Actualizar estado de conversación del usuario
        user = order.user
        self.set_state(user, ConversationState.MANUAL_ATTENTION)
