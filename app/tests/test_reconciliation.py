"""
Tests de la conciliación pago ↔ orden.

Lo crítico: que NUNCA vincule cuando hay duda. Un falso positivo aquí significa
dar por bueno un pago que no entró.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.reconciliation_service import (
    ReconciliationService, UMBRAL_VINCULACION, MARGEN_EMPATE
)


# Centinela: permite distinguir "no me pasaron fecha" (usa la de por defecto)
# de "me pasaron None a propósito" (pago sin fecha). Con `fecha or defecto` el
# None se sustituía silenciosamente y el caso nunca llegaba a probarse.
_SIN_VALOR = object()

FECHA_PAGO = datetime(2026, 7, 12, 14, 30)
FECHA_ORDEN = datetime(2026, 7, 12, 13, 45)


def hacer_pago(importe=15.00, pagador='Jose Mora', metodo='paypal',
               fecha=_SIN_VALOR, memo=None):
    """Pago falso con los campos que usa el puntaje."""
    return SimpleNamespace(
        id=1,
        importe_bruto=Decimal(str(importe)),
        pagador_nombre=pagador,
        metodo=metodo,
        fecha_pago=FECHA_PAGO if fecha is _SIN_VALOR else fecha,
        memo=memo,
        notas=None,
        order_id=None,
    )


def hacer_orden(amount=15.00, holder='Jose Mora', creada=_SIN_VALOR,
                reference='ORD-20260712-001'):
    """Orden falsa con los campos que usa el puntaje."""
    return SimpleNamespace(
        id=1,
        reference=reference,
        amount_usd=Decimal(str(amount)),
        client_holder=holder,
        created_at=FECHA_ORDEN if creada is _SIN_VALOR else creada,
    )


class TestSimilitudDeNombres:
    """La comparación replica el ojo humano."""

    def test_ignora_mayusculas_y_acentos(self):
        assert ReconciliationService.similitud_nombres(
            'MARÍA RODRÍGUEZ', 'maria rodriguez') >= 0.95

    def test_ignora_el_orden_de_los_apellidos(self):
        assert ReconciliationService.similitud_nombres(
            'Mora Jose', 'Jose Mora') >= 0.95

    def test_nombres_distintos_no_coinciden(self):
        assert ReconciliationService.similitud_nombres(
            'Pedro Perez', 'Ana Gomez') < 0.65

    def test_nombre_vacio_da_cero(self):
        assert ReconciliationService.similitud_nombres('', 'Jose') == 0.0


class TestPuntajeDeMonto:
    """Se compara el BRUTO: la comisión (variable) no interfiere."""

    def test_monto_exacto_puntua_alto(self):
        puntos, motivo = ReconciliationService._puntuar_monto(
            hacer_pago(15.00), hacer_orden(15.00))
        assert puntos == 45

    def test_de_mas_dentro_de_un_dolar(self):
        """El cliente redondeó de 14.87 a 15: se acepta con menos puntaje."""
        puntos, _ = ReconciliationService._puntuar_monto(
            hacer_pago(15.00), hacer_orden(14.87))
        assert puntos == 35

    def test_de_mas_de_lo_tolerado_no_puntua(self):
        puntos, _ = ReconciliationService._puntuar_monto(
            hacer_pago(20.00), hacer_orden(15.00))
        assert puntos == 0

    def test_de_menos_nunca_puntua(self):
        """Si envió menos de lo pactado, no se concilia solo."""
        puntos, _ = ReconciliationService._puntuar_monto(
            hacer_pago(14.00), hacer_orden(15.00))
        assert puntos == 0

    def test_la_comision_no_afecta(self):
        """Aunque PayPal cobre distinto (F&F, tarjeta), el bruto no cambia."""
        pago = hacer_pago(15.00)   # bruto: lo que el cliente tecleó
        puntos, _ = ReconciliationService._puntuar_monto(pago, hacer_orden(15.00))
        assert puntos == 45


class TestPuntajeTotal:
    """El caso típico del operador debe superar el umbral."""

    def test_caso_tipico_supera_el_umbral(self):
        """Método + monto exacto + nombre + misma franja = vinculable."""
        puntos, motivos = ReconciliationService.puntuar(
            hacer_pago(15.00, 'Jose Mora'), hacer_orden(15.00, 'Jose Mora'))
        assert puntos >= UMBRAL_VINCULACION

    def test_nombre_distinto_baja_el_puntaje(self):
        """Mismo monto pero otro pagador: no alcanza para vincular solo."""
        puntos, _ = ReconciliationService.puntuar(
            hacer_pago(15.00, 'Ana Gomez'), hacer_orden(15.00, 'Jose Mora'))
        assert puntos < UMBRAL_VINCULACION

    def test_referencia_en_memo_es_determinante(self):
        """Si el cliente escribió la referencia, se dispara el puntaje."""
        puntos, motivos = ReconciliationService.puntuar(
            hacer_pago(15.00, memo='Pago ORD-20260712-001'),
            hacer_orden(15.00, reference='ORD-20260712-001'))
        assert puntos >= 100
        assert 'referencia en el memo' in motivos

    def test_pago_muy_posterior_no_suma_tiempo(self):
        """Un pago de 3 días después no puntúa por cercanía."""
        puntos, _ = ReconciliationService._puntuar_tiempo(
            hacer_pago(fecha=datetime(2026, 7, 15, 14, 0)),
            hacer_orden(creada=datetime(2026, 7, 12, 13, 45)))
        assert puntos == 0


class TestVentanaTemporal:
    """La ventana de 24 h es un filtro duro, no un simple puntaje."""

    def test_pago_dentro_de_la_ventana(self):
        assert ReconciliationService._dentro_de_ventana(
            hacer_pago(fecha=datetime(2026, 7, 12, 14, 0)),
            hacer_orden(creada=datetime(2026, 7, 12, 13, 0))) is True

    def test_pago_fuera_de_la_ventana_queda_excluido(self):
        """Un pago de 3 días después NO es candidato, aunque todo coincida."""
        assert ReconciliationService._dentro_de_ventana(
            hacer_pago(fecha=datetime(2026, 7, 15, 14, 0)),
            hacer_orden(creada=datetime(2026, 7, 12, 13, 0))) is False

    def test_pago_sin_fecha_no_es_candidato(self):
        """Sin fecha de pago no se puede evaluar la ventana: no es candidato."""
        assert ReconciliationService._dentro_de_ventana(
            hacer_pago(fecha=None), hacer_orden()) is False

    def test_orden_sin_fecha_no_es_candidata(self):
        """Lo mismo si la orden no tiene fecha de creación."""
        assert ReconciliationService._dentro_de_ventana(
            hacer_pago(), hacer_orden(creada=None)) is False


class TestReglasDeSeguridad:
    """Con dinero, ante la duda no se adivina."""

    def test_el_margen_de_empate_es_estricto(self):
        """Dos candidatos con puntajes parecidos se consideran empate."""
        assert MARGEN_EMPATE >= 10

    def test_umbral_exige_varias_senales(self):
        """El umbral no se alcanza con una sola señal (p.ej. solo el monto)."""
        solo_monto, _ = ReconciliationService._puntuar_monto(
            hacer_pago(15.00), hacer_orden(15.00))
        assert solo_monto < UMBRAL_VINCULACION
