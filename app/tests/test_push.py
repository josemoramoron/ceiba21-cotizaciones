"""
Tests de Web Push: suscripciones de cliente, anónimo y operador.
"""
import pytest

from app.models.push_subscription import PushSubscription


@pytest.fixture
def limpiar_subs(db):
    """Borra las suscripciones creadas por el test."""
    endpoints = []
    yield endpoints
    for endpoint in endpoints:
        PushSubscription.query.filter_by(endpoint=endpoint).delete()
    db.session.commit()


class TestSuscripciones:
    """Alta y consulta de suscripciones."""

    def test_upsert_crea_suscripcion_anonima(self, db, limpiar_subs):
        """Un visitante anónimo puede suscribirse (sin WebUser)."""
        endpoint = 'https://push.example.com/test-anon-1'
        limpiar_subs.append(endpoint)

        sub = PushSubscription.upsert(
            endpoint=endpoint, p256dh='clave_p256', auth='clave_auth',
            anon_id='anon_test_1',
        )

        assert sub is not None
        assert sub.anon_id == 'anon_test_1'
        assert sub.web_user_id is None
        assert sub.is_active is True

    def test_upsert_no_duplica_por_endpoint(self, db, limpiar_subs):
        """Reenviar la misma suscripción actualiza, no duplica."""
        endpoint = 'https://push.example.com/test-anon-2'
        limpiar_subs.append(endpoint)

        PushSubscription.upsert(endpoint=endpoint, p256dh='a', auth='b',
                                anon_id='anon_test_2')
        PushSubscription.upsert(endpoint=endpoint, p256dh='c', auth='d',
                                anon_id='anon_test_2')

        encontradas = PushSubscription.query.filter_by(endpoint=endpoint).all()
        assert len(encontradas) == 1
        assert encontradas[0].p256dh == 'c'  # se actualizó

    def test_busqueda_por_anon(self, db, limpiar_subs):
        """Se recuperan las suscripciones activas de un anónimo."""
        endpoint = 'https://push.example.com/test-anon-3'
        limpiar_subs.append(endpoint)

        PushSubscription.upsert(endpoint=endpoint, p256dh='a', auth='b',
                                anon_id='anon_test_3')

        subs = PushSubscription.get_active_for_anon('anon_test_3')
        assert len(subs) == 1

    def test_desactivar_por_endpoint(self, db, limpiar_subs):
        """Un endpoint muerto (404/410) se desactiva, no se borra."""
        endpoint = 'https://push.example.com/test-anon-4'
        limpiar_subs.append(endpoint)

        PushSubscription.upsert(endpoint=endpoint, p256dh='a', auth='b',
                                anon_id='anon_test_4')
        PushSubscription.deactivate_by_endpoint(endpoint)

        sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
        assert sub.is_active is False
        assert PushSubscription.get_active_for_anon('anon_test_4') == []

    def test_formato_para_pywebpush(self, db, limpiar_subs):
        """El dict de suscripción tiene la forma que espera pywebpush."""
        endpoint = 'https://push.example.com/test-anon-5'
        limpiar_subs.append(endpoint)

        sub = PushSubscription.upsert(endpoint=endpoint, p256dh='p', auth='a',
                                      anon_id='anon_test_5')
        info = sub.to_subscription_info()

        assert info['endpoint'] == endpoint
        assert info['keys'] == {'p256dh': 'p', 'auth': 'a'}


class TestRutasPush:
    """Endpoints de suscripción."""

    def test_clave_publica_disponible(self, client):
        """El navegador puede pedir la clave VAPID pública."""
        r = client.get('/push/vapid-public-key')
        assert r.status_code == 200
        assert 'publicKey' in r.get_json()

    def test_suscripcion_invalida_rechazada(self, client):
        """Una suscripción sin claves se rechaza con 400."""
        r = client.post('/push/subscribe', json={'endpoint': 'https://x/y'})
        assert r.status_code == 400
        assert r.get_json()['ok'] is False
