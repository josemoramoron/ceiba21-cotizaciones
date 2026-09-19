/**
 * Interceptor global de CSRF para peticiones fetch().
 *
 * Flask-WTF exige un token en cualquier POST/PUT/PATCH/DELETE. En vez de
 * agregarlo a mano en cada llamada fetch() del dashboard (son ~39 puntos
 * distintos), este script lo agrega automaticamente leyendo el
 * <meta name="csrf-token"> que ya viene en base.html y public_base.html.
 *
 * Solo toca peticiones al mismo origen (nunca manda el token a un dominio
 * externo) y solo en metodos que cambian estado; GET/HEAD/OPTIONS quedan
 * intactos porque Flask-WTF no los protege.
 */
(function () {
    'use strict';

    var META_SELECTOR = 'meta[name="csrf-token"]';
    var HEADER_NAME = 'X-CSRFToken';
    var METODOS_PROTEGIDOS = ['POST', 'PUT', 'PATCH', 'DELETE'];

    function obtenerToken() {
        var meta = document.querySelector(META_SELECTOR);
        return meta ? meta.getAttribute('content') : null;
    }

    function esMismoOrigen(url) {
        try {
            var absoluta = new URL(url, window.location.href);
            return absoluta.origin === window.location.origin;
        } catch (e) {
            // URLs relativas raras o malformadas: por seguridad, no se tocan.
            return false;
        }
    }

    var fetchOriginal = window.fetch;
    if (typeof fetchOriginal !== 'function') {
        return;
    }

    window.fetch = function (input, init) {
        var token = obtenerToken();
        if (!token) {
            return fetchOriginal(input, init);
        }

        var url = (typeof input === 'string') ? input : input.url;
        var metodo = ((init && init.method) || (input && input.method) || 'GET').toUpperCase();

        if (METODOS_PROTEGIDOS.indexOf(metodo) === -1 || !esMismoOrigen(url)) {
            return fetchOriginal(input, init);
        }

        init = init || {};
        var headers = new Headers(init.headers || (typeof input !== 'string' ? input.headers : undefined));
        if (!headers.has(HEADER_NAME)) {
            headers.set(HEADER_NAME, token);
        }
        init.headers = headers;

        return fetchOriginal(input, init);
    };
})();
