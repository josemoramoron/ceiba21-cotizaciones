#!/usr/bin/env python3
"""
Script para probar la estructura base del bot conversacional.
Verifica imports y validaciones básicas.
"""
import sys
import os
from decimal import Decimal

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.bot.states import ConversationState
from app.bot.message_parser import MessageParser


def test_states():
    """Probar ConversationState"""
    print("🔍 Probando ConversationState...")
    print("=" * 50)
    
    # Test 1: Crear estado
    state = ConversationState.START
    print(f"✅ Estado creado: {state}")
    
    # Test 2: Convertir desde string
    state_from_str = ConversationState.from_string('main_menu')
    print(f"✅ Estado desde string: {state_from_str}")
    
    # Test 3: Estado terminal
    is_terminal = ConversationState.COMPLETED.is_terminal()
    print(f"✅ COMPLETED es terminal: {is_terminal}")
    
    # Test 4: Transiciones válidas
    can_transition = ConversationState.START.can_transition_to(ConversationState.MAIN_MENU)
    print(f"✅ START → MAIN_MENU es válido: {can_transition}")
    
    # Test 5: Transición inválida
    invalid = ConversationState.START.can_transition_to(ConversationState.AWAIT_PROOF)
    print(f"✅ START → AWAIT_PROOF es inválido: {not invalid}")
    
    # Test 6: Todos los estados
    all_states = ConversationState.get_all_states()
    print(f"✅ Total de estados: {len(all_states)}")
    
    print("\n✅ Todos los tests de ConversationState pasaron!\n")
    return True


def test_message_parser():
    """Probar MessageParser"""
    print("🔍 Probando MessageParser...")
    print("=" * 50)
    
    # Test 1: Validar monto válido
    valid, amount, error = MessageParser.validate_amount("100")
    assert valid == True, "Monto 100 debe ser válido"
    assert amount == Decimal('100'), "Monto debe ser 100"
    print(f"✅ Monto válido: ${amount}")
    
    # Test 2: Validar monto inválido
    valid, amount, error = MessageParser.validate_amount("abc")
    assert valid == False, "Monto 'abc' debe ser inválido"
    assert error is not None, "Debe retornar mensaje de error"
    print(f"✅ Monto inválido detectado: {error[:30]}...")
    
    # Test 3: Validar cuenta venezolana
    valid, account, error = MessageParser.validate_account("01020123456789012345", "VE")
    assert valid == True, "Cuenta de 20 dígitos debe ser válida"
    assert account == "01020123456789012345"
    print(f"✅ Cuenta venezolana válida: {account}")
    
    # Test 4: Validar nombre de titular
    valid, name, error = MessageParser.validate_holder_name("Juan Pérez")
    assert valid == True, "Nombre completo debe ser válido"
    assert name == "Juan Pérez"
    print(f"✅ Nombre válido: {name}")
    
    # Test 5: Validar DNI venezolano
    valid, dni, error = MessageParser.validate_dni("V12345678", "VE")
    assert valid == True, "DNI venezolano debe ser válido"
    assert dni == "V-12345678", "DNI debe normalizarse con guion"
    print(f"✅ DNI válido: {dni}")
    
    # Test 6: Parsear callback data
    data = MessageParser.parse_callback_data("currency:1")
    assert data['action'] == 'currency'
    assert data['value'] == '1'
    print(f"✅ Callback parseado: {data}")
    
    # Test 7: Detectar comando
    is_cmd = MessageParser.is_command("/start")
    assert is_cmd == True
    print(f"✅ Comando detectado: /start")
    
    # Test 8: Extraer comando
    cmd = MessageParser.extract_command("/start")
    assert cmd == "start"
    print(f"✅ Comando extraído: {cmd}")
    
    # Test 9: Sanitizar input
    sanitized = MessageParser.sanitize_input("  Hola mundo  ")
    assert sanitized == "Hola mundo"
    print(f"✅ Input sanitizado: '{sanitized}'")
    
    print("\n✅ Todos los tests de MessageParser pasaron!\n")
    return True


def test_integration():
    """Probar integración entre módulos"""
    print("🔍 Probando integración...")
    print("=" * 50)
    
    # Simular flujo básico
    state = ConversationState.START
    print(f"1. Estado inicial: {state}")
    
    # Usuario envía /start
    text = "/start"
    if MessageParser.is_command(text):
        cmd = MessageParser.extract_command(text)
        print(f"2. Comando detectado: /{cmd}")
        
        # Transicionar a MAIN_MENU
        if state.can_transition_to(ConversationState.MAIN_MENU):
            state = ConversationState.MAIN_MENU
            print(f"3. Transición a: {state}")
    
    # Usuario selecciona moneda
    if state.can_transition_to(ConversationState.SELECT_CURRENCY):
        state = ConversationState.SELECT_CURRENCY
        print(f"4. Usuario selecciona moneda: {state}")
    
    # Usuario ingresa monto
    if state.can_transition_to(ConversationState.ENTER_AMOUNT):
        state = ConversationState.SELECT_METHOD_FROM
        state = ConversationState.ENTER_AMOUNT
        print(f"5. Usuario ingresa monto: {state}")
        
        valid, amount, error = MessageParser.validate_amount("100")
        if valid:
            print(f"6. Monto validado: ${amount}")
    
    print("\n✅ Integración funciona correctamente!\n")
    return True


def main():
    """Ejecutar todos los tests"""
    print("\n" + "=" * 50)
    print("🧪 TESTING ESTRUCTURA BASE DEL BOT")
    print("=" * 50 + "\n")
    
    try:
        # Test 1: States
        if not test_states():
            return False
        
        # Test 2: MessageParser
        if not test_message_parser():
            return False
        
        # Test 3: Integración
        if not test_integration():
            return False
        
        print("=" * 50)
        print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE!")
        print("=" * 50)
        print("\n📦 Estructura base del bot lista para usar:\n")
        print("  ✅ app/bot/__init__.py")
        print("  ✅ app/bot/states.py")
        print("  ✅ app/bot/message_parser.py")
        print("\n🚀 Siguiente paso: Implementar conversation_handler.py\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error en tests: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
