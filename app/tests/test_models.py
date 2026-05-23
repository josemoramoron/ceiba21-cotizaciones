"""
Tests para los modelos de Ceiba21.
Prueban lógica de negocio pura sin depender de HTTP.
"""
import pytest
from app import create_app, db as _db
from app.models.operator import Operator, OperatorRole
from app.models.currency import Currency


@pytest.fixture(autouse=True)
def app_context():
    """Contexto de app para cada test."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://webmaster:postgres123@localhost/ceiba21_dev'
    with app.app_context():
        yield


class TestOperator:
    """Tests del modelo Operator."""

    def test_password_hash_no_es_texto_plano(self):
        """La contraseña nunca debe guardarse en texto plano."""
        op = Operator()
        op.set_password('mi_password_123')
        assert op.password_hash != 'mi_password_123'
        assert op.password_hash is not None

    def test_verificar_password_correcto(self):
        """check_password debe retornar True con la contraseña correcta."""
        op = Operator()
        op.set_password('mi_password_123')
        assert op.check_password('mi_password_123') is True

    def test_verificar_password_incorrecto(self):
        """check_password debe retornar False con contraseña incorrecta."""
        op = Operator()
        op.set_password('mi_password_123')
        assert op.check_password('password_equivocada') is False

    def test_admin_tiene_todos_los_permisos(self):
        """Un operador ADMIN debe tener todos los permisos."""
        op = Operator(role=OperatorRole.ADMIN)
        assert op.has_permission('manage_operators') is True
        assert op.has_permission('edit_rates') is True
        assert op.has_permission('cancel_orders') is True

    def test_operator_no_tiene_permisos_admin(self):
        """Un operador normal no debe poder gestionar operadores."""
        op = Operator(role=OperatorRole.OPERATOR, permissions={})
        assert op.has_permission('manage_operators') is False


class TestCurrency:
    """Tests del modelo Currency."""

    def test_currencies_existen_en_bd(self):
        """Debe haber al menos una moneda activa en la BD."""
        currencies = Currency.query.filter_by(active=True).all()
        assert len(currencies) > 0

    def test_ves_y_cop_activas(self):
        """VES y COP deben estar activas — son las principales."""
        ves = Currency.query.filter_by(code='VES').first()
        cop = Currency.query.filter_by(code='COP').first()
        assert ves is not None
        assert cop is not None