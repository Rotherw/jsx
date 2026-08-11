const DEFAULT_SETTINGS = {
  bridgeBaseUrl: 'http://127.0.0.1:18777',
  token: '',
  safeMode: true,
  queue: [],
  products: [],
  logs: []
};

const MARKETPLACES = {
  cults: { domain: 'cults3d.com', publishUrl: 'https://cults3d.com/en/3d-model/new' },
  thangs: { domain: 'thangs.com', publishUrl: 'https://thangs.com/upload' },
  creality: { domain: 'crealitycloud.com', publishUrl: 'https://www.crealitycloud.com/creator/upload' },
  printables: { domain: 'printables.com', publishUrl: 'https://www.printables.com/model/new' },
  makerworld: { domain: 'makerworld.com', publishUrl: 'https://makerworld.com/en/models/upload' },
  myminifactory: { domain: 'myminifactory.com', publishUrl: 'https://www.myminifactory.com/users/upload' },
  '3dexport': { domain: '3dexport.com', publishUrl: 'https://3dexport.com/upload-model' }
};

let state = { ...DEFAULT_SETTINGS };
let running = false;
let ws = null;

const saveState = async () => chrome.storage.local.set({ publisherState: state });
const loadState = async () => {
  const stored = await chrome.storage.local.get('publisherState');
  state = { ...DEFAULT_SETTINGS, ...(stored.publisherState || {}) };
};

const emitUpdate = async () => {
  await saveState();
  chrome.runtime.sendMessage({ type: 'state.updated', state }).catch(() => {});
};

const bridgeHeaders = () => ({ 'x-publisher-token': state.token, 'content-type': 'application/json' });

async function bridgeGet(path) {
  const res = await fetch(`${state.bridgeBaseUrl}${path}`, { headers: { 'x-publisher-token': state.token } });
  if (!res.ok) throw new Error(`Bridge ${path} failed: ${res.status}`);
  return res.json();
}

async function bridgePost(path, body) {
  const res = await fetch(`${state.bridgeBaseUrl}${path}`, { method: 'POST', headers: bridgeHeaders(), body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`Bridge ${path} failed: ${res.status}`);
  return res.json();
}

function mapProductStatus(p) {
  const vals = Object.values(p.publishState || {});
  const hasError = vals.some((s) => s && s.published === false && s.error);
  const hasSuccess = vals.some((s) => s && s.published);
  const inQueue = state.queue.some((q) => q.productId === p.id && q.status === 'PUBLIKOWANIE');
  if (inQueue) return 'PUBLIKOWANIE';
  if (hasError) return 'BŁĄD';
  if (hasSuccess) return 'OPUBLIKOWANE';
  return p.validation?.ready ? 'GOTOWE' : 'NOWE';
}

async function loadProductsFromBridge() {
  if (!state.token) return;
  const products = await bridgeGet('/api/products');
  state.products = products.map((p) => ({ ...p, status: mapProductStatus(p) }));
  await emitUpdate();
}

function pushLog(entry) {
  state.logs.unshift({ ...entry, date: new Date().toISOString() });
  state.logs = state.logs.slice(0, 500);
}

async function logToBridge(model, marketplace, action, result) {
  pushLog({ model, marketplace, action, result });
  await emitUpdate();
  if (!state.token) return;
  try {
    await bridgePost('/api/logs', { model, marketplace, action, result });
  } catch {}
}

async function ensureTab(urlPart, createUrl) {
  const tabs = await chrome.tabs.query({});
  const existing = tabs.find((t) => t.url && t.url.includes(urlPart));
  if (existing) {
    await chrome.tabs.update(existing.id, { active: true, url: createUrl });
    return existing;
  }
  return chrome.tabs.create({ url: createUrl, active: true });
}

async function runJob(job) {
  const { productId, marketplace } = job;
  const product = state.products.find((p) => p.id === productId);
  if (!product) throw new Error('product not found');

  const marketplaceInfo = MARKETPLACES[marketplace];
  if (!marketplaceInfo) throw new Error(`unknown marketplace ${marketplace}`);

  await logToBridge(product.name, marketplaceInfo.domain, 'Open publisher page', 'START');
  const tab = await ensureTab(marketplaceInfo.domain, marketplaceInfo.publishUrl);
  await chrome.tabs.update(tab.id, { url: marketplaceInfo.publishUrl });

  await new Promise((resolve) => setTimeout(resolve, 3500));

  const response = await chrome.tabs.sendMessage(tab.id, {
    type: 'publisher.run',
    payload: {
      marketplace,
      product,
      runtime: {
        bridgeBaseUrl: state.bridgeBaseUrl,
        token: state.token,
        safeMode: state.safeMode
      }
    }
  });

  const ok = Boolean(response?.success);
  if (response?.logs?.length) {
    for (const line of response.logs) {
      await logToBridge(line.model, line.marketplace, line.action, line.result);
    }
  }

  await bridgePost(`/api/products/${encodeURIComponent(productId)}/publish-state`, {
    marketplace,
    published: ok,
    url: response?.url || null,
    error: ok ? null : response?.error || 'unknown error'
  });

  await logToBridge(product.name, marketplaceInfo.domain, ok ? 'Publish flow' : 'Publish flow', ok ? 'SUCCESS' : `ERROR: ${response?.error || 'unknown'}`);
}

async function processQueue() {
  if (running) return;
  running = true;
  while (state.queue.length) {
    const item = state.queue[0];
    item.status = 'PUBLIKOWANIE';
    await emitUpdate();
    try {
      await runJob(item);
      item.status = 'OPUBLIKOWANE';
    } catch (err) {
      item.status = 'BŁĄD';
      pushLog({ model: item.productName, marketplace: item.marketplace, action: 'Queue item', result: `ERROR: ${err.message}` });
    }
    state.queue.shift();
    await loadProductsFromBridge();
    await emitUpdate();
  }
  running = false;
}

async function connectWs() {
  if (ws) ws.close();
  if (!state.token) return;
  ws = new WebSocket(`${state.bridgeBaseUrl.replace('http', 'ws')}/ws?token=${encodeURIComponent(state.token)}`);
  ws.onmessage = async (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === 'products.updated') {
      state.products = payload.products.map((p) => ({ ...p, status: mapProductStatus(p) }));
      await emitUpdate();
    }
  };
  ws.onerror = () => {};
}

chrome.runtime.onInstalled.addListener(async () => {
  await loadState();
  await emitUpdate();
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    if (msg?.type === 'state.get') {
      await loadState();
      sendResponse({ state });
      return;
    }

    if (msg?.type === 'settings.save') {
      state.bridgeBaseUrl = msg.payload.bridgeBaseUrl || state.bridgeBaseUrl;
      state.token = msg.payload.token || state.token;
      state.safeMode = Boolean(msg.payload.safeMode);
      await connectWs();
      await loadProductsFromBridge();
      sendResponse({ ok: true, state });
      return;
    }

    if (msg?.type === 'products.refresh') {
      await loadProductsFromBridge();
      sendResponse({ ok: true, products: state.products });
      return;
    }

    if (msg?.type === 'publish.one') {
      const p = state.products.find((x) => x.id === msg.payload.productId);
      if (!p) throw new Error('product not found');
      const targets = Object.entries(p.metadata.publish || {})
        .filter(([_, enabled]) => enabled)
        .map(([k]) => k);
      for (const market of targets) {
        if (p.publishState?.[market]?.published) continue;
        state.queue.push({ productId: p.id, productName: p.name, marketplace: market, status: 'NOWE' });
      }
      await emitUpdate();
      processQueue();
      sendResponse({ ok: true });
      return;
    }

    if (msg?.type === 'publish.marketplace') {
      const p = state.products.find((x) => x.id === msg.payload.productId);
      if (!p) throw new Error('product not found');
      state.queue.push({ productId: p.id, productName: p.name, marketplace: msg.payload.marketplace, status: 'NOWE' });
      await emitUpdate();
      processQueue();
      sendResponse({ ok: true });
      return;
    }

    if (msg?.type === 'publish.all') {
      for (const p of state.products.filter((x) => x.validation?.ready)) {
        const targets = Object.entries(p.metadata.publish || {}).filter(([_, enabled]) => enabled).map(([k]) => k);
        for (const market of targets) {
          if (p.publishState?.[market]?.published) continue;
          state.queue.push({ productId: p.id, productName: p.name, marketplace: market, status: 'NOWE' });
        }
      }
      await emitUpdate();
      processQueue();
      sendResponse({ ok: true });
      return;
    }

    if (msg?.type === 'diagnose.activeTab') {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.id) throw new Error('active tab not found');
      const result = await chrome.tabs.sendMessage(tab.id, { type: 'publisher.diagnose' });
      sendResponse({ ok: true, result });
      return;
    }
  })().catch((error) => sendResponse({ ok: false, error: error.message }));
  return true;
});

setInterval(() => {
  loadProductsFromBridge().catch(() => {});
}, 12000);
