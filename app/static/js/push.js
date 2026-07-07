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

    const res = await fetch('/push/vapid-public-key');
    const { publicKey } = await res.json();
    if (!publicKey) {
      alert('El servidor no tiene configuradas las claves de notificación.');
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
    alert(r.ok ? '✅ Notificaciones activadas.' : 'No se pudo guardar la suscripción.');
  }

  async function testPush() {
    const r = await fetch('/push/test', { method: 'POST' });
    const data = await r.json().catch(() => ({}));
    if (!data.sent) {
      alert('No hay suscripción activa. Activa las notificaciones primero.');
    }
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
