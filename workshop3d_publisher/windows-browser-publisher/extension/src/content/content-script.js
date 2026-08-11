async function getBridgeTokenData() {
  const data = await chrome.storage.local.get('bridgeTokenData');
  if (data.bridgeTokenData) return data.bridgeTokenData;
  const cfg = await fetch(chrome.runtime.getURL('bridge-token.json')).then((r) => r.json());
  await chrome.storage.local.set({ bridgeTokenData: cfg });
  return cfg;
}

async function bridgeFetch(path) {
  const cfg = await getBridgeTokenData();
  const base = `http://${cfg.host}:${cfg.port}`;
  return fetch(`${base}${path}`, {
    headers: { 'x-publisher-token': cfg.token }
  });
}

async function downloadModelFiles(modelId, files) {
  const out = [];
  for (const file of files) {
    const res = await bridgeFetch(`/model-file?modelId=${encodeURIComponent(modelId)}&file=${encodeURIComponent(file.relativePath)}`);
    if (!res.ok) continue;
    const blob = await res.blob();
    out.push(new File([blob], file.name, { type: blob.type || 'application/octet-stream' }));
  }
  return out;
}

async function publishWithAdapter(payload) {
  const { marketplace, model, mode } = payload;
  const adapter = window.SiteRegistry.getAdapterByMarketplace(marketplace) || window.SiteRegistry.detectAdapter();
  if (!adapter) throw new Error(`Brak adaptera: ${marketplace}`);
  if (!adapter.detectPage()) {
    throw new Error(`Nieobsługiwana strona dla ${marketplace}`);
  }
  if (!adapter.isLoggedIn()) {
    throw new Error(`Brak zalogowanej sesji na ${marketplace}`);
  }

  await adapter.openPublisher();

  const metadata = model.metadata || {};
  const modelFiles = await downloadModelFiles(model.id, model.modelFiles || []);
  const imageFiles = await downloadModelFiles(model.id, model.imageFiles || []);

  await adapter.fillTitle(metadata);
  await adapter.fillDescription(metadata);
  await adapter.fillTags(metadata);
  await adapter.fillCategory(metadata);
  await adapter.fillLicense(metadata);
  await adapter.fillPrice(metadata);
  await adapter.uploadModelFiles(metadata, modelFiles);
  await adapter.uploadImages(metadata, imageFiles);
  await adapter.setCollection(metadata);

  const valid = await adapter.validateForm();
  if (!valid) throw new Error('Formularz nie jest gotowy do publikacji');

  await adapter.publish(mode);
  return adapter.getResult();
}

function summarizeElements(selector, limit = 30) {
  return Array.from(document.querySelectorAll(selector)).slice(0, limit).map((el) => ({
    tag: el.tagName,
    name: el.getAttribute('name') || '',
    id: el.id || '',
    type: el.getAttribute('type') || '',
    role: el.getAttribute('role') || '',
    ariaLabel: el.getAttribute('aria-label') || '',
    placeholder: el.getAttribute('placeholder') || '',
    testId: el.getAttribute('data-testid') || '',
    text: (el.textContent || '').trim().slice(0, 120)
  }));
}

function diagnosePage() {
  const adapter = window.SiteRegistry.detectAdapter();
  return {
    url: location.href,
    title: document.title,
    adapter: adapter?.name || null,
    loggedIn: adapter ? adapter.isLoggedIn() : null,
    forms: summarizeElements('form', 15),
    inputs: summarizeElements('input'),
    textarea: summarizeElements('textarea'),
    selects: summarizeElements('select'),
    buttons: summarizeElements('button,[role="button"],input[type="submit"]'),
    fileUpload: summarizeElements('input[type="file"]'),
    contenteditable: summarizeElements('[contenteditable="true"]')
  };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  (async () => {
    if (message.type === 'RUN_PUBLISH') {
      const result = await publishWithAdapter(message.payload);
      sendResponse({ ok: true, result });
      return;
    }
    if (message.type === 'DIAGNOSE_PAGE') {
      sendResponse(diagnosePage());
      return;
    }
  })().catch((error) => sendResponse({ ok: false, error: error.message }));
  return true;
});
