// Chat web de Ceiba21 — widget del cliente (burbuja flotante)
(function () {
  'use strict';

  const POLL_MS = 4000;

  let panel, list, input, form, reminder, btnReminder, btnClose, btnChat;
  let lastId = 0;
  let pollTimer = null;
  let isOpen = false;

  function scrollToEnd() {
    if (list) list.scrollTop = list.scrollHeight;
  }

  function addMessage(msg) {
    if (!list) return;
    const isClient = msg.sender === 'client';
    const row = document.createElement('div');
    row.className = 'chat-row ' + (isClient ? 'chat-row--client' : 'chat-row--staff');

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble ' + (isClient ? 'chat-bubble--client' : 'chat-bubble--staff');
    bubble.textContent = msg.body;

    row.appendChild(bubble);
    list.appendChild(row);
    if (msg.id && msg.id > lastId) lastId = msg.id;
    scrollToEnd();
  }

  function showEmptyHint() {
    if (!list || list.children.length > 0) return;
    const hint = document.createElement('div');
    hint.className = 'chat-empty';
    hint.textContent = 'Escríbenos y te respondemos por aquí.';
    list.appendChild(hint);
  }

  function clearEmptyHint() {
    const hint = list ? list.querySelector('.chat-empty') : null;
    if (hint) hint.remove();
  }

  async function loadHistory() {
    try {
      const r = await fetch('/chat/historial');
      const data = await r.json();
      (data.messages || []).forEach(addMessage);
      showEmptyHint();
    } catch (e) {
      showEmptyHint();
    }
  }

  async function poll() {
    try {
      const r = await fetch('/chat/nuevos?after=' + lastId);
      const data = await r.json();
      const msgs = data.messages || [];
      if (msgs.length) {
        clearEmptyHint();
        msgs.forEach(addMessage);
      }
    } catch (e) {
      // Silencioso: el polling reintenta en el siguiente ciclo
    }
  }

  function startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(poll, POLL_MS);
  }

  function stopPolling() {
    if (!pollTimer) return;
    clearInterval(pollTimer);
    pollTimer = null;
  }

  async function sendMessage(text) {
    clearEmptyHint();
    try {
      const r = await fetch('/chat/mensaje', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: text })
      });
      const data = await r.json();
      if (data.ok && data.message) {
        addMessage(data.message);
        maybeShowReminder();
      }
    } catch (e) {
      // El mensaje no salió: se lo indicamos al usuario sin romper el widget
      addMessage({ sender: 'bot', body: 'No pudimos enviar tu mensaje. Reintenta.' });
    }
  }

  // Recordatorio de notificaciones: solo si el navegador aún no decidió
  function maybeShowReminder() {
    if (!reminder) return;
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'default') return;
    if (sessionStorage.getItem('c21_push_reminder_off') === '1') return;
    reminder.style.display = 'flex';
  }

  function hideReminder() {
    if (reminder) reminder.style.display = 'none';
  }

  function openPanel() {
    if (!panel) return;
    isOpen = true;
    panel.style.display = 'flex';
    if (lastId === 0) loadHistory();
    startPolling();
    if (input) input.focus();
    scrollToEnd();
  }

  function closePanel() {
    if (!panel) return;
    isOpen = false;
    panel.style.display = 'none';
    stopPolling();
  }

  document.addEventListener('DOMContentLoaded', function () {
    panel = document.getElementById('chatPanel');
    list = document.getElementById('chatMessages');
    input = document.getElementById('chatInput');
    form = document.getElementById('chatForm');
    reminder = document.getElementById('chatPushReminder');
    btnReminder = document.getElementById('chatEnablePush');
    btnClose = document.getElementById('chatClose');
    btnChat = document.getElementById('btn-chat');

    if (!panel) return;

    // La burbuja "web" abre el chat (antes no hacía nada)
    if (btnChat) {
      btnChat.addEventListener('click', function (e) {
        e.preventDefault();
        if (isOpen) { closePanel(); } else { openPanel(); }
      });
    }

    if (btnClose) btnClose.addEventListener('click', closePanel);

    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        const text = (input.value || '').trim();
        if (!text) return;
        input.value = '';
        sendMessage(text);
      });
    }

    if (btnReminder) {
      btnReminder.addEventListener('click', async function () {
        hideReminder();
        sessionStorage.setItem('c21_push_reminder_off', '1');
        if (window.Ceiba21Push && window.Ceiba21Push.enablePush) {
          await window.Ceiba21Push.enablePush();
        }
      });
    }

    const btnReminderNo = document.getElementById('chatDismissPush');
    if (btnReminderNo) {
      btnReminderNo.addEventListener('click', function () {
        hideReminder();
        sessionStorage.setItem('c21_push_reminder_off', '1');
      });
    }
  });
})();
