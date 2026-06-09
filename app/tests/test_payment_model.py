"""
Tests del modelo Payment.

Prueban la lógica en memoria (propiedades calculadas, lectura/escritura de
datos_extra y aplicar_calculo) sin tocar la base de datos.
"""
from app.models.payment import (
    Payment, PaymentProvider, PaymentStatus, PaypalSubtipo
)


class TestMontoBaseCalculo:
    """monto_base_calculo: neto si existe, si no bruto, si no None."""

    def test_usa_neto_si_existe(self):
        p = Payment(importe_bruto=100, importe_neto=95)
        assert p.monto_base_calculo == 95.0

    def test_usa_bruto_si_no_hay_neto(self):
        p = Payment(importe_bruto=100, importe_neto=None)
        assert p.monto_base_calculo == 100.0

    def test_none_si_no_hay_montos(self):
        assert Payment().monto_base_calculo is None


class TestMonedaSoportada:
    """es_moneda_soportada: solo USD se auto-valoriza."""

    def test_usd_soportada(self):
        assert Payment(moneda='USD').es_moneda_soportada is True

    def test_eur_no_soportada(self):
        assert Payment(moneda='EUR').es_moneda_soportada is False


class TestDatosExtra:
    """Lectores planos (subtipo/memo) y set_dato_extra sobre datos_extra."""

    def test_subtipo_desde_datos_extra(self):
        p = Payment(metodo=PaymentProvider.PAYPAL,
                    datos_extra={'subtipo': PaypalSubtipo.GS})
        assert p.subtipo == PaypalSubtipo.GS

    def test_subtipo_none_si_no_existe(self):
        assert Payment(metodo=PaymentProvider.ZELLE).subtipo is None

    def test_memo_desde_datos_extra(self):
        p = Payment(metodo=PaymentProvider.ZELLE, datos_extra={'memo': 'C21'})
        assert p.memo == 'C21'

    def test_direccion_envio_desde_datos_extra(self):
        p = Payment(metodo=PaymentProvider.PAYPAL,
                    datos_extra={'direccion_envio': 'Calle 1, Bogotá'})
        assert p.direccion_envio == 'Calle 1, Bogotá'

    def test_set_dato_extra_inicializa_si_none(self):
        p = Payment()
        assert p.datos_extra is None
        p.set_dato_extra('subtipo', PaypalSubtipo.FF)
        assert p.datos_extra == {'subtipo': PaypalSubtipo.FF}
        assert p.subtipo == PaypalSubtipo.FF


class TestAplicarCalculo:
    """aplicar_calculo: traslada el resultado y avanza el estado con cuidado."""

    def _resultado(self) -> dict:
        return {
            'cotizacion_id': 9,
            'tasa_aplicada': 684.76,
            'valor_a_pagar': 34238.0,
            'moneda_local': 'VES',
        }

    def test_aplica_resultado_y_avanza_a_procesado(self):
        p = Payment(metodo=PaymentProvider.ZELLE, importe_bruto=50, moneda='USD',
                    estado=PaymentStatus.PENDIENTE)
        p.aplicar_calculo(self._resultado(), operador_id=7)
        assert p.cotizacion_id == 9
        assert p.tasa_aplicada == 684.76
        assert p.valor_a_pagar == 34238.0
        assert p.moneda_pago_local == 'VES'
        assert p.estado == PaymentStatus.PROCESADO
        assert p.procesado_por == 7

    def test_estado_manual_avanza_a_procesado(self):
        p = Payment(estado=PaymentStatus.MANUAL)
        p.aplicar_calculo(self._resultado())
        assert p.estado == PaymentStatus.PROCESADO

    def test_no_retrocede_estado_si_ya_pagado(self):
        p = Payment(estado=PaymentStatus.PAGADO)
        p.aplicar_calculo(self._resultado())
        # Un pago ya PAGADO no debe volver a PROCESADO al recalcular
        assert p.estado == PaymentStatus.PAGADO