"""
Servicio de lectura de Gmail via IMAP.
Lee correos de PayPal no procesados y los marca como leídos.
"""
import imaplib
import email
import logging
from email.header import decode_header
from typing import Optional
from flask import current_app

logger = logging.getLogger(__name__)


class GmailService:
    """
    Servicio para leer correos de Gmail via IMAP.

    Filtra específicamente correos de PayPal con asunto
    'Ha recibido un pago' para evitar otros tipos de correos
    (publicidad, políticas, notificaciones).

    Attributes:
        PAYPAL_SENDER: Remitente oficial de PayPal
        PAYPAL_SUBJECT: Asunto exacto de correos de pago
        IMAP_HOST: Servidor IMAP de Gmail
        IMAP_PORT: Puerto SSL de Gmail
    """

    PAYPAL_SENDER = 'service@intl.paypal.com'
    PAYPAL_SUBJECT = 'Ha recibido un pago'
    IMAP_HOST = 'imap.gmail.com'
    IMAP_PORT = 993

    def __init__(self) -> None:
        """Inicializa con credenciales desde variables de entorno."""
        self.user = current_app.config.get('GMAIL_IMAP_USER')
        self.password = current_app.config.get('GMAIL_IMAP_PASSWORD')
        self._connection: Optional[imaplib.IMAP4_SSL] = None

    def _connect(self) -> bool:
        """
        Establece conexión IMAP con Gmail.

        Returns:
            bool: True si conectó exitosamente
        """
        try:
            self._connection = imaplib.IMAP4_SSL(
                self.IMAP_HOST,
                self.IMAP_PORT
            )
            self._connection.login(self.user, self.password)
            logger.info(f"Gmail IMAP conectado: {self.user}")
            return True
        except imaplib.IMAP4.error as e:
            logger.error(f"Error autenticando Gmail IMAP: {e}")
            return False
        except OSError as e:
            logger.error(f"Error de red conectando a Gmail IMAP: {e}")
            return False

    def _disconnect(self) -> None:
        """Cierra la conexión IMAP de forma segura."""
        if self._connection:
            try:
                self._connection.close()
                self._connection.logout()
            except (imaplib.IMAP4.error, OSError):
                pass
            finally:
                self._connection = None

    def _decode_header_value(self, value: str) -> str:
        """
        Decodifica valores de headers de email (maneja encoding especial).

        Args:
            value: Valor del header a decodificar

        Returns:
            str: Valor decodificado
        """
        decoded_parts = decode_header(value)
        result = ''
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(encoding or 'utf-8', errors='replace')
            else:
                result += str(part)
        return result

    def _get_email_body_html(self, msg: email.message.Message) -> Optional[str]:
        """
        Extrae el cuerpo HTML del mensaje email.

        Args:
            msg: Objeto Message de Python email

        Returns:
            str con el HTML, o None si no hay parte HTML
        """
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        return payload.decode(charset, errors='replace')
        else:
            content_type = msg.get_content_type()
            if content_type == 'text/html':
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    return payload.decode(charset, errors='replace')

        return None

    def _fetch_email_by_uid(self, uid: bytes) -> Optional[dict]:
        """
        Obtiene y parsea un correo individual por su UID IMAP.

        Args:
            uid: UID del mensaje en el servidor IMAP

        Returns:
            dict con los datos del correo, o None si falló el fetch
        """
        status, msg_data = self._connection.fetch(uid, '(RFC822)')

        if status != 'OK':
            return None

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        message_id = msg.get('Message-ID', '').strip()
        subject = self._decode_header_value(msg.get('Subject', ''))
        sender = msg.get('From', '')
        date_str = msg.get('Date', '')
        to_raw = msg.get('To', '')

        html_body = self._get_email_body_html(msg)

        if not html_body:
            logger.warning(f"Correo {message_id} sin cuerpo HTML, omitiendo")
            return None

        return {
            'message_id': message_id,
            'subject': subject,
            'sender': sender,
            'to_raw': to_raw,
            'date': date_str,
            'html_body': html_body,
            'imap_uid': uid.decode() if isinstance(uid, bytes) else uid
        }

    def get_new_paypal_payments(self) -> list[dict]:
        """
        Obtiene correos de pago PayPal no leídos del inbox.

        Filtra por:
        - Remitente: service@intl.paypal.com
        - Asunto: 'Ha recibido un pago'
        - Estado: NO SEEN (no leído)

        Returns:
            Lista de dicts con datos crudos del correo:
            {
                'message_id': str,      # ID único del mensaje Gmail
                'subject': str,         # Asunto del correo
                'sender': str,          # Remitente
                'date': str,            # Fecha del correo
                'html_body': str,       # Cuerpo HTML completo
                'imap_uid': str         # UID para marcar como leído
            }
        """
        if not self._connect():
            return []

        emails = []

        try:
            self._connection.select('INBOX')

            search_criteria = (
                f'(UNSEEN FROM "{self.PAYPAL_SENDER}" '
                f'SUBJECT "{self.PAYPAL_SUBJECT}")'
            )
            status, message_ids = self._connection.search(None, search_criteria)

            if status != 'OK' or not message_ids[0]:
                logger.info("No hay correos nuevos de PayPal")
                return []

            uid_list = message_ids[0].split()
            logger.info(f"Encontrados {len(uid_list)} correos PayPal nuevos")

            for uid in uid_list:
                try:
                    correo = self._fetch_email_by_uid(uid)
                    if correo:
                        emails.append(correo)
                except (UnicodeDecodeError, KeyError, AttributeError) as e:
                    logger.error(f"Error procesando correo UID {uid}: {e}")
                    continue

        except imaplib.IMAP4.error as e:
            logger.error(f"Error IMAP buscando correos: {e}")
        except OSError as e:
            logger.error(f"Error de red en get_new_paypal_payments: {e}")
        finally:
            self._disconnect()

        return emails

    def mark_as_read(self, imap_uid: str) -> bool:
        """
        Marca un correo como leído en Gmail.

        Args:
            imap_uid: UID del mensaje en IMAP

        Returns:
            bool: True si se marcó exitosamente
        """
        if not self._connect():
            return False

        try:
            self._connection.select('INBOX')
            status, _ = self._connection.store(
                imap_uid,
                '+FLAGS',
                '\\Seen'
            )
            return status == 'OK'
        except (imaplib.IMAP4.error, OSError) as e:
            logger.error(f"Error marcando correo {imap_uid} como leído: {e}")
            return False
        finally:
            self._disconnect()

    def test_connection(self) -> dict:
        """
        Prueba la conexión IMAP y retorna el estado.

        Returns:
            dict: {'success': bool, 'message': str, 'inbox_count': int}
        """
        if not self._connect():
            return {
                'success': False,
                'message': 'No se pudo conectar. Verifica usuario y App Password.',
                'inbox_count': 0
            }

        try:
            self._connection.select('INBOX')
            status, data = self._connection.search(None, 'ALL')
            count = len(data[0].split()) if status == 'OK' and data[0] else 0

            return {
                'success': True,
                'message': f'Conexión exitosa a {self.user}',
                'inbox_count': count
            }
        except (imaplib.IMAP4.error, OSError) as e:
            return {
                'success': False,
                'message': f'Error de conexión: {str(e)}',
                'inbox_count': 0
            }
        finally:
            self._disconnect()
            
    def get_emails_de_remitentes(self, remitentes: list, limite: int = 50) -> list:
        """
        Obtiene correos UNSEEN de cualquiera de los remitentes dados.

        NO filtra por asunto (para no perder variantes como los payouts); el
        filtrado fino lo hace cada parser via puede_parsear(). Para no descargar
        un backlog enorme de golpe, procesa solo los `limite` mas recientes.
        """
        if not remitentes or not self._connect():
            return []
        emails = []
        try:
            self._connection.select('INBOX')
            status, message_ids = self._connection.search(
                None, self._build_from_criteria(remitentes)
            )
            if status != 'OK' or not message_ids[0]:
                logger.info("No hay correos nuevos de las fuentes vigiladas")
                return []
            uids = message_ids[0].split()
            total = len(uids)
            # IMAP devuelve los UID en orden ascendente: los mas recientes al final.
            if limite and total > limite:
                uids = uids[-limite:]
                logger.info(f"{total} correos coinciden; proceso los {limite} mas recientes")
            else:
                logger.info(f"Encontrados {total} correos nuevos de fuentes vigiladas")
            for uid in uids:
                try:
                    correo = self._fetch_email_by_uid(uid)
                    if correo:
                        emails.append(correo)
                except (UnicodeDecodeError, KeyError, AttributeError) as e:
                    logger.error(f"Error procesando correo UID {uid}: {e}")
                    continue
        except imaplib.IMAP4.error as e:
            logger.error(f"Error IMAP buscando correos: {e}")
        except OSError as e:
            logger.error(f"Error de red en get_emails_de_remitentes: {e}")
        finally:
            self._disconnect()
        return emails

    @staticmethod
    def _build_from_criteria(remitentes: list) -> str:
        """
        Criterio IMAP UNSEEN + OR de remitentes.

        IMAP OR es binario, por eso se anida: (OR (FROM a) (OR (FROM b) (FROM c))).
        """
        cadena = f'(FROM "{remitentes[0]}")'
        for r in remitentes[1:]:
            cadena = f'(OR {cadena} (FROM "{r}"))'
        return f'(UNSEEN {cadena})'         