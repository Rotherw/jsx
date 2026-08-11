async function send(type, payload = {}) {
  return chrome.runtime.sendMessage({ type, payload });
}

function $(id) { return document.getElementById(id); }

(async () => {
  const state = await send('GET_STATE');
  $('mode').value = state.mode || 'safe';
})();

$('mode').addEventListener('change', async (e) => {
  await send('SET_MODE', { mode: e.target.value });
  $('status').textContent = `Tryb: ${e.target.value}`;
});

$('openPanel').addEventListener('click', () => {
  chrome.tabs.create({ url: chrome.runtime.getURL('panel/panel.html') });
});

$('sync').addEventListener('click', async () => {
  const res = await send('SYNC_QUEUE');
  $('status').textContent = res.ok ? 'Odświeżono.' : res.error;
});

$('publishAll').addEventListener('click', async () => {
  const res = await send('PUBLISH_ALL');
  $('status').textContent = res.ok ? 'Publikacja uruchomiona.' : res.error;
});

$('saveToken').addEventListener('click', async () => {
  const token = $('token').value.trim();
  if (!token) return;
  await send('SET_BRIDGE_TOKEN', { token, host: '127.0.0.1', port: 17373 });
  $('status').textContent = 'Token zapisany.';
});
