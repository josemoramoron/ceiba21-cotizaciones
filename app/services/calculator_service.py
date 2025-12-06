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
            # O más preciso: net = (amount - 0.30) / 1.054
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
            'currency_code': currency.code
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
        
        rate = Decimal(str(quote.final_value)) if quote and quote.final_value else Decimal(str(exchange_rate.rate))
        
        # Calcular USD necesario
        usd_needed = (amount_local / rate).quantize(Decimal('0.01'))
        
        # Ajustar por comisión PayPal si aplica
        payment_method = PaymentMethod.query.get(payment_method_id)
        if payment_method and payment_method.name == 'PayPal':
            # amount_to_send = (usd_needed + 0.30) / 0.946
            amount_to_send = ((usd_needed + Decimal('0.30')) / Decimal('0.946')).quantize(Decimal('0.01'))
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
            'currency_code': currency.code if currency else 'USD'
        }
