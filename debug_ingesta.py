from app import create_app
from app.models.payment_source import PaymentSource
from app.services.gmail_service import GmailService
from app.services.parsers.registry import ParserRegistry

app = create_app()
with app.app_context():
    remitentes = [f.remitente for f in PaymentSource.get_activos()]
    correos = GmailService().get_emails_de_remitentes(remitentes, limite=10)
    reg = ParserRegistry()
    for c in correos:
        parser = reg.seleccionar(c)
        nombre = parser.__class__.__name__ if parser else 'NINGUNO'
        estado = ''
        if parser:
            estado = 'OK' if parser.parse(c) else 'FALLO_PARSE'
        print(f"[{nombre:14s} {estado:11s}] {c.get('sender','')[:32]:32s} | {c.get('subject','')[:55]}")