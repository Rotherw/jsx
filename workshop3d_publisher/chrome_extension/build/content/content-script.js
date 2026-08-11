(() => {
  const adapterByMarketplace = (marketplace) => window.Workshop3DAdapters?.[marketplace] || null;

  async function runPublish({ marketplace, product, runtime }) {
    const adapter = adapterByMarketplace(marketplace);
    if (!adapter) {
      return { success: false, error: `Adapter not found: ${marketplace}`, logs: [] };
    }

    adapter.logs = [];
    if (!adapter.detectPage()) {
      return { success: false, error: `Wrong page for ${marketplace}`, logs: adapter.logs };
    }

    const waitForm = () => document.querySelector('form,input,textarea,select,[contenteditable="true"]');
    await window.W3D_DOM.observeUntil(waitForm, 20000);

    if (!adapter.isLoggedIn()) {
      adapter.log(product.name, 'Check login', 'ERROR: not logged in');
      return { success: false, error: 'not logged in', logs: adapter.logs };
    }

    adapter.fillTitle(product);
    adapter.fillDescription(product);
    adapter.fillTags(product);
    adapter.fillCategory(product);
    adapter.fillLicense(product);
    adapter.fillPrice(product);
    adapter.setCollection(product);
    await adapter.uploadModelFiles(product, runtime);
    await adapter.uploadImages(product, runtime);

    const isValid = adapter.validateForm(product);
    if (!isValid) return { success: false, error: 'form validation failed', logs: adapter.logs };

    if (!runtime.safeMode) {
      const clicked = adapter.publish();
      adapter.log(product.name, 'Click publish', clicked ? 'SUCCESS' : 'ERROR: publish button not found');
    } else {
      adapter.log(product.name, 'Safe mode', 'SUCCESS: stopped before Publish click');
    }

    return adapter.getResult();
  }

  function diagnosePage() {
    const forms = [...document.querySelectorAll('form')].map((f, idx) => ({
      index: idx,
      action: f.getAttribute('action') || '',
      id: f.id || null,
      classes: f.className || ''
    }));
    const toList = (selector) => [...document.querySelectorAll(selector)].slice(0, 100).map((e) => ({
      tag: e.tagName.toLowerCase(),
      name: e.getAttribute('name') || null,
      id: e.id || null,
      ariaLabel: e.getAttribute('aria-label') || null,
      placeholder: e.getAttribute('placeholder') || null,
      type: e.getAttribute('type') || null,
      role: e.getAttribute('role') || null,
      text: (e.innerText || e.textContent || '').trim().slice(0, 120)
    }));

    const loginHeuristics = !window.W3D_DOM.queryByText(document, 'a,button', ['sign in', 'log in', 'zaloguj']);

    return {
      url: location.href,
      title: document.title,
      isLoggedIn: loginHeuristics,
      forms,
      inputs: toList('input'),
      textareas: toList('textarea'),
      selects: toList('select'),
      buttons: toList('button,[role="button"],input[type="submit"]'),
      fileUploads: toList('input[type="file"]'),
      contenteditable: toList('[contenteditable="true"]')
    };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.type === 'publisher.run') {
      runPublish(msg.payload).then(sendResponse).catch((err) => sendResponse({ success: false, error: String(err), logs: [] }));
      return true;
    }
    if (msg?.type === 'publisher.diagnose') {
      sendResponse(diagnosePage());
    }
    return false;
  });
})();
