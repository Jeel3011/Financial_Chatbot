'use strict';

const form = document.getElementById('chat-form');
const input = document.getElementById('question-input');
const sendBtn = document.getElementById('send-btn');
const messages = document.getElementById('messages');

// ── Helpers ────────────────────────────────────────────────────────────────

function scrollBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function addMessage(role, text, sql = '') {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? '🧑' : '🤖';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;

  // Attach SQL disclosure if present
  if (sql && role === 'assistant') {
    const toggle = document.createElement('button');
    toggle.className = 'sql-toggle';
    toggle.textContent = '▶ Show SQL';

    const sqlBlock = document.createElement('pre');
    sqlBlock.className = 'sql-block';
    sqlBlock.textContent = sql;

    toggle.addEventListener('click', () => {
      const visible = sqlBlock.classList.toggle('visible');
      toggle.textContent = visible ? '▼ Hide SQL' : '▶ Show SQL';
    });

    bubble.appendChild(document.createElement('br'));
    bubble.appendChild(toggle);
    bubble.appendChild(sqlBlock);
  }

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  messages.appendChild(wrapper);
  scrollBottom();
  return wrapper;
}

function addThinking() {
  const wrapper = document.createElement('div');
  wrapper.className = 'message assistant thinking';

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = '🤖';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';

  const span = document.createElement('span');
  span.className = 'dot-anim';
  span.textContent = 'Thinking';
  bubble.appendChild(span);

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  messages.appendChild(wrapper);
  scrollBottom();
  return wrapper;
}

function setLoading(loading) {
  sendBtn.disabled = loading;
  input.disabled = loading;
}

// ── Chat submission ─────────────────────────────────────────────────────────

async function submitQuestion(question) {
  if (!question.trim()) return;

  addMessage('user', question);
  input.value = '';
  setLoading(true);

  const thinking = addThinking();

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      thinking.remove();
      addMessage('assistant', `⚠️ Error: ${err.detail || res.statusText}`);
      return;
    }

    const data = await res.json();
    thinking.remove();
    addMessage('assistant', data.answer, data.sql);
  } catch (err) {
    thinking.remove();
    addMessage('assistant', `⚠️ Network error: ${err.message}`);
  } finally {
    setLoading(false);
    input.focus();
  }
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  submitQuestion(input.value);
});

// ── Quick-suggestion buttons ────────────────────────────────────────────────

document.querySelectorAll('.suggestion').forEach((btn) => {
  btn.addEventListener('click', () => {
    const q = btn.dataset.q;
    if (q) submitQuestion(q);
  });
});

// ── Initial focus ───────────────────────────────────────────────────────────
input.focus();
