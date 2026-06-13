"""
Diagnóstico de títulos de correos PayPal.

Lista todos los correos de un remitente (PayPal por defecto) desde una fecha,
y muestra cuáles reconoce el parser de título y cuáles no. Para los que fallan,
vuelca los elementos con font-size y los textos que contienen montos, para poder
ver dónde quedó el título/monto en ese layout y decidir si ampliar el parser.

Es solo lectura: NO marca correos como leídos ni modifica nada.

Uso (Windows / PowerShell):
    python scripts\\diagnostico_titulos_paypal.py
    python scripts\\diagnostico_titulos_paypal.py 01-Jun-2026
    python scripts\\diagnostico_titulos_paypal.py 01-Jun-2026 service@intl.paypal.com
"""
import os
import re
import sys
from typing import Optional

# Permitir importar el paquete `app` al correr el script desde la raíz del repo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bs4 import BeautifulSoup

from app import create_app
from app.services.gmail_service import GmailService
from app.services.parsers.paypal_parser import _TITULO_RE

_MONTO_RE = re.compile(r'\$|\bUSD\b|€|\bEUR\b')


def _titulo_42px(soup: BeautifulSoup) -> Optional[str]:
    """Devuelve el texto del <p> con font-size:42px (el título que busca el parser)."""
    el = soup.find('p', style=lambda s: s and 'font-size:42px' in s)
    return el.get_text(separator=' ', strip=True) if el else None


def _volcar_estructura(soup: BeautifulSoup) -> None:
    """Imprime elementos con font-size y textos con monto, para los correos que fallan."""
    print("        --- elementos con font-size ---")
    vistos = set()
    for el in soup.find_all(style=lambda s: s and 'font-size' in s):
        texto = el.get_text(separator=' ', strip=True)
        if not texto or texto in vistos or len(texto) > 130:
            continue
        vistos.add(texto)
        fs = next(
            (x.strip() for x in el.get('style', '').split(';') if 'font-size' in x),
            ''
        )
        print(f"          <{el.name}> [{fs}] {texto}")

    print("        --- textos con monto ($, USD, EUR) ---")
    vistos.clear()
    for nodo in soup.find_all(string=_MONTO_RE):
        texto = nodo.strip()
        if texto and texto not in vistos and len(texto) < 100:
            vistos.add(texto)
            print(f"          {texto}")


def main(desde_imap: str, remitente: str) -> None:
    """Conecta a Gmail, recorre los correos del remitente y reporta el estado del parseo."""
    app = create_app()
    with app.app_context():
        gmail = GmailService()
        correos = gmail.get_emails_desde_fecha([remitente], desde_imap)

        print(f"\n{len(correos)} correos de {remitente} desde {desde_imap}")
        print("=" * 72)

        ok = falla = 0
        for correo in correos:
            html = correo.get('html_body')
            if not html:
                continue
            soup = BeautifulSoup(html, 'html.parser')
            titulo = _titulo_42px(soup)
            reconocido = bool(titulo and _TITULO_RE.match(titulo))

            if reconocido:
                ok += 1
                continue

            falla += 1
            print(f"\n✗ NO RECONOCIDO | {(correo.get('subject') or '')[:62]}")
            print(f"        msg_id:      {correo.get('message_id')}")
            print(f"        titulo 42px: {titulo!r}")
            _volcar_estructura(soup)

        print("\n" + "=" * 72)
        print(f"Resumen: {ok} reconocidos, {falla} no reconocidos, {len(correos)} total")


if __name__ == '__main__':
    fecha = sys.argv[1] if len(sys.argv) > 1 else '01-Jun-2026'
    sender = sys.argv[2] if len(sys.argv) > 2 else 'service@intl.paypal.com'
    main(fecha, sender)