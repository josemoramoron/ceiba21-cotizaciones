"""
Estados de la conversación del bot (FSM).
Define todos los estados posibles en el flujo de creación de órdenes.
"""
from enum import Enum


class ConversationState(Enum):
    """
    Estados de la máquina de estados finita (FSM) para conversaciones del bot.
    
    Flujo principal:
    START → MAIN_MENU → SELECT_CURRENCY → SELECT_METHOD_FROM → 
    ENTER_AMOUNT → CONFIRM_CALCULATION → ENTER_BANK → ENTER_ACCOUNT → 
    ENTER_HOLDER → ENTER_DNI → AWAIT_PROOF → COMPLETED
    
    Estados especiales:
    - MANUAL_ATTENTION: Operador intervino manualmente
    - CANCELLED: Usuario canceló la conversación
    """
    
    # Estados iniciales
    START = 'start'
    MAIN_MENU = 'main_menu'
    
    # Estados de selección
    SELECT_CURRENCY = 'select_currency'
    SELECT_METHOD_FROM = 'select_method_from'
    SELECT_METHOD_TO = 'select_method_to'  # Opcional: solo si se implementa en futuro
    
    # Estados de ingreso de datos de transacción
    ENTER_AMOUNT = 'enter_amount'
    CONFIRM_CALCULATION = 'confirm_calculation'
    
    # Estados de ingreso de datos bancarios
    ENTER_BANK = 'enter_bank'
    ENTER_ACCOUNT = 'enter_account'
    ENTER_HOLDER = 'enter_holder'
    ENTER_DNI = 'enter_dni'
    
    # Estados finales
    AWAIT_PROOF = 'await_proof'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    
    # Estados especiales
    MANUAL_ATTENTION = 'manual_attention'  # Operador tomó control
    
    def __str__(self):
        """Representación en string del estado"""
        return self.value
    
    @classmethod
    def from_string(cls, state_str: str):
        """
        Crear ConversationState desde string.
        
        Args:
            state_str: String del estado
            
        Returns:
            ConversationState o None si no existe
        """
        try:
            return cls(state_str)
        except ValueError:
            return None
    
    @classmethod
    def get_all_states(cls):
        """Obtener lista de todos los estados disponibles"""
        return [state for state in cls]
    
    def is_terminal(self) -> bool:
        """
        Verificar si es un estado terminal (no hay siguiente estado).
        
        Returns:
            bool: True si es estado terminal
        """
        return self in [
            ConversationState.COMPLETED,
            ConversationState.CANCELLED,
            ConversationState.MANUAL_ATTENTION
        ]
    
    def can_transition_to(self, next_state) -> bool:
        """
        Verificar si es válida la transición al siguiente estado.
        
        Args:
            next_state: Estado destino
            
        Returns:
            bool: True si la transición es válida
        """
        # Desde estados terminales no se puede transicionar
        if self.is_terminal():
            return next_state == ConversationState.START
        
        # Definir transiciones válidas
        valid_transitions = {
            ConversationState.START: [ConversationState.MAIN_MENU],
            ConversationState.MAIN_MENU: [
                ConversationState.SELECT_CURRENCY,
                ConversationState.CANCELLED
            ],
            ConversationState.SELECT_CURRENCY: [
                ConversationState.SELECT_METHOD_FROM,
                ConversationState.MAIN_MENU,
                ConversationState.CANCELLED
            ],
            ConversationState.SELECT_METHOD_FROM: [
                ConversationState.ENTER_AMOUNT,
                ConversationState.SELECT_CURRENCY,
                ConversationState.CANCELLED
            ],
            ConversationState.ENTER_AMOUNT: [
                ConversationState.CONFIRM_CALCULATION,
                ConversationState.SELECT_METHOD_FROM,
                ConversationState.CANCELLED
            ],
            ConversationState.CONFIRM_CALCULATION: [
                ConversationState.ENTER_BANK,  # Si confirma
                ConversationState.ENTER_AMOUNT,  # Si rechaza, volver a ingresar monto
                ConversationState.CANCELLED
            ],
            ConversationState.ENTER_BANK: [
                ConversationState.ENTER_ACCOUNT,
                ConversationState.CANCELLED
            ],
            ConversationState.ENTER_ACCOUNT: [
                ConversationState.ENTER_HOLDER,
                ConversationState.ENTER_BANK,
                ConversationState.CANCELLED
            ],
            ConversationState.ENTER_HOLDER: [
                ConversationState.ENTER_DNI,
                ConversationState.ENTER_ACCOUNT,
                ConversationState.CANCELLED
            ],
            ConversationState.ENTER_DNI: [
                ConversationState.AWAIT_PROOF,
                ConversationState.ENTER_HOLDER,
                ConversationState.CANCELLED
            ],
            ConversationState.AWAIT_PROOF: [
                ConversationState.COMPLETED,
                ConversationState.MANUAL_ATTENTION,
                ConversationState.CANCELLED
            ],
        }
        
        # Desde cualquier estado se puede ir a MANUAL_ATTENTION
        if next_state == ConversationState.MANUAL_ATTENTION:
            return True
        
        # Desde cualquier estado se puede volver a START
        if next_state == ConversationState.START:
            return True
        
        allowed = valid_transitions.get(self, [])
        return next_state in allowed
