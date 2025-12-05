#!/usr/bin/env python3
"""
Script para probar la integración de Redis.
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, cache
from app.services import CacheService
from redis import Redis

def test_redis():
    """Probar conexión y operaciones básicas con Redis"""
    print("🔍 Probando Redis...")
    print("=" * 50)
    
    # Crear la app primero para inicializar redis_client
    app = create_app()
    
    # Obtener redis_client del módulo app
    import app as app_module
    redis_client = app_module.redis_client
    
    # Test 1: Conexión básica
    print("\n1️⃣ Test de conexión básica:")
    try:
        response = redis_client.ping()
        if response:
            print("   ✅ Redis conectado exitosamente!")
        else:
            print("   ❌ Redis no respondió")
            return False
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False
    
    # Test 2: Operaciones SET/GET
    print("\n2️⃣ Test de SET/GET:")
    try:
        redis_client.set('test_key', 'Hello Redis!')
        value = redis_client.get('test_key')
        if value == 'Hello Redis!':
            print(f"   ✅ SET/GET funcionando: '{value}'")
        else:
            print(f"   ❌ Valor incorrecto: {value}")
            return False
    except Exception as e:
        print(f"   ❌ Error en SET/GET: {e}")
        return False
    
    # Test 3: Expiración (TTL)
    print("\n3️⃣ Test de expiración (TTL):")
    try:
        redis_client.setex('temp_key', 5, 'Expira en 5 segundos')
        ttl = redis_client.ttl('temp_key')
        print(f"   ✅ TTL configurado: {ttl} segundos restantes")
    except Exception as e:
        print(f"   ❌ Error en TTL: {e}")
        return False
    
    # Test 4: CacheService
    print("\n4️⃣ Test de CacheService:")
    try:
        success = CacheService.set('cache_test', 'Cache funcionando', ttl=60)
        if success:
            value = CacheService.get('cache_test')
            if value == 'Cache funcionando':
                print(f"   ✅ CacheService funcionando: '{value}'")
            else:
                print(f"   ⚠️  Valor recuperado diferente: {value}")
        else:
            print("   ❌ Error al guardar en CacheService")
            return False
    except Exception as e:
        print(f"   ❌ Error en CacheService: {e}")
        return False
    
    # Test 5: Flask-Caching
    print("\n5️⃣ Test de Flask-Caching:")
    try:
        app = create_app()
        with app.app_context():
            cache.set('flask_cache_test', 'Flask cache OK', timeout=60)
            value = cache.get('flask_cache_test')
            if value == 'Flask cache OK':
                print(f"   ✅ Flask-Caching funcionando: '{value}'")
            else:
                print(f"   ⚠️  Flask-Caching retornó: {value}")
    except Exception as e:
        print(f"   ❌ Error en Flask-Caching: {e}")
        return False
    
    # Test 6: Limpieza
    print("\n6️⃣ Limpieza de tests:")
    try:
        redis_client.delete('test_key', 'temp_key', 'cache_test', 'flask_cache_test')
        print("   ✅ Keys de test eliminadas")
    except Exception as e:
        print(f"   ⚠️  Error en limpieza: {e}")
    
    # Info de Redis
    print("\n📊 Información de Redis:")
    try:
        info = redis_client.info('memory')
        used_memory = info.get('used_memory_human', 'N/A')
        print(f"   Memoria usada: {used_memory}")
        
        info_server = redis_client.info('server')
        redis_version = info_server.get('redis_version', 'N/A')
        print(f"   Versión Redis: {redis_version}")
    except Exception as e:
        print(f"   ⚠️  No se pudo obtener info: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Todos los tests de Redis pasaron exitosamente!")
    print("=" * 50)
    
    return True

if __name__ == '__main__':
    success = test_redis()
    sys.exit(0 if success else 1)
