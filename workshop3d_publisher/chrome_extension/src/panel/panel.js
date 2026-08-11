const productsEl = document.getElementById('products');
const logsEl = document.getElementById('logs');
let currentState = null;

function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}

function productCard(p) {
  const files = (p.files || []).map((f) => `${f.name} (${f.type})`).join(', ');
  const markets = Object.entries(p.metadata?.publish || {}).filter(([, v]) => v).map(([k]) => k).join(', ');
  const thumbFile = (p.files || []).find((f) => f.name === p.thumbnail);
  const thumb = thumbFile && currentState?.bridgeBaseUrl && currentState?.token
    ? `${currentState.bridgeBaseUrl}/api/products/${encodeURIComponent(p.id)}/file?fileId=${encodeURIComponent(thumbFile.id)}&token=${encodeURIComponent(currentState.token)}`
    : '';
  const perMarket = Object.entries(p.publishState || {}).map(([k, v]) => `${k}: ${v.published ? 'SUCCESS' : `ERROR (${v.error || 'unknown'})`}`).join(' | ');
  return `
  <div class="card">
    <div class="status">${escapeHtml(p.status)}</div>
    <h3>${escapeHtml(p.name)}</h3>
    ${thumb ? `<img class="thumb" src="${thumb}" alt="${escapeHtml(p.name)}" />` : '<div class="small">Brak miniatury</div>'}
    <div class="small">Pliki: ${escapeHtml(files || '-')}</div>
    <div class="small">Marketplace: ${escapeHtml(markets || '-')}</div>
    <div class="small">Wyniki: ${escapeHtml(perMarket || '-')}</div>
    <div class="small">Folder: ${escapeHtml(p.folderPath)}</div>
    <div class="row" style="margin-top:8px;">
      <button data-action="publish" data-id="${p.id}">PUBLIKUJ</button>
      <button data-action="retry" data-id="${p.id}">PONÓW</button>
    </div>
    <div class="row">
      <button data-action="open-cults" data-id="${p.id}">OTWÓRZ STRONĘ</button>
    </div>
  </div>`;
}

function render(state) {
  currentState = state;
  productsEl.innerHTML = (state.products || []).map(productCard).join('');
  logsEl.textContent = (state.logs || []).slice(0, 200).map((l) => `[${l.model}]\n[${l.marketplace}]\n${l.action}\n${l.result}`).join('\n\n');
}

function refresh() {
  chrome.runtime.sendMessage({ type: 'state.get' }, (resp) => render(resp.state));
}

document.getElementById('refresh').addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'products.refresh' }, refresh);
});

document.getElementById('publishAll').addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'publish.all' }, refresh);
});

document.getElementById('diagnose').addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'diagnose.activeTab' }, (resp) => {
    if (!resp?.ok) return;
    const lines = [`URL: ${resp.result.url}`, `TITLE: ${resp.result.title}`, `LOGGED: ${resp.result.isLoggedIn}`,
      `FORMS: ${resp.result.forms.length}`, `INPUTS: ${resp.result.inputs.length}`,
      `TEXTAREAS: ${resp.result.textareas.length}`, `SELECTS: ${resp.result.selects.length}`,
      `BUTTONS: ${resp.result.buttons.length}`, `FILES: ${resp.result.fileUploads.length}`,
      `CONTENTEDITABLE: ${resp.result.contenteditable.length}`
    ];
    logsEl.textContent = `${lines.join('\n')}\n\n${logsEl.textContent}`;
  });
});

productsEl.addEventListener('click', (event) => {
  const btn = event.target.closest('button[data-action]');
  if (!btn) return;
  const productId = btn.dataset.id;
  const action = btn.dataset.action;
  if (action === 'publish' || action === 'retry') {
    chrome.runtime.sendMessage({ type: 'publish.one', payload: { productId } }, refresh);
  }
  if (action === 'open-cults') {
    chrome.tabs.create({ url: 'https://cults3d.com/en/3d-model/new' });
  }
});

chrome.runtime.onMessage.addListener((msg) => {
  if (msg?.type === 'state.updated') render(msg.state);
});

refresh();
