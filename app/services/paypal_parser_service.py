"""
Servicio de parseo de correos HTML de PayPal.
Extrae datos estructurados del HTML de los correos de pago.
"""
import re
import logging
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Mapeo de meses en español a número
MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
    'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

# Símbolos de moneda a código ISO
SIMBOLO_A_CODIGO = {
    '$': 'USD',
    '€': 'EUR',
    '£': 'GBP',
    'R$': 'BRL',
    'MX$': 'MXN',
    'COP$': 'COP',
    'S/': 'PEN',
    'CLP$': 'CLP',
    'ARS$': 'ARS',
}


class PaypalParserService:
    """
    Parser de correos HTML de PayPal.

    Maneja dos tipos de correo:
    - Tipo A (personal/F&F): Sin comisión, sin dirección obligatoria
    - Tipo B (comercial/G&S): Con comisión, con o sin dirección

    Ambos tipos pueden tener o no dirección de envío.
    """

    @staticmethod
    def _limpiar_monto(texto: str) -> tuple[Optional[float], Optional[str]]:
        """
        Extrae el monto y moneda de un texto como '$\xa020,00\xa0USD'.

        Los correos usan \xa0 (non-breaking space) como separador.

        Args:
            texto: Texto con monto y moneda del correo PayPal

        Returns:
            tuple: (monto_float, codigo_moneda) o (None, None) si falla

        Example:
            >>> _limpiar_monto('$\xa020,00\xa0USD')
            (20.0, 'USD')
            >>> _limpiar_monto('€\xa070,00\xa0EUR')
            (70.0, 'EUR')
        """
        if not texto:
            return None, None

        # Limpiar non-breaking spaces y espacios extra
        texto = texto.replace('\xa0', ' ').replace('\u00a0', ' ').strip()

        # Extraer código de moneda ISO al final (3 letras mayúsculas)
        moneda_match = re.search(r'\b([A-Z]{3})\b', texto)
        moneda_codigo = moneda_match.group(1) if moneda_match else None

        # Si no encontró ISO, intentar por símbolo
        if not moneda_codigo:
            for simbolo, codigo in SIMBOLO_A_CODIGO.items():
                if simbolo in texto:
                    moneda_codigo = codigo
                    break

        # Extraer número: formato europeo usa coma como decimal
        # Ejemplos: "20,00", "9,96", "70,00"
        numero_match = re.search(r'[\d.,]+', texto)
        if not numero_match:
            return None, moneda_codigo

        numero_str = numero_match.group(0)

        try:
            # Formato europeo: punto=miles, coma=decimal
            if ',' in numero_str and '.' in numero_str:
                # Ej: "1.234,56" → 1234.56
                numero_str = numero_str.replace('.', '').replace(',', '.')
            elif ',' in numero_str:
                # Ej: "20,00" → 20.00
                numero_str = numero_str.replace(',', '.')

            return float(numero_str), moneda_codigo
        except ValueError:
            logger.warning(f"No se pudo convertir monto: {numero_str}")
            return None, moneda_codigo

    @staticmethod
    def _parsear_fecha(texto: str) -> Optional[datetime]:
        """
        Parsea la fecha en formato español del correo PayPal.
        Formato: "2 de junio de 2026"

        Args:
            texto: Fecha en texto español

        Returns:
            datetime o None si no se pudo parsear
        """
        if not texto:
            return None

        texto = texto.strip().lower()

        # Patrón: "2 de junio de 2026"
        patron = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})'
        match = re.search(patron, texto)

        if match:
            dia = int(match.group(1))
            mes_texto = match.group(2)
            anio = int(match.group(3))
            mes = MESES_ES.get(mes_texto)

            if mes:
                try:
                    return datetime(anio, mes, dia)
                except ValueError:
                    pass

        logger.warning(f"No se pudo parsear fecha: {texto}")
        return None

    @staticmethod
    def _detectar_tipo_pago(
        comision: Optional[float],
        total: Optional[float]
    ) -> str:
        """
        Detecta si es pago personal (F&F) o comercial (G&S).

        La diferencia clave: comercial tiene fila de Comisión en el HTML.

        Args:
            comision: Monto de comisión extraído (None si no apareció)
            total: Monto total/neto extraído (None si no apareció)

        Returns:
            str: 'comercial' o 'personal'
        """
        from app.models.paypal_payment import PaypalPaymentType
        if comision is not None and comision > 0:
            return PaypalPaymentType.COMERCIAL
        return PaypalPaymentType.PERSONAL

    def parse_email(self, html_body: str, message_id: str) -> Optional[dict]:
        """
        Parsea el HTML de un correo PayPal y extrae los datos del pago.

        Args:
            html_body: Contenido HTML del correo
            message_id: ID del mensaje Gmail (para referencia)

        Returns:
            dict con los datos del pago, o None si no se pudo parsear:
            {
                'pagador_nombre': str,
                'importe_bruto': float,
                'moneda': str,
                'comision_paypal': float|None,
                'importe_neto': float|None,
                'tipo_pago': str,
                'paypal_transaction_id': str|None,
                'fecha_pago': datetime|None,
                'direccion_envio': str|None,
                'cuenta_destino': str|None
            }
        """
        if not html_body:
            logger.error(f"HTML vacío para mensaje {message_id}")
            return None

        try:
            soup = BeautifulSoup(html_body, 'html.parser')
            resultado = {}

            # ── 1. Pagador y monto desde el título principal ──────────
            # Texto: "Paul Milton III le ha enviado $\xa020,00\xa0USD"
            titulo = soup.find('p', style=lambda s: s and 'font-size:42px' in s)
            if titulo:
                texto_titulo = titulo.get_text(separator=' ', strip=True)
                # Extraer nombre del pagador (todo antes de "le ha enviado")
                match_titulo = re.match(
                    r'^(.+?)\s+le ha enviado\s+(.+)$',
                    texto_titulo,
                    re.IGNORECASE
                )
                if match_titulo:
                    resultado['pagador_nombre'] = match_titulo.group(1).strip()
                    monto_texto = match_titulo.group(2).strip()
                    monto, moneda = PaypalParserService._limpiar_monto(
                        monto_texto
                    )
                    resultado['importe_bruto'] = monto
                    resultado['moneda'] = moneda or 'USD'
                else:
                    logger.warning(
                        f"No se pudo parsear título: {texto_titulo}"
                    )

            # Fallback: preHeader tiene "Nombre, recibió $20,00 USD"
            if not resultado.get('pagador_nombre'):
                preheader = soup.find(id='preHeader')
                if preheader:
                    texto_pre = preheader.get_text(strip=True)
                    match_pre = re.match(
                        r'^(.+?),\s+recibió\s+(.+)$',
                        texto_pre,
                        re.IGNORECASE
                    )
                    if match_pre and not resultado.get('importe_bruto'):
                        monto_texto = match_pre.group(2).strip()
                        monto, moneda = PaypalParserService._limpiar_monto(
                            monto_texto
                        )
                        resultado['importe_bruto'] = monto
                        resultado['moneda'] = moneda or 'USD'

            # ── 2. Tabla de detalles (cartDetails) ───────────────────
            # Busca filas: Importe recibido, Comisión, Total
            comision = None
            total_neto = None
            fecha_pago = None
            transaction_id = None

            tablas_cart = soup.find_all('table', id='cartDetails')

            for tabla in tablas_cart:
                filas = tabla.find_all('tr')
                for fila in filas:
                    celdas = fila.find_all('td')
                    if len(celdas) >= 2:
                        etiqueta = celdas[0].get_text(strip=True).lower()
                        valor_texto = celdas[1].get_text(strip=True)

                        if 'importe recibido' in etiqueta:
                            monto, _ = PaypalParserService._limpiar_monto(
                                valor_texto
                            )
                            if monto:
                                resultado['importe_bruto'] = monto

                        elif 'comisión' in etiqueta or 'comision' in etiqueta:
                            monto, _ = PaypalParserService._limpiar_monto(
                                valor_texto
                            )
                            comision = monto

                        elif 'total' in etiqueta:
                            monto, _ = PaypalParserService._limpiar_monto(
                                valor_texto
                            )
                            total_neto = monto

                        elif 'id. de transacci' in etiqueta or 'transaction' in etiqueta.lower():
                            # El ID está en un enlace dentro de la celda
                            enlace = celdas[0].find('a')
                            if enlace:
                                transaction_id = enlace.get_text(strip=True)

                        elif 'fecha de la transacci' in etiqueta:
                            fecha_pago = PaypalParserService._parsear_fecha(
                                valor_texto
                            )

            resultado['comision_paypal'] = comision
            resultado['importe_neto'] = total_neto
            resultado['paypal_transaction_id'] = transaction_id
            resultado['fecha_pago'] = fecha_pago

            # ── 3. Tipo de pago ───────────────────────────────────────
            resultado['tipo_pago'] = PaypalParserService._detectar_tipo_pago(
                comision,
                total_neto
            )

            # ── 4. Dirección de envío (opcional en ambos tipos) ───────
            direccion = None
            seccion_dir = soup.find(
                'p',
                string=lambda s: s and 'Dirección de envío' in s
                if s else False
            )

            # Buscar por texto del encabezado de sección
            for p in soup.find_all('p'):
                texto_p = p.get_text(strip=True)
                if 'Dirección de envío' in texto_p:
                    # La dirección está en el siguiente párrafo
                    padre = p.find_parent('td')
                    if padre:
                        siguiente_td = padre.find_parent('tr')
                        if siguiente_td:
                            siguiente_fila = siguiente_td.find_next_sibling('tr')
                            if siguiente_fila:
                                dir_p = siguiente_fila.find('p')
                                if dir_p:
                                    direccion = dir_p.get_text(
                                        separator=', ',
                                        strip=True
                                    )
                    break

            resultado['direccion_envio'] = direccion

            # ── 5. Cuenta destino (del header X-Forwarded-To) ─────────
            # No está en el HTML, se pasa desde el correo raw
            resultado['cuenta_destino'] = None  # Se rellena en PaymentIngestionService

            # ── Validación mínima ─────────────────────────────────────
            if not resultado.get('importe_bruto'):
                logger.error(
                    f"No se pudo extraer importe del correo {message_id}"
                )
                return None

            if not resultado.get('moneda'):
                resultado['moneda'] = 'USD'

            logger.info(
                f"Correo parseado: {resultado.get('pagador_nombre')} | "
                f"{resultado.get('importe_bruto')} {resultado.get('moneda')} | "
                f"Tipo: {resultado.get('tipo_pago')}"
            )

            return resultado

        except Exception as e:
            logger.error(f"Error parseando correo {message_id}: {e}")
            return None

    @staticmethod
    def extraer_nombre_destinatario(to_raw: str) -> Optional[str]:
        """
        Extrae el nombre del destinatario del header To: del correo.

        El header viene en formato:
            "Jhoisa Blanco Padilla <bjhoisa16@gmail.com>"
        o simplemente:
            "bjhoisa16@gmail.com"

        Args:
            to_raw: Valor del header To: del correo

        Returns:
            Nombre del destinatario, o la parte antes del @ si no hay nombre,
            o None si el header está vacío

        Example:
            >>> extraer_nombre_destinatario("Jhoisa Blanco Padilla <bjhoisa16@gmail.com>")
            "Jhoisa Blanco Padilla"
            >>> extraer_nombre_destinatario("bjhoisa16@gmail.com")
            "bjhoisa16"
        """
        if not to_raw:
            return None

        to_raw = to_raw.strip()

        # Formato: "Nombre Completo <email@gmail.com>"
        match = re.match(r'^"?([^"<]+)"?\s*<.+>$', to_raw)
        if match:
            nombre = match.group(1).strip()
            if nombre:
                return nombre

        # Formato: solo email
        match_email = re.match(r'^([^@]+)@', to_raw)
        if match_email:
            return match_email.group(1)

        return to_raw

    def parse_cuenta_destino(self, raw_headers: str) -> Optional[str]:
        """
        Extrae la cuenta Gmail destino del header X-Forwarded-For.
        Útil para saber a qué cuenta llegó el pago originalmente.

        Args:
            raw_headers: Headers del correo en texto plano

        Returns:
            str con el email de destino original, o None
        """
        # X-Forwarded-For: bjhoisa16@gmail.com ceiba21.oficial@gmail.com
        match = re.search(
            r'X-Forwarded-For:\s*(\S+@\S+)',
            raw_headers,
            re.IGNORECASE
        )
        if match:
            return match.group(1)
        return None