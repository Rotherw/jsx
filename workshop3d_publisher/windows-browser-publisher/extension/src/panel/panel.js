function send(type, payload = {}) {
  return chrome.runtime.sendMessage({ type, payload });
}

function escapeHtml(text) {
  return (text || '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}

async function render() {
  const state = await send('GET_STATE');
  const list = document.getElementById('list');
  list.innerHTML = '';

  for (const item of state.queue || []) {
    const thumb = item.model?.imageFiles?.[0];
    const marketplaces = Object.entries(item.model?.metadata?.publish || {})
      .filter(([, enabled]) => enabled)
      .map(([key]) => key)
      .join(', ');

    const div = document.createElement('div');
    div.className = 'card';
    div.innerHTML = `
      <div class="row">
        <div>
          ${thumb ? `<img class="thumb" src="http://127.0.0.1:17373/model-file?modelId=${encodeURIComponent(item.id)}&file=${encodeURIComponent(thumb.relativePath)}" />` : ''}
        </div>
        <div class="meta">
          <h3>${escapeHtml(item.title)}</h3>
          <div class="status">Status: ${escapeHtml(item.status)}</div>
          <div>Marketplace: ${escapeHtml(marketplaces)}</div>
          <div>Pliki: ${(item.model?.files || []).map((f) => escapeHtml(f.name)).join(', ')}</div>
          <div class="actions">
            <button data-action="publish" data-id="${item.id}">PUBLIKUJ</button>
            <button data-action="retry" data-id="${item.id}">PONÓW</button>
            <button data-action="open" data-id="${item.id}">OTWÓRZ STRONĘ</button>
          </div>
          <pre>${(item.logs || []).map(escapeHtml).join('\n')}</pre>
        </div>
      </div>
    `;
    list.appendChild(div);
  }

  list.querySelectorAll('button[data-action="publish"]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      await send('PUBLISH_ONE', { modelId: btn.dataset.id });
      await render();
    });
  });

  list.querySelectorAll('button[data-action="retry"]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      await send('PUBLISH_ONE', { modelId: btn.dataset.id });
      await render();
    });
  });

  list.querySelectorAll('button[data-action="open"]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const stateNow = await send('GET_STATE');
      const item = stateNow.queue.find((x) => x.id === btn.dataset.id);
      const marketplaces = Object.entries(item.model.metadata.publish).filter(([, enabled]) => enabled);
      if (marketplaces[0]) {
        await send('OPEN_MARKETPLACE', { marketplace: marketplaces[0][0] });
      }
    });
  });
}

document.getElementById('refresh').addEventListener('click', async () => {
  await send('SYNC_QUEUE');
  await render();
});

document.getElementById('publishAll').addEventListener('click', async () => {
  await send('PUBLISH_ALL');
  await render();
});

document.getElementById('diagnose').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  const out = await chrome.tabs.sendMessage(tab.id, { type: 'DIAGNOSE_PAGE' });
  alert(JSON.stringify(out, null, 2));
});

render();
