#!/usr/bin/env python3
"""
Script de diagnóstico completo del sistema Ceiba21.
Verifica todos los componentes críticos.
"""
import sys
import os

# Agregar directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def check_imports():
    """Verificar que todos los imports críticos funcionan"""
    print("📦 Verificando imports...")
    try:
        from app import create_app
        from app.models import db
        from app.models.operator import Operator
        from app.models.order import Order
        from app.models.transaction import Transaction
        from app.services.accounting_service import AccountingService
        print("   ✅ Imports OK\n")
        return True
    except Exception as e:
        print(f"   ❌ Error en imports: {e}\n")
        return False


def check_database():
    """Verificar conexión a PostgreSQL"""
    print("🗄️  Verificando PostgreSQL...")
    try:
        from app import create_app
        from app.models import db
        from sqlalchemy import inspect
        
        app = create_app()
        with app.app_context():
            # Intentar query simple
            db.session.execute(db.text('SELECT 1'))
            
            # Listar tablas
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"   ✅ PostgreSQL conectado")
            print(f"   ✅ {len(tables)} tablas encontradas\n")
            return True
    except Exception as e:
        print(f"   ❌ Error en PostgreSQL: {e}\n")
        return False


def check_redis():
    """Verificar conexión a Redis"""
    print("🔴 Verificando Redis...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        
        # Info básica
        info = r.info()
        print(f"   ✅ Redis conectado")
        print(f"   ✅ Versión: {info.get('redis_version', 'unknown')}\n")
        return True
    except Exception as e:
        print(f"   ❌ Error en Redis: {e}\n")
        return False


def check_operators():
    """Verificar que existan operadores"""
    print("👥 Verificando operadores...")
    try:
        from app import create_app
        from app.models.operator import Operator
        
        app = create_app()
        with app.app_context():
            total = Operator.query.count()
            admin_exists = Operator.get_by_username('admin') is not None
            
            print(f"   ✅ {total} operadores en BD")
            print(f"   {'✅' if admin_exists else '❌'} Admin {'existe' if admin_exists else 'NO existe'}\n")
            
            if not admin_exists:
                print("   ⚠️  Ejecuta: python scripts/seed_operators.py\n")
            
            return total > 0
    except Exception as e:
        print(f"   ❌ Error verificando operadores: {e}\n")
        return False


def check_environment():
    """Verificar variables de entorno"""
    print("🔐 Verificando variables de entorno...")
    required_vars = ['SECRET_KEY', 'DATABASE_URL']
    missing = []
    
    from dotenv import load_dotenv
    load_dotenv()
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"   ❌ Faltan variables: {', '.join(missing)}\n")
        return False
    else:
        print(f"   ✅ Variables de entorno OK\n")
        return True


def check_bot_status():
    """Verificar si el bot está corriendo"""
    print("🤖 Verificando bot de Telegram...")
    try:
        import psutil
        
        bot_running = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if any('app.telegram.bot' in str(cmd) for cmd in cmdline):
                    bot_running = True
                    print(f"   ✅ Bot corriendo (PID: {proc.info['pid']})\n")
                    break
            except:
                continue
        
        if not bot_running:
            print("   ⚠️  Bot NO está corriendo\n")
        
        return bot_running
    except Exception as e:
        print(f"   ❌ Error verificando bot: {e}\n")
        return False


def main():
    """Ejecutar todos los checks"""
    print("\n" + "="*60)
    print("🏥 HEALTH CHECK - CEIBA21")
    print("="*60 + "\n")
    
    checks = {
        'Imports': check_imports(),
        'PostgreSQL': check_database(),
        'Redis': check_redis(),
        'Environment': check_environment(),
        'Operators': check_operators(),
        'Bot': check_bot_status()
    }
    
    # Resumen
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    
    print("="*60)
    print(f"RESULTADO: {passed}/{total} checks pasaron")
    print("="*60)
    
    for name, status in checks.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {name}")
    
    print()
    
    if passed == total:
        print("✅ SISTEMA SALUDABLE - Todo funcionando correctamente\n")
        return True
    else:
        print("⚠️  SISTEMA CON PROBLEMAS - Revisar errores arriba\n")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
