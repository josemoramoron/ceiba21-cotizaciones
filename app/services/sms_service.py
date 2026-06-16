"""
Servicio de SMS: orquesta el gateway Android, la persistencia y la rotación.

Toda la lógica de negocio del módulo SMS vive aquí (las rutas solo orquestan).
Hereda de BaseService para el manejo centralizado de sesión.

Configuración del gateway leída de variables de entorno (ver .env):
    SMS_GATEWAY_IP, SMS_GATEWAY_PORT, SMS_GATEWAY_USER, SMS_GATEWAY_PASSWORD
"""
import os
from typing import Dict, List, Optional, Tuple

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException, Timeout

from app.models import db
from app.models.sms_message import SmsMessage, SmsDirection, SmsStatus
from app.models.sim_slot import SimSlot
from app.services.base_service import BaseService
from app.services.system_config_service import SystemConfigService


class SmsService(BaseService):
    """Servicio para enviar/recibir SMS y gestionar el board multi-SIM."""

    _TIMEOUT = (5, 30)  # (connect, read) — split como en bot.py

    @staticmethod
    def _gateway_base() -> str:
        """Construye la URL base del gateway desde variables de entorno.

        Returns:
            URL base, p. ej. ``http://192.168.20.16:8080``.
        """
        ip = os.environ.get('SMS_GATEWAY_IP', '192.168.20.16')
        port = os.environ.get('SMS_GATEWAY_PORT', '8080')
        return f'http://{ip}:{port}'

    @staticmethod
    def _gateway_auth() -> HTTPBasicAuth:
        """Credenciales HTTP Basic para el gateway.

        Returns:
            Objeto HTTPBasicAuth con usuario y contraseña del entorno.
        """
        user = os.environ.get('SMS_GATEWAY_USER', 'sms')
        password = os.environ.get('SMS_GATEWAY_PASSWORD', '')
        return HTTPBasicAuth(user, password)

    @classmethod
    def get_gateway_health(cls) -> Tuple[Optional[Dict], Optional[str]]:
        """Consulta el endpoint /health del gateway.

        Returns:
            Tupla (datos, error). Si hay éxito, error es None y datos trae el
            JSON; si falla, datos es None y error trae el mensaje.
        """
        try:
            resp = requests.get(
                f'{cls._gateway_base()}/health',
                auth=cls._gateway_auth(),
                timeout=cls._TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json(), None
        except (RequestException, Timeout, ValueError) as exc:
            return None, str(exc)

    @classmethod
    def send_sms(
        cls,
        phones: List[str],
        text: str,
        sim_slot: Optional[int] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Envía un SMS a uno o varios números vía el gateway.

        Persiste cada destinatario como un SmsMessage saliente.

        Args:
            phones: Lista de números en formato E.164 (+57...).
            text: Contenido del mensaje.
            sim_slot: Slot del board a usar (None = automático del gateway).

        Returns:
            Tupla (datos, error). datos trae la respuesta del gateway si todo
            fue bien; error trae el mensaje si falló la llamada HTTP.
        """
        payload: Dict = {'textMessage': {'text': text}, 'phoneNumbers': phones}
        if sim_slot:
            payload['simNumber'] = sim_slot

        try:
            resp = requests.post(
                f'{cls._gateway_base()}/message',
                json=payload,
                auth=cls._gateway_auth(),
                timeout=cls._TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except (RequestException, Timeout, ValueError) as exc:
            return None, str(exc)

        cls._persist_outbound(data, text, sim_slot)
        return data, None

    @classmethod
    def _persist_outbound(
        cls,
        gateway_data: Dict,
        text: str,
        sim_slot: Optional[int],
    ) -> None:
        """Guarda en BD los mensajes salientes de una respuesta del gateway.

        Args:
            gateway_data: JSON devuelto por el endpoint /message.
            text: Texto enviado.
            sim_slot: Slot usado, si se especificó.
        """
        gw_id = gateway_data.get('id')
        device_id = gateway_data.get('deviceId')
        for recipient in gateway_data.get('recipients', []):
            msg = SmsMessage(
                gateway_id=f"{gw_id}_{recipient['phoneNumber']}",
                direction=SmsDirection.OUTBOUND,
                phone=recipient['phoneNumber'],
                text=text,
                status=recipient.get('state', SmsStatus.PENDING),
                sim_slot=sim_slot,
                device_id=device_id,
            )
            db.session.add(msg)
        cls.commit()

    @classmethod
    def ingest_incoming(cls, body: Dict) -> Optional[SmsMessage]:
        """Registra un SMS entrante recibido por webhook del gateway.

        El gateway envía la estructura anidada::

            {"event": "sms:received", "payload": {"messageId": ...,
             "message": ..., "sender": ..., "simNumber": ...}}

        Se usa ``messageId`` como identificador de deduplicación (es estable
        por contenido) y ``sender`` como remitente. Idempotente.

        Args:
            body: JSON completo del webhook (con la clave anidada ``payload``).

        Returns:
            El SmsMessage creado, o None si era un duplicado.
        """
        data = body.get('payload', body)

        gateway_id = data.get('messageId') or body.get('id')
        if SmsMessage.exists_gateway_id(gateway_id):
            return None

        phone = data.get('sender') or data.get('phoneNumber') or 'desconocido'
        text = data.get('message') or data.get('text') or ''
        sim = data.get('simNumber')

        msg = SmsMessage(
            gateway_id=gateway_id,
            direction=SmsDirection.INBOUND,
            phone=phone,
            text=text,
            sim_slot=sim,
            is_read=False,
        )
        db.session.add(msg)
        cls.commit()
        return msg

    @classmethod
    def update_delivery_status(cls, gateway_id: str, status: str) -> bool:
        """Actualiza el estado de entrega de los salientes de un envío.

        Args:
            gateway_id: ID base del mensaje en el gateway.
            status: Nuevo estado (SmsStatus.*).

        Returns:
            True si se actualizó al menos un registro.
        """
        if not gateway_id or not status:
            return False
        updated = (
            SmsMessage.query
            .filter(SmsMessage.gateway_id.like(f'{gateway_id}%'))
            .update({'status': status}, synchronize_session=False)
        )
        cls.commit()
        return updated > 0

    @classmethod
    def mark_inbound_read(cls) -> None:
        """Marca como leídos todos los SMS entrantes no leídos."""
        (
            SmsMessage.query
            .filter_by(direction=SmsDirection.INBOUND, is_read=False)
            .update({'is_read': True}, synchronize_session=False)
        )
        cls.commit()

    # ── Gestión de slots SIM ────────────────────────────────────────────────

    @staticmethod
    def get_active_slot() -> Optional[int]:
        """Devuelve el número de slot SIM activo guardado en config.

        Returns:
            Número de slot activo, o None si no se ha fijado.
        """
        return SystemConfigService.get_sms_active_slot()

    @classmethod
    def set_active_slot(cls, slot_number: int) -> SimSlot:
        """Fija el slot SIM activo (persiste la preferencia en config).

        Args:
            slot_number: Número de slot del board a activar.

        Returns:
            El SimSlot activado.

        Raises:
            ValueError: Si el slot no existe.
        """
        slot = SimSlot.get_by_slot(slot_number)
        if slot is None:
            raise ValueError(f'El slot {slot_number} no existe')
        SystemConfigService.set_sms_active_slot(slot_number)
        return slot

    @staticmethod
    def ensure_slots(total: int) -> None:
        """Crea los slots faltantes hasta completar el total del board.

        Idempotente: solo inserta los que no existan.

        Args:
            total: Número total de slots del board (p. ej. 20).
        """
        existing = {s.slot_number for s in SimSlot.query.all()}
        for i in range(1, total + 1):
            if i not in existing:
                db.session.add(
                    SimSlot(slot_number=i, label=f'SIM {i}', active=False)
                )
        SmsService.commit()
