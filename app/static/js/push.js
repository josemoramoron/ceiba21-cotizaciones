// Web Push — registro de suscripción del cliente (Ceiba21)
(function () {
  'use strict';

  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(base64);
    const arr = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
    return arr;
  }

  async function enablePush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      alert('Tu navegador no soporta notificaciones push.');
      return;
    }
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      alert('No se concedió permiso para notificaciones.');
      return;
    }

    const reg = await navigator.serviceWorker.register('/static/sw.js');
    await navigator.serviceWorker.ready;

    const keyRes = await fetch('/push/vapid-public-key');
    const { publicKey } = await keyRes.json();
    if (!publicKey) {
      alert('El servidor no tiene configuradas las claves de notificación (VAPID).');
      return;
    }

    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey)
      });
    }

    const r = await fetch('/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sub)
    });
    let data = {};
    try { data = await r.json(); } catch (e) { data = {}; }

    if (r.status === 401) {
      alert('Tu sesión expiró. Vuelve a iniciar sesión y reintenta.');
      return;
    }
    if (data && data.ok) {
      alert('✅ Notificaciones activadas.');
    } else {
      alert('No se guardó la suscripción (' + ((data && data.error) || r.status) + ').');
    }
  }

  async function testPush() {
    const r = await fetch('/push/test', { method: 'POST' });
    let data = {};
    try { data = await r.json(); } catch (e) { data = {}; }

    if (r.status === 401) {
      alert('Tu sesión expiró. Vuelve a iniciar sesión y reintenta.');
      return;
    }
    if (data.sent > 0) {
      alert('✅ Notificación enviada.');
      return;
    }
    if (!data.subs) {
      alert('No hay suscripción guardada. Pulsa "Activar notificaciones" primero.');
      return;
    }
    alert('Tienes ' + data.subs + ' suscripción(es), pero el envío falló. '
          + 'Suele ser un desajuste de claves VAPID en el servidor (revisa los logs).');
  }

  document.addEventListener('DOMContentLoaded', function () {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/static/sw.js').catch(function () {});
    }
    const btnEnable = document.getElementById('btnEnablePush');
    const btnTest = document.getElementById('btnTestPush');
    if (btnEnable) btnEnable.addEventListener('click', enablePush);
    if (btnTest) btnTest.addEventListener('click', testPush);
  });
})();
