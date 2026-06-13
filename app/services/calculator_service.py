"""
Calculator Service - Cálculos de conversión de divisas.
Calcula montos, comisiones y tasas aplicando las fórmulas del sistema.
"""
from decimal import Decimal
from typing import Dict, Any
from app.models.currency import Currency
from app.models.payment_method import PaymentMethod
from app.models.exchange_rate import ExchangeRate
from app.models.quote import Quote


class CalculatorService:
    """
    Servicio para calcular conversiones de divisas.

    Maneja comisiones de PayPal y otros métodos de pago.
    """

    @classmethod
    def calculate_exchange(
        cls,
        amount_usd: Decimal,
        currency_id: int,
        payment_method_id: int
    ) -> Dict[str, Any]:
        """
        Calcular conversión completa.

        Args:
            amount_usd: Monto que el cliente enviará en USD
            currency_id: ID de la moneda destino
            payment_method_id: ID del método de pago

        Returns:
            Dict con todos los valores calculados
        """
        # Obtener modelos
        currency = Currency.query.get(currency_id)
        payment_method = PaymentMethod.query.get(payment_method_id)

        if not currency or not payment_method:
            raise ValueError("Currency o PaymentMethod no encontrado")

        # Obtener tasa de cambio
        exchange_rate = ExchangeRate.query.filter_by(currency_id=currency_id).first()
        if not exchange_rate:
            raise ValueError(f"Exchange rate no encontrado para {currency.code}")

        # Calcular comisión (solo PayPal tiene comisión de plataforma)
        fee_usd = Decimal('0.00')
        net_usd = amount_usd

        if payment_method.name == 'PayPal':
            # Fórmula PayPal: fee = (amount - 0.30) * 0.054
            fee_usd = ((amount_usd - Decimal('0.30')) * Decimal('0.054')).quantize(Decimal('0.01'))
            net_usd = (amount_usd - Decimal('0.30') - fee_usd).quantize(Decimal('0.01'))

        # Obtener quote para este método y moneda
        quote = Quote.query.filter_by(
            payment_method_id=payment_method_id,
            currency_id=currency_id
        ).first()

        # Usar tasa del quote si existe, sino la tasa general
        if quote and quote.final_value:
            rate = Decimal(str(quote.final_value))
        else:
            rate = Decimal(str(exchange_rate.rate))

        # Calcular monto en moneda local
        amount_local = (net_usd * rate).quantize(Decimal('0.01'))

        return {
            'amount_usd': amount_usd,
            'fee_usd': fee_usd,
            'net_usd': net_usd,
            'exchange_rate': rate,
            'amount_local': amount_local,
            'currency_code': currency.code,
        }

    @classmethod
    def calculate_reverse(
        cls,
        amount_local: Decimal,
        currency_id: int,
        payment_method_id: int
    ) -> Dict[str, Any]:
        """
        Cálculo inverso: desde moneda local a USD.

        Args:
            amount_local: Monto en moneda local que el cliente recibirá
            currency_id: ID de la moneda
            payment_method_id: ID del método de pago

        Returns:
            Dict con valores calculados
        """
        # Obtener tasa
        exchange_rate = ExchangeRate.query.filter_by(currency_id=currency_id).first()
        if not exchange_rate:
            raise ValueError("Exchange rate no encontrado")

        quote = Quote.query.filter_by(
            payment_method_id=payment_method_id,
            currency_id=currency_id
        ).first()

        rate = (
            Decimal(str(quote.final_value))
            if quote and quote.final_value
            else Decimal(str(exchange_rate.rate))
        )

        # Calcular USD necesario
        usd_needed = (amount_local / rate).quantize(Decimal('0.01'))

        # Ajustar por comisión PayPal si aplica
        payment_method = PaymentMethod.query.get(payment_method_id)
        if payment_method and payment_method.name == 'PayPal':
            # amount_to_send = (usd_needed + 0.30) / 0.946
            amount_to_send = (
                (usd_needed + Decimal('0.30')) / Decimal('0.946')
            ).quantize(Decimal('0.01'))
            fee = (amount_to_send - usd_needed).quantize(Decimal('0.01'))
        else:
            amount_to_send = usd_needed
            fee = Decimal('0.00')

        currency = Currency.query.get(currency_id)

        return {
            'amount_local': amount_local,
            'amount_usd': amount_to_send,
            'net_usd': usd_needed,
            'fee_usd': fee,
            'exchange_rate': rate,
            'currency_code': currency.code if currency else 'USD',
        }

    @classmethod
    def calcular_pago_paypal_recibido(
        cls,
        monto_base: float,
        currency_code: str
    ) -> dict:
        """
        Calcula el valor a pagar al cliente por un pago PayPal recibido.

        Busca la cotización vigente de PayPal para la moneda indicada
        y multiplica por el monto base (neto tras comisión PayPal).

        Args:
            monto_base: Monto neto en USD (después de comisión PayPal)
            currency_code: Código de moneda local (VES, COP, BRL, etc.)

        Returns:
            dict con valor_a_pagar, tasa_aplicada, cotizacion_id, moneda_local
            o dict con 'error' si no hay cotización disponible

        Example:
            >>> CalculatorService.calcular_pago_paypal_recibido(40.0, 'VES')
            {'valor_a_pagar': 25223.6, 'tasa_aplicada': 630.59, ...}
        """
        paypal_method = PaymentMethod.query.filter_by(code='PAYPAL').first()
        if not paypal_method:
            paypal_method = PaymentMethod.query.filter(
                PaymentMethod.name.ilike('%paypal%')
            ).first()

        if not paypal_method:
            return {'error': 'Método de pago PayPal no encontrado'}

        currency = Currency.query.filter_by(
            code=currency_code.upper(),
            active=True
        ).first()
        if not currency:
            return {'error': f'Moneda {currency_code} no encontrada o inactiva'}

        quote = Quote.query.filter_by(
            payment_method_id=paypal_method.id,
            currency_id=currency.id
        ).first()

        if not quote or not quote.final_value:
            return {'error': f'No hay cotización PayPal activa para {currency_code}'}

        tasa = float(quote.final_value)
        valor = round(monto_base * tasa, 2)

        return {
            'valor_a_pagar': valor,
            'tasa_aplicada': tasa,
            'cotizacion_id': quote.id,
            'moneda_local': currency_code.upper(),
        }

    @classmethod
    def calcular_pago_recibido(
        cls,
        monto_base: float,
        currency_code: str,
        metodo_code: str
    ) -> dict:
        """
        Calcula el valor a pagar usando la cotizacion DEL METODO indicado.

        Args:
            monto_base: Monto neto en USD.
            currency_code: Codigo de moneda local (VES, COP, ...).
            metodo_code: Codigo del metodo ('paypal', 'zelle', 'wise', ...).

        Returns:
            dict con valor_a_pagar, tasa_aplicada, cotizacion_id, moneda_local,
            o dict con 'error' si no hay metodo/moneda/cotizacion.
        """
        method = PaymentMethod.query.filter_by(code=metodo_code.upper()).first()
        if not method:
            method = PaymentMethod.query.filter(
                PaymentMethod.name.ilike(f'%{metodo_code}%')
            ).first()
        if not method:
            return {'error': f'Metodo {metodo_code} no encontrado'}

        currency = Currency.query.filter_by(
            code=currency_code.upper(), active=True
        ).first()
        if not currency:
            return {'error': f'Moneda {currency_code} no encontrada o inactiva'}

        quote = Quote.query.filter_by(
            payment_method_id=method.id, currency_id=currency.id
        ).first()
        if not quote or not quote.final_value:
            return {'error': f'No hay cotizacion {metodo_code} para {currency_code}'}

        tasa = float(quote.final_value)
        return {
            'valor_a_pagar': round(monto_base * tasa, 2),
            'tasa_aplicada': tasa,
            'cotizacion_id': quote.id,
            'moneda_local': currency_code.upper(),
        }

    # ── Calculadora pública ────────────────────────────────────────────────

    @classmethod
    def calcular_publico_fiat_to_fiat(
        cls,
        tengo_code: str,
        quiero_code: str,
        monto: float,
        margen_pct: float,
    ) -> dict:
        """
        Conversión fiat↔fiat para la calculadora pública.

        Aplica el margen global configurado sobre la tasa cruzada
        derivada del pivote USD.

        Fórmula::

            tasa_efectiva = tasa_ref / (1 + margen_pct / 100)
            resultado     = monto * tasa_efectiva

        Args:
            tengo_code: Código de la moneda de origen (ej. 'USD', 'COP').
            quiero_code: Código de la moneda de destino (ej. 'VES').
            monto: Cantidad a convertir en la moneda de origen.
            margen_pct: Margen porcentual del operador (0 = sin margen).

        Returns:
            dict con tasa_ref, tasa_efectiva, resultado y tipo,
            o dict con 'error' si no hay tasa para alguna moneda.
        """
        from app.services.exchange_rate_service import ExchangeRateService

        cross = ExchangeRateService.get_cross_rate(tengo_code, quiero_code)
        if cross is None:
            return {
                'error': f'No hay tasa registrada para {tengo_code} o {quiero_code}'
            }

        divisor = 1.0 + margen_pct / 100.0
        tasa_efectiva = round(cross / divisor, 6)
        resultado = round(monto * tasa_efectiva, 2)

        return {
            'tengo': tengo_code.upper(),
            'quiero': quiero_code.upper(),
            'monto': monto,
            'tasa_ref': round(cross, 6),
            'tasa_efectiva': tasa_efectiva,
            'margen': margen_pct,
            'resultado': resultado,
            'tipo': 'fiat_to_fiat',
        }

    @classmethod
    def calcular_publico_method_to_fiat(
        cls,
        metodo_code: str,
        quiero_code: str,
        monto: float,
    ) -> dict:
        """
        Conversión método-de-pago→fiat para la calculadora pública.

        Usa directamente la cotización (Quote) vigente del método
        sin aplicar margen adicional. El margen del operador ya está
        incorporado en cada Quote a través del sistema de cotizaciones.
        El margen global de la calculadora aplica SOLO a fiat↔fiat.

        Args:
            metodo_code: Código del método de pago (ej. 'PAYPAL', 'ZELLE').
            quiero_code: Código de la moneda destino (ej. 'VES').
            monto: Monto en USD (todos los métodos se nominan en USD).

        Returns:
            dict con tasa, resultado y tipo,
            o dict con 'error' si no existe cotización activa.
        """
        method = PaymentMethod.query.filter_by(
            code=metodo_code.upper(), active=True
        ).first()
        if not method:
            method = PaymentMethod.query.filter(
                PaymentMethod.name.ilike(f'%{metodo_code}%'),
                PaymentMethod.active.is_(True),
            ).first()
        if not method:
            return {'error': f'Método {metodo_code} no encontrado o inactivo'}

        currency = Currency.query.filter_by(
            code=quiero_code.upper(), active=True
        ).first()
        if not currency:
            return {'error': f'Moneda {quiero_code} no encontrada o inactiva'}

        quote = Quote.query.filter_by(
            payment_method_id=method.id,
            currency_id=currency.id,
        ).first()
        if not quote or not quote.final_value:
            return {
                'error': (
                    f'No hay cotización activa de {metodo_code} '
                    f'para {quiero_code}'
                )
            }

        tasa = float(quote.final_value)
        resultado = round(monto * tasa, 2)

        return {
            'tengo': metodo_code.upper(),
            'quiero': quiero_code.upper(),
            'monto': monto,
            'tasa_ref': round(tasa, 6),
            'tasa_efectiva': round(tasa, 6),
            'margen': 0,
            'resultado': resultado,
            'tipo': 'method_to_fiat',
        }
