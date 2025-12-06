#!/usr/bin/env python3
"""
Script para iniciar el bot conversacional de Telegram.

Uso:
    python start_bot.py
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Importar y ejecutar bot
from app.telegram.bot_conversational import start_conversational_bot

if __name__ == '__main__':
    print("=" * 50)
    print("🤖 CEIBA21 - BOT CONVERSACIONAL")
    print("=" * 50)
    print("\nIniciando bot...")
    print("Presiona Ctrl+C para detener.\n")
    
    try:
        start_conversational_bot()
    except KeyboardInterrupt:
        print("\n\n👋 Bot detenido por usuario.")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
