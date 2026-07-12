// Chat web de Ceiba21 — widget del cliente (burbuja flotante)
(function () {
  'use strict';

  const POLL_MS = 4000;

  let panel, list, input, form, reminder, btnReminder, btnClose, btnChat;
  let lastId = 0;
  let pollTimer = null;
  let isOpen = false;
  let typingSentAt = 0;

  function setTypingIndicator(on) {
    if (!list) return;
    let el = list.querySelector('.chat-typing');
    if (on && !el) {
      el = document.createElement('div');
      el.className = 'chat-row chat-row--staff chat-typing';
      el.innerHTML = '<div class="chat-bubble chat-bubble--staff chat-dots">'
                   + '<span></span><span></span><span></span></div>';
      list.appendChild(el);
      list.scrollTop = list.scrollHeight;
    } else if (!on && el) {
      el.remove();
    }
  }

  // Avisa al servidor que el cliente escribe (como mucho 1 vez cada 3 s)
  function notifyTyping() {
    const now = Date.now();
    if (now - typingSentAt < 3000) return;
    typingSentAt = now;
    fetch('/chat/typing', { method: 'POST' }).catch(function () {});
  }

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
    const dots = list.querySelector('.chat-typing');
    if (dots) { list.insertBefore(row, dots); } else { list.appendChild(row); }

    if (msg.buttons && msg.buttons.length) renderButtons(msg.buttons);

    if (msg.id && msg.id > lastId) lastId = msg.id;
    scrollToEnd();
  }

  // Botones del bot: fila de "chips". Al pulsar uno se envía su callback_data.
  function renderButtons(rows) {
    const wrap = document.createElement('div');
    wrap.className = 'chat-btns';
    rows.forEach(function (row) {
      (row || []).forEach(function (btn) {
        if (btn.url) {
          const a = document.createElement('a');
          a.className = 'chat-chip';
          a.href = btn.url;
          a.target = '_blank';
          a.rel = 'noopener';
          a.textContent = btn.text;
          wrap.appendChild(a);
        } else if (btn.callback_data) {
          const b = document.createElement('button');
          b.type = 'button';
          b.className = 'chat-chip';
          b.textContent = btn.text;
          b.addEventListener('click', function () {
            disableButtons(wrap);
            sendMessage(btn.callback_data, btn.text);
          });
          wrap.appendChild(b);
        }
      });
    });
    const dots = list.querySelector('.chat-typing');
    if (dots) { list.insertBefore(wrap, dots); } else { list.appendChild(wrap); }
  }

  function disableButtons(wrap) {
    wrap.querySelectorAll('button').forEach(function (b) {
      b.disabled = true;
      b.classList.add('chat-chip--off');
    });
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
        setTypingIndicator(false);
        msgs.forEach(addMessage);
      }
      setTypingIndicator(!!data.typing);
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

  async function sendMessage(text, label) {
    clearEmptyHint();
    try {
      const r = await fetch('/chat/mensaje', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: text })
      });
      const data = await r.json();
      if (data.ok && data.message) {
        // Si vino de un botón, mostramos su etiqueta y no el callback_data
        if (label) data.message.body = label;
        addMessage(data.message);
        (data.bot_messages || []).forEach(addMessage);
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

    if (input) {
      input.addEventListener('input', notifyTyping);
    }

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
