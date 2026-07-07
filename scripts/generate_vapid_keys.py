"""
Genera un par de claves VAPID para Web Push (ejecutar UNA sola vez).

Imprime las variables para pegar en .env (dev y prod):
- VAPID_PRIVATE_KEY: clave privada raw en base64url (una sola línea).
- VAPID_PUBLIC_KEY: applicationServerKey (base64url del punto público sin
  comprimir) que el navegador usa al suscribirse.
- VAPID_CLAIM_EMAIL: email de contacto del emisor (requerido por el protocolo).

Uso:
    python scripts/generate_vapid_keys.py
"""
import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid01


def _b64url(data: bytes) -> str:
    """Codificar en base64url sin padding."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def main() -> int:
    """Generar e imprimir el par de claves VAPID."""
    vapid = Vapid01()
    vapid.generate_keys()

    private_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, 'big')
    public_point = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )

    print("# --- Pega esto en tu .env (dev y prod) ---")
    print(f"VAPID_PRIVATE_KEY={_b64url(private_raw)}")
    print(f"VAPID_PUBLIC_KEY={_b64url(public_point)}")
    print("VAPID_CLAIM_EMAIL=info@ceiba21.com")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
