/**
 * Banner de consentimiento de cookies — Ceiba21.
 *
 * Lee la configuración desde los data-attributes del banner (#cookieBanner),
 * gestiona la elección del usuario, escribe la cookie de consentimiento y la
 * registra en el servidor (POST /cookies/consent).
 */
(function () {
  'use strict';

  var banner = document.getElementById('cookieBanner');

  function readConfig() {
    var el = banner || document.body;
    return {
      name: el.getAttribute('data-cookie-name') || 'ceiba21_consent',
      version: el.getAttribute('data-cookie-version') || '1',
      maxAgeDays: parseInt(el.getAttribute('data-cookie-max-age-days') || '180', 10)
    };
  }

  var CFG = readConfig();

  function setCookie(categories) {
    var payload = encodeURIComponent(JSON.stringify({ v: CFG.version, c: categories }));
    var maxAge = CFG.maxAgeDays * 24 * 60 * 60;
    var secure = location.protocol === 'https:' ? '; secure' : '';
    document.cookie = CFG.name + '=' + payload +
      '; path=/; max-age=' + maxAge + '; samesite=Lax' + secure;
  }

  function recordConsent(categories) {
    // Registro en el servidor (auditoría + cookie autoritativa). No bloquea la UI.
    try {
      fetch('/cookies/consent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ categories: categories })
      }).catch(function () { /* la cookie local ya quedó escrita */ });
    } catch (e) { /* noop */ }
  }

  function hideBanner() {
    if (banner) {
      banner.classList.add('cookie-banner--hidden');
    }
  }

  function save(categories) {
    setCookie(categories);
    recordConsent(categories);
    hideBanner();
  }

  function readToggles() {
    var prefs = document.getElementById('cookiePrefPreferences');
    var analytics = document.getElementById('cookiePrefAnalytics');
    return {
      necessary: true,
      preferences: !!(prefs && prefs.checked),
      analytics: !!(analytics && analytics.checked)
    };
  }

  function bind() {
    if (!banner) { return; }

    var btnAccept = document.getElementById('cookieAcceptAll');
    var btnReject = document.getElementById('cookieRejectAll');
    var btnSave = document.getElementById('cookieSavePrefs');
    var btnPrefs = document.getElementById('cookieOpenPrefs');
    var prefsPanel = document.getElementById('cookiePrefsPanel');

    if (btnAccept) {
      btnAccept.addEventListener('click', function () {
        save({ necessary: true, preferences: true, analytics: true });
      });
    }
    if (btnReject) {
      btnReject.addEventListener('click', function () {
        save({ necessary: true, preferences: false, analytics: false });
      });
    }
    if (btnPrefs && prefsPanel) {
      btnPrefs.addEventListener('click', function () {
        prefsPanel.classList.toggle('cookie-banner__prefs--open');
      });
    }
    if (btnSave) {
      btnSave.addEventListener('click', function () {
        save(readToggles());
      });
    }
  }

  // Helper mínimo para que otros scripts comprueben categorías consentidas.
  window.Ceiba21Consent = {
    has: function (category) {
      if (category === 'necessary') { return true; }
      var safeName = CFG.name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1');
      var match = document.cookie.match(new RegExp('(?:^|; )' + safeName + '=([^;]*)'));
      if (!match) { return false; }
      try {
        var data = JSON.parse(decodeURIComponent(match[1]));
        return !!(data && data.c && data.c[category]);
      } catch (e) { return false; }
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
