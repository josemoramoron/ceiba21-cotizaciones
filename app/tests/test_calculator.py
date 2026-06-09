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

from app import create_app
from app.services.calculator_service import CalculatorService


@pytest.fixture(autouse=True)
def app_context():
    """Contexto de app para cada test (acceso a la BD de dev)."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'postgresql://webmaster:postgres123@localhost/ceiba21_dev'
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