"""
Tests de CurrencyService.

Usa la BD real de dev (ceiba21_dev, ya sembrada por scripts/seed_data.py).
Todo dato creado por un test se limpia en un finally, incluyendo las
cotizaciones que CurrencyService.create() genera automáticamente para
todos los métodos de pago activos (vía Currency.initialize_for_trading()).
"""
import pytest

from app import create_app
from app.models import db, Currency, ExchangeRate, Quote
from app.services.currency_service import CurrencyService


@pytest.fixture(autouse=True)
def app_context():
    """Contexto de app para cada test (acceso a la BD de dev)."""
    app = create_app()
    app.config['TESTING'] = True
    # :5433 porque en esta laptop el cluster nativo de Postgres no está en
    # el puerto default 5432 (ocupado por el contenedor Docker de FVA).
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'postgresql://webmaster:postgres123@localhost:5433/ceiba21_dev'
    )
    with app.app_context():
        yield


def _borrar_moneda_de_prueba(currency_id):
    """Limpieza común: borra Quotes + ExchangeRate + Currency de un ID de prueba."""
    Quote.query.filter_by(currency_id=currency_id).delete()
    ExchangeRate.query.filter_by(currency_id=currency_id).delete()
    Currency.query.filter_by(id=currency_id).delete()
    db.session.commit()


class TestGetById:
    def test_encuentra_moneda_existente(self):
        ves = Currency.query.filter_by(code='VES').first()
        assert ves is not None
        found = CurrencyService.get_by_id(ves.id)
        assert found.id == ves.id

    def test_id_inexistente_devuelve_none(self):
        assert CurrencyService.get_by_id(-1) is None


class TestGetByCode:
    def test_encuentra_por_codigo_exacto(self):
        found = CurrencyService.get_by_code('VES')
        assert found is not None
        assert found.code == 'VES'

    def test_es_insensible_a_mayusculas(self):
        found = CurrencyService.get_by_code('ves')
        assert found is not None
        assert found.code == 'VES'

    def test_codigo_inexistente_devuelve_none(self):
        assert CurrencyService.get_by_code('ZZZNOEXISTE') is None


class TestGetAll:
    def test_incluye_las_monedas_sembradas_y_ordena_por_codigo(self):
        monedas = CurrencyService.get_all()
        codigos = [m.code for m in monedas]
        assert 'VES' in codigos
        assert codigos == sorted(codigos)


class TestCreate:
    def test_crea_moneda_con_tasa_explicita(self):
        currency, error = CurrencyService.create('TSTC', 'Test Currency', 'T$', initial_rate=15.5)
        try:
            assert error is None
            assert currency is not None
            assert currency.code == 'TSTC'

            rate = ExchangeRate.query.filter_by(currency_id=currency.id).first()
            assert rate is not None
            assert float(rate.rate) == 15.5
        finally:
            if currency:
                _borrar_moneda_de_prueba(currency.id)

    def test_codigo_duplicado_da_error(self):
        currency, error = CurrencyService.create('VES', 'Duplicado', 'X')
        assert currency is None
        assert error is not None
        assert 'VES' in error

    def test_tasa_invalida_cae_a_default(self):
        currency, error = CurrencyService.create('TSTD', 'Test D', 'T$', initial_rate='no-es-numero')
        try:
            assert error is None
            rate = ExchangeRate.query.filter_by(currency_id=currency.id).first()
            # 'TSTD' no está en el dict de tasas conocidas de
            # Currency.get_default_rate_for_currency -> fallback genérico 1.0.
            assert float(rate.rate) == 1.0
        finally:
            if currency:
                _borrar_moneda_de_prueba(currency.id)

    def test_codigo_se_normaliza_a_mayusculas(self):
        """create() ahora uppercasea el code antes de guardarlo, para que
        quede consistente con get_by_code() (que uppercasea lo que busca)
        y con el resto del sistema (VES, COP, CLP, ...). Antes del fix,
        pasar un código en minúsculas dejaba la moneda inencontrable por
        get_by_code() — ver el fix en app/services/currency_service.py."""
        currency, error = CurrencyService.create('tstl', 'Test Lower', 'T$', initial_rate=5.0)
        try:
            assert error is None
            assert currency.code == 'TSTL'
            assert CurrencyService.get_by_code('tstl') is not None
            assert CurrencyService.get_by_code('tstl').id == currency.id
        finally:
            if currency:
                _borrar_moneda_de_prueba(currency.id)


class TestUpdate:
    def test_actualiza_solo_los_campos_dados(self):
        currency, _ = CurrencyService.create('TSTU', 'Original', 'T$', initial_rate=5.0)
        try:
            updated, error = CurrencyService.update(currency.id, name='Nuevo Nombre')
            assert error is None
            assert updated.name == 'Nuevo Nombre'
            assert updated.code == 'TSTU'  # no se tocó
        finally:
            if currency:
                _borrar_moneda_de_prueba(currency.id)

    def test_id_inexistente_da_error(self):
        updated, error = CurrencyService.update(-1, name='X')
        assert updated is None
        assert error == "Moneda no encontrada"


class TestToggleActive:
    def test_alterna_dos_veces_vuelve_al_original(self):
        currency, _ = CurrencyService.create('TSTA', 'Toggle', 'T$', initial_rate=5.0)
        try:
            original = currency.active
            toggled, _ = CurrencyService.toggle_active(currency.id)
            assert toggled.active != original
            toggled_again, _ = CurrencyService.toggle_active(currency.id)
            assert toggled_again.active == original
        finally:
            if currency:
                _borrar_moneda_de_prueba(currency.id)


class TestDelete:
    def test_rechaza_si_tiene_cotizaciones(self):
        currency, _ = CurrencyService.create('TSTE', 'Con Quotes', 'T$', initial_rate=5.0)
        try:
            ok, error = CurrencyService.delete(currency.id)
            assert ok is False
            assert 'cotizaciones' in error
        finally:
            if currency:
                _borrar_moneda_de_prueba(currency.id)

    def test_elimina_si_no_tiene_cotizaciones(self):
        currency = Currency(code='TSTF', name='Sin Quotes', symbol='T$', active=True)
        db.session.add(currency)
        db.session.commit()
        currency_id = currency.id
        try:
            ok, error = CurrencyService.delete(currency_id)
            assert ok is True
            assert error is None
            assert db.session.get(Currency, currency_id) is None
        finally:
            leftover = db.session.get(Currency, currency_id)
            if leftover:
                db.session.delete(leftover)
                db.session.commit()


class TestReorder:
    def test_aplica_el_orden_dado(self):
        c1 = Currency(code='TSTR1', name='R1', symbol='T$', active=True)
        c2 = Currency(code='TSTR2', name='R2', symbol='T$', active=True)
        db.session.add_all([c1, c2])
        db.session.commit()
        try:
            ok = CurrencyService.reorder([c2.id, c1.id])
            assert ok is True
            db.session.refresh(c1)
            db.session.refresh(c2)
            assert c2.display_order == 1
            assert c1.display_order == 2
        finally:
            Currency.query.filter(Currency.id.in_([c1.id, c2.id])).delete(synchronize_session=False)
            db.session.commit()

    def test_ignora_ids_inexistentes_sin_error(self):
        ok = CurrencyService.reorder([-1, -2])
        assert ok is True
