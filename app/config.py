"""
Configuración de la aplicación
Lee variables de entorno desde .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

basedir = Path(__file__).resolve().parent.parent
dotenv_path = basedir / '.env'
load_dotenv(dotenv_path=dotenv_path)

print(f"🔍 Cargando .env desde: {dotenv_path}")
if os.getenv('SECRET_KEY'):
    print(f"✅ SECRET_KEY cargado: {os.getenv('SECRET_KEY')[:20]}...")
else:
    print("❌ SECRET_KEY no encontrado")

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'ceiba21admin')
    GMAIL_IMAP_USER = os.getenv('GMAIL_IMAP_USER')
    GMAIL_IMAP_PASSWORD = os.getenv('GMAIL_IMAP_PASSWORD')
    DEFAULT_LOCAL_CURRENCY = os.getenv('DEFAULT_LOCAL_CURRENCY', 'VES')

    # Cookies / consentimiento (banner + categorías)
    COOKIE_CONSENT_NAME = os.getenv('COOKIE_CONSENT_NAME', 'ceiba21_consent')
    COOKIE_CONSENT_VERSION = os.getenv('COOKIE_CONSENT_VERSION', '1')
    COOKIE_CONSENT_MAX_AGE_DAYS = int(os.getenv('COOKIE_CONSENT_MAX_AGE_DAYS', '180'))

    # Tamaño máximo de cualquier petición (16 MB). Corta las subidas gigantes
    # en la puerta, antes de que Werkzeug reciba el cuerpo completo.
    # El límite real del comprobante (5 MB) lo valida ChatService.
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Web Push (VAPID)
    VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY')
    VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY')
    VAPID_CLAIM_EMAIL = os.getenv('VAPID_CLAIM_EMAIL', 'info@ceiba21.com')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}