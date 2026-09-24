"""
Tests de CalculatorService.calcular_pago_recibido.

Se enfocan en el contrato de error: devolver SIEMPRE un dict (con 'error'
cuando falta método/moneda/cotización) y nunca lanzar excepción. Ese contrato
es lo que permite que la ingesta haga `if 'error' not in resultado` sin
reventar con KeyError, que fue el bug que corregimos.

La verificación de la cotización por método correcto (Zelle != PayPal) se hace
a nivel de aplicación en el dashboard; un test de ese camino feliz requiere
sembrar método+moneda+cotización en una BD aislada (pendiente: fixtures).
"""
import pytest
from decimal import Decimal

from app import create_app
from app.models import db
from app.models.currency import Currency
from app.models.payment_method import PaymentMethod
from app.models.exchange_rate import ExchangeRate
from app.models.quote import Quote
from app.services.calculator_service import CalculatorService


@pytest.fixture(autouse=True)
def app_context():
    """Contexto de app para cada test (acceso a la BD de dev)."""
    app = create_app()
    app.config['TESTING'] = True
    # :5433 porque en esta laptop el cluster nativo de Postgres no está en
    # el puerto default 5432 (ocupado por el contenedor Docker de FVA) —
    # sin el puerto explícito, la conexión cae silenciosamente en el
    # contenedor equivocado en vez de fallar limpio.
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'postgresql://webmaster:postgres123@localhost:5433/ceiba21_dev'
    )
    with app.app_context():
        yield


class TestCalcularPagoRecibido:
    """Contrato de error de calcular_pago_recibido."""

    def test_metodo_inexistente_retorna_error(self):
        r = CalculatorService.calcular_pago_recibido(
            100, 'VES', 'metodo_que_no_existe_xyz'
        )
        assert 'error' in r
        assert 'valor_a_pagar' not in r

    def test_error_es_dict_sin_lanzar(self):
        # Entrada inválida en todos los campos: debe devolver dict, no crashear.
        r = CalculatorService.calcular_pago_recibido(0, '', '')
        assert isinstance(r, dict)

    def test_moneda_invalida_no_crashea(self):
        # Código de moneda inexistente: cae en 'error', nunca KeyError/excepción.
        r = CalculatorService.calcular_pago_recibido(
            100, 'ZZZ', 'metodo_que_no_existe_xyz'
        )
        assert 'error' in r


@pytest.fixture
def datos_calculo():
    """
    Siembra datos mínimos para probar CalculatorService contra la BD real:

    - TSTX: moneda de prueba con Quote propia (final_value=9.50) tanto para
      un método normal (TSTPM) como para el PayPal real ya sembrado.
    - TSTY: moneda de prueba con ExchangeRate (20.0000) pero SIN Quote —
      prueba el fallback de calculate_exchange/calculate_reverse cuando no
      hay cotización propia del método.
    - TSTPM: método de pago de prueba, sin comisión.
    - Reutiliza el PaymentMethod 'PAYPAL' real ya sembrado por
      scripts/seed_data.py (no se crea ni se borra) para probar la rama
      real de comisión de PayPal, en vez de inventar un duplicado.
    """
    paypal = PaymentMethod.query.filter_by(code='PAYPAL').first()
    assert paypal is not None, (
        "Falta el PaymentMethod PAYPAL sembrado — correr scripts/seed_data.py"
    )

    tstx = Currency(code='TSTX', name='Test Currency X', symbol='T$', active=True, display_order=999)
    tsty = Currency(code='TSTY', name='Test Currency Y', symbol='T$', active=True, display_order=999)
    tstpm = PaymentMethod(code='TSTPM', name='Test Method', active=True, value_type='manual', usd_value=Decimal('1.0'))
    db.session.add_all([tstx, tsty, tstpm])
    db.session.flush()  # asigna IDs sin cerrar la transacción

    rate_x = ExchangeRate(currency_id=tstx.id, rate=Decimal('10.0000'), source_type='manual')
    rate_y = ExchangeRate(currency_id=tsty.id, rate=Decimal('20.0000'), source_type='manual')
    db.session.add_all([rate_x, rate_y])

    quote_tstpm_x = Quote(
        payment_method_id=tstpm.id, currency_id=tstx.id,
        value_type='manual', final_value=Decimal('9.50'),
    )
    quote_paypal_x = Quote(
        payment_method_id=paypal.id, currency_id=tstx.id,
        value_type='manual', final_value=Decimal('9.50'),
    )
    db.session.add_all([quote_tstpm_x, quote_paypal_x])
    db.session.commit()

    ids = {
        'tstx_id': tstx.id,
        'tsty_id': tsty.id,
        'tstpm_id': tstpm.id,
        'paypal_id': paypal.id,
    }
    yield ids

    # Limpieza en orden por FKs: Quote -> ExchangeRate -> PaymentMethod/Currency.
    # El PaymentMethod PAYPAL real (paypal.id) NO se toca.
    Quote.query.filter(Quote.currency_id.in_([tstx.id, tsty.id])).delete(synchronize_session=False)
    ExchangeRate.query.filter(ExchangeRate.currency_id.in_([tstx.id, tsty.id])).delete(synchronize_session=False)
    PaymentMethod.query.filter_by(id=tstpm.id).delete(synchronize_session=False)
    Currency.query.filter(Currency.id.in_([tstx.id, tsty.id])).delete(synchronize_session=False)
    db.session.commit()


class TestComisionPaypal:
    """comision_paypal(): pura, sin DB — comisión = 5.4% + $0.30 fijo."""

    def test_comision_sobre_100(self):
        comision, neto = CalculatorService.comision_paypal(Decimal('100'))
        assert comision == Decimal('5.70')
        assert neto == Decimal('94.30')

    def test_comision_redondea_a_dos_decimales(self):
        comision, neto = CalculatorService.comision_paypal(Decimal('10.55'))
        assert comision == Decimal('0.87')
        assert neto == Decimal('9.68')

    def test_monto_cero_da_neto_negativo(self):
        """Comportamiento actual, no necesariamente deseado: con bruto=0 la
        tarifa fija de $0.30 se cobra igual, dando un neto negativo. Se deja
        documentado como test de regresión, no como validación de que esto
        sea correcto para el negocio — vale la pena que Jose lo revise."""
        comision, neto = CalculatorService.comision_paypal(Decimal('0'))
        assert comision == Decimal('0.30')
        assert neto == Decimal('-0.30')


class TestCalculateExchange:
    """calculate_exchange(): conversión USD -> moneda local."""

    def test_usa_quote_cuando_existe(self, datos_calculo):
        r = CalculatorService.calculate_exchange(
            Decimal('100.00'), datos_calculo['tstx_id'], datos_calculo['tstpm_id']
        )
        assert r['fee_usd'] == Decimal('0.00')
        assert r['net_usd'] == Decimal('100.00')
        assert r['exchange_rate'] == Decimal('9.50')
        assert r['amount_local'] == Decimal('950.00')

    def test_cae_a_tasa_general_sin_quote(self, datos_calculo):
        r = CalculatorService.calculate_exchange(
            Decimal('100.00'), datos_calculo['tsty_id'], datos_calculo['tstpm_id']
        )
        assert r['exchange_rate'] == Decimal('20.0000')
        assert r['amount_local'] == Decimal('2000.00')

    def test_paypal_aplica_comision(self, datos_calculo):
        r = CalculatorService.calculate_exchange(
            Decimal('100.00'), datos_calculo['tstx_id'], datos_calculo['paypal_id']
        )
        assert r['fee_usd'] == Decimal('5.70')
        assert r['net_usd'] == Decimal('94.30')
        assert r['amount_local'] == Decimal('895.85')

    def test_currency_o_metodo_inexistente_lanza_valueerror(self, datos_calculo):
        with pytest.raises(ValueError):
            CalculatorService.calculate_exchange(
                Decimal('100'), -1, datos_calculo['tstpm_id']
            )

    def test_sin_exchange_rate_lanza_valueerror(self, datos_calculo):
        currency = Currency(code='TSTZ', name='Test Z', symbol='T$', active=True)
        db.session.add(currency)
        db.session.commit()
        try:
            with pytest.raises(ValueError):
                CalculatorService.calculate_exchange(
                    Decimal('100'), currency.id, datos_calculo['tstpm_id']
                )
        finally:
            Currency.query.filter_by(id=currency.id).delete()
            db.session.commit()


class TestCalculateReverse:
    """calculate_reverse(): conversión moneda local -> USD (inversa)."""

    def test_no_paypal_sin_comision(self, datos_calculo):
        r = CalculatorService.calculate_reverse(
            Decimal('950.00'), datos_calculo['tstx_id'], datos_calculo['tstpm_id']
        )
        assert r['net_usd'] == Decimal('100.00')
        assert r['amount_usd'] == Decimal('100.00')
        assert r['fee_usd'] == Decimal('0.00')

    def test_paypal_ajusta_por_comision(self, datos_calculo):
        r = CalculatorService.calculate_reverse(
            Decimal('895.85'), datos_calculo['tstx_id'], datos_calculo['paypal_id']
        )
        assert r['net_usd'] == Decimal('94.30')
        assert r['amount_usd'] == Decimal('100.00')
        assert r['fee_usd'] == Decimal('5.70')

    def test_ida_y_vuelta_son_inversas_para_paypal(self, datos_calculo):
        """calculate_exchange y calculate_reverse deben ser inversas exactas
        (no aproximadas) para PayPal: el divisor 0.946 de calculate_reverse
        es exactamente 1 - PAYPAL_FEE_PERCENT."""
        ida = CalculatorService.calculate_exchange(
            Decimal('100.00'), datos_calculo['tstx_id'], datos_calculo['paypal_id']
        )
        vuelta = CalculatorService.calculate_reverse(
            ida['amount_local'], datos_calculo['tstx_id'], datos_calculo['paypal_id']
        )
        assert vuelta['amount_usd'] == Decimal('100.00')


class TestCalcularPagoPaypalRecibido:
    """calcular_pago_paypal_recibido(): camino feliz + moneda inactiva."""

    def test_camino_feliz(self, datos_calculo):
        r = CalculatorService.calcular_pago_paypal_recibido(40.0, 'TSTX')
        assert 'error' not in r
        assert r['valor_a_pagar'] == 380.0
        assert r['tasa_aplicada'] == 9.5
        assert r['moneda_local'] == 'TSTX'

    def test_moneda_inactiva_da_error(self):
        currency = Currency(code='TSTI', name='Test Inactiva', symbol='T$', active=False)
        db.session.add(currency)
        db.session.commit()
        try:
            r = CalculatorService.calcular_pago_paypal_recibido(40.0, 'TSTI')
            assert 'error' in r
        finally:
            Currency.query.filter_by(id=currency.id).delete()
            db.session.commit()


class TestCalcularPublicoMethodToFiat:
    """calcular_publico_method_to_fiat(): calculadora pública, y la defensa
    en profundidad contra métodos estructurales/pivote."""

    def test_metodo_pivote_ref_no_se_expone(self, datos_calculo):
        """REF es estructural/pivote (PaymentMethod.CODIGOS_NO_PUBLICOS):
        pedirlo directo por código debe dar el MISMO error genérico que un
        método inexistente, sin revelar que existe."""
        r = CalculatorService.calcular_publico_method_to_fiat('REF', 'TSTX', 100)
        assert 'error' in r
        assert 'no encontrado o inactivo' in r['error']

    def test_metodo_publico_camino_feliz(self, datos_calculo):
        r = CalculatorService.calcular_publico_method_to_fiat('PAYPAL', 'TSTX', 100)
        assert 'error' not in r
        assert r['tasa_ref'] == 9.5
        assert r['resultado'] == 950.0
        assert r['tipo'] == 'method_to_fiat'

    def test_metodo_o_moneda_inexistente_da_error(self, datos_calculo):
        r = CalculatorService.calcular_publico_method_to_fiat('NOEXISTE', 'TSTX', 100)
        assert 'error' in r


class TestCalcularPublicoFiatToFiat:
    """calcular_publico_fiat_to_fiat(): calculadora pública fiat<->fiat vía
    el pivote USD (ExchangeRateService.get_cross_rate)."""

    def test_camino_feliz_sin_margen(self, datos_calculo):
        r = CalculatorService.calcular_publico_fiat_to_fiat('USD', 'TSTX', 100, 0)
        assert 'error' not in r
        assert r['tasa_ref'] == 10.0
        assert r['resultado'] == 1000.0

    def test_camino_feliz_con_margen(self, datos_calculo):
        r = CalculatorService.calcular_publico_fiat_to_fiat('USD', 'TSTX', 100, 5)
        # Float, no Decimal: comparar con tolerancia en vez de ==.
        assert r['tasa_efectiva'] == pytest.approx(9.523810, rel=1e-6)
        assert r['resultado'] == pytest.approx(952.38, rel=1e-4)

    def test_moneda_sin_tasa_da_error(self, datos_calculo):
        r = CalculatorService.calcular_publico_fiat_to_fiat('ZZZ1', 'ZZZ2', 100, 0)
        assert 'error' in r
