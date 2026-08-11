(() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const queryByText = (root, selectors, textMatchers = []) => {
    const nodes = root.querySelectorAll(selectors);
    for (const n of nodes) {
      const text = (n.innerText || n.textContent || '').trim().toLowerCase();
      if (textMatchers.some((m) => text.includes(m.toLowerCase()))) return n;
    }
    return null;
  };

  const findField = (root, hints) => {
    const candidates = root.querySelectorAll('input,textarea,select,[contenteditable="true"]');
    for (const node of candidates) {
      const attrs = [
        node.getAttribute('name'),
        node.getAttribute('aria-label'),
        node.getAttribute('placeholder'),
        node.getAttribute('data-testid'),
        node.id,
        node.getAttribute('role')
      ].filter(Boolean).join(' ').toLowerCase();
      if (hints.some((h) => attrs.includes(h.toLowerCase()))) return node;
      if (node.id) {
        const label = root.querySelector(`label[for="${node.id}"]`);
        if (label) {
          const text = (label.textContent || '').toLowerCase();
          if (hints.some((h) => text.includes(h.toLowerCase()))) return node;
        }
      }
    }
    return null;
  };

  const setNativeValue = (el, value) => {
    if (!el) return false;
    if (el.tagName === 'SELECT') {
      const options = [...el.options];
      const opt = options.find((o) => (o.textContent || '').toLowerCase().includes(String(value).toLowerCase())) ||
        options.find((o) => String(o.value).toLowerCase() === String(value).toLowerCase());
      if (opt) el.value = opt.value;
      else el.value = value;
    } else if (el.isContentEditable) {
      el.focus();
      el.innerText = value;
    } else if (el.type === 'checkbox' || el.type === 'radio') {
      el.checked = Boolean(value);
    } else {
      const proto = Object.getPrototypeOf(el);
      const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
      if (descriptor?.set) descriptor.set.call(el, value);
      else el.value = value;
    }
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  };

  const observeUntil = (predicate, timeoutMs = 15000) => new Promise((resolve) => {
    const ok = predicate();
    if (ok) return resolve(ok);
    const obs = new MutationObserver(() => {
      const got = predicate();
      if (got) {
        obs.disconnect();
        resolve(got);
      }
    });
    obs.observe(document.documentElement, { childList: true, subtree: true, attributes: true });
    setTimeout(() => {
      obs.disconnect();
      resolve(predicate() || null);
    }, timeoutMs);
  });

  window.W3D_DOM = { sleep, queryByText, findField, setNativeValue, observeUntil };
})();
