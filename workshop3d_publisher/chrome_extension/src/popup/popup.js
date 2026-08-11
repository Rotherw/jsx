const bridgeBaseUrl = document.getElementById('bridgeBaseUrl');
const token = document.getElementById('token');
const safeMode = document.getElementById('safeMode');
const statusEl = document.getElementById('status');

function status(text) { statusEl.textContent = text; }

chrome.runtime.sendMessage({ type: 'state.get' }, (resp) => {
  const st = resp?.state;
  if (!st) return;
  bridgeBaseUrl.value = st.bridgeBaseUrl || bridgeBaseUrl.value;
  token.value = st.token || '';
  safeMode.checked = st.safeMode !== false;
});

document.getElementById('save').addEventListener('click', () => {
  chrome.runtime.sendMessage({
    type: 'settings.save',
    payload: { bridgeBaseUrl: bridgeBaseUrl.value.trim(), token: token.value.trim(), safeMode: safeMode.checked }
  }, (resp) => status(resp?.ok ? 'Połączono z bridge.' : `Błąd: ${resp?.error || 'unknown'}`));
});

document.getElementById('openPanel').addEventListener('click', () => {
  chrome.tabs.create({ url: chrome.runtime.getURL('panel/panel.html') });
});

document.getElementById('refresh').addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'products.refresh' }, (resp) => status(resp?.ok ? 'Odświeżono produkty.' : `Błąd: ${resp?.error || 'unknown'}`));
});
