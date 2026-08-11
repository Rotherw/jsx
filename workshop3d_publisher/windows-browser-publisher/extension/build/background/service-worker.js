const MARKETPLACE_URLS = {
  cults: 'https://cults3d.com/en/creations/new',
  thangs: 'https://thangs.com/designer/upload',
  creality: 'https://www.crealitycloud.com/model/upload',
  printables: 'https://www.printables.com/model/new',
  makerworld: 'https://makerworld.com/en/upload',
  myminifactory: 'https://www.myminifactory.com/object/create',
  '3dexport': 'https://3dexport.com/upload'
};

const STATE_KEY = 'publisherState';
const TOKEN_KEY = 'bridgeTokenData';

async function getBridgeTokenData() {
  const stored = await chrome.storage.local.get(TOKEN_KEY);
  if (stored[TOKEN_KEY]) return stored[TOKEN_KEY];
  const tokenUrl = chrome.runtime.getURL('bridge-token.json');
  const cfg = await fetch(tokenUrl).then((r) => r.json());
  await chrome.storage.local.set({ [TOKEN_KEY]: cfg });
  return cfg;
}

async function bridgeFetch(path, options = {}) {
  const tokenData = await getBridgeTokenData();
  const base = `http://${tokenData.host}:${tokenData.port}`;
  const headers = { ...(options.headers || {}), 'x-publisher-token': tokenData.token };
  return fetch(`${base}${path}`, { ...options, headers });
}

async function loadModels() {
  const res = await bridgeFetch('/models');
  if (!res.ok) throw new Error('Bridge offline');
  return res.json();
}

async function getState() {
  const { [STATE_KEY]: state } = await chrome.storage.local.get(STATE_KEY);
  return state || { mode: 'safe', queue: [] };
}

async function setState(next) {
  await chrome.storage.local.set({ [STATE_KEY]: next });
}

async function syncQueue() {
  const state = await getState();
  const data = await loadModels();
  const queue = data.items.map((item) => {
    const old = state.queue.find((q) => q.id === item.id);
    return {
      id: item.id,
      title: item.title,
      model: item,
      status: old?.status || (item.ready ? 'GOTOWE' : 'NOWE'),
      logs: old?.logs || []
    };
  });
  await setState({ ...state, queue });
}

async function ensureTabForMarketplace(marketplace) {
  const url = MARKETPLACE_URLS[marketplace];
  if (!url) throw new Error(`Brak URL dla ${marketplace}`);
  const tabs = await chrome.tabs.query({});
  const existing = tabs.find((t) => t.url && t.url.startsWith(new URL(url).origin));
  if (existing?.id) return existing.id;
  const tab = await chrome.tabs.create({ url, active: true });
  return tab.id;
}


function waitForTabLoaded(tabId) {
  return new Promise((resolve) => {
    const done = (id, info) => {
      if (id === tabId && info.status === 'complete') {
        chrome.tabs.onUpdated.removeListener(done);
        resolve();
      }
    };
    chrome.tabs.onUpdated.addListener(done);
    setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(done);
      resolve();
    }, 12000);
  });
}

async function publishOnMarketplace(item, marketplace, mode) {
  const tabId = await ensureTabForMarketplace(marketplace);
  await chrome.tabs.update(tabId, { active: true });

  await waitForTabLoaded(tabId);
  const response = await chrome.tabs.sendMessage(tabId, {
    type: 'RUN_PUBLISH',
    payload: {
      marketplace,
      model: item.model,
      mode
    }
  });
  if (!response?.ok) {
    throw new Error(response?.error || 'Błąd publikacji content-script');
  }
}

async function updatePublishState(modelId, marketplace, result) {
  await bridgeFetch('/publish-state', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ modelId, marketplace, ...result })
  });
}

async function appendLog(modelName, marketplace, action, result) {
  await bridgeFetch('/log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: modelName, marketplace, action, result })
  });
}

async function runPublishOne(modelId, requestedMarketplace) {
  const state = await getState();
  const item = state.queue.find((q) => q.id === modelId);
  if (!item) throw new Error('Model nie znaleziony');

  item.status = 'PUBLIKOWANIE';
  await setState({ ...state });

  const enabled = item.model?.metadata?.publish || {};
  const marketplaces = requestedMarketplace ? [requestedMarketplace] : Object.keys(enabled).filter((key) => enabled[key]);

  for (const marketplace of marketplaces) {
    try {
      await appendLog(item.title, marketplace, 'Start publish', 'START');
      const mode = (await getState()).mode;
      await publishOnMarketplace(item, marketplace, mode);
      await updatePublishState(item.id, marketplace, { published: true, url: '' });
      item.logs.push(`[${marketplace}] SUCCESS`);
      await appendLog(item.title, marketplace, 'Publish', 'SUCCESS');
    } catch (error) {
      item.logs.push(`[${marketplace}] ERROR: ${error.message}`);
      await appendLog(item.title, marketplace, 'Publish', `ERROR: ${error.message}`);
      await updatePublishState(item.id, marketplace, { published: false, error: error.message });
    }
  }

  item.status = item.logs.some((l) => l.includes('ERROR')) ? 'BŁĄD' : 'OPUBLIKOWANE';
  await setState({ ...state });
}

chrome.runtime.onInstalled.addListener(async () => {
  await syncQueue();
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  (async () => {
    if (message.type === 'GET_STATE') {
      sendResponse(await getState());
      return;
    }
    if (message.type === 'SYNC_QUEUE') {
      await syncQueue();
      sendResponse({ ok: true });
      return;
    }
    if (message.type === 'SET_MODE') {
      const state = await getState();
      state.mode = message.payload.mode === 'auto' ? 'auto' : 'safe';
      await setState(state);
      sendResponse({ ok: true });
      return;
    }
    if (message.type === 'PUBLISH_ONE') {
      await runPublishOne(message.payload.modelId, message.payload.marketplace || null);
      sendResponse({ ok: true });
      return;
    }
    if (message.type === 'PUBLISH_ALL') {
      const state = await getState();
      for (const item of state.queue) {
        if (item.status === 'GOTOWE' || item.status === 'BŁĄD' || item.status === 'NOWE') {
          await runPublishOne(item.id, null);
        }
      }
      sendResponse({ ok: true });
      return;
    }
    if (message.type === 'OPEN_MARKETPLACE') {
      const tabId = await ensureTabForMarketplace(message.payload.marketplace);
      sendResponse({ ok: true, tabId });
      return;
    }
    if (message.type === 'SET_BRIDGE_TOKEN') {
      await chrome.storage.local.set({ [TOKEN_KEY]: message.payload });
      sendResponse({ ok: true });
      return;
    }
  })().catch((error) => sendResponse({ ok: false, error: error.message }));
  return true;
});
