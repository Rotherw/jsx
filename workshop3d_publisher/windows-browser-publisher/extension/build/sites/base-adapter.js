(() => {
  class BaseMarketplaceAdapter {
    constructor(name) {
      this.name = name;
      this.fallbackTimeout = 15000;
    }

    detectPage() { return false; }
    isLoggedIn() { return true; }
    async openPublisher() {}
    async fillTitle() {}
    async fillDescription() {}
    async fillTags() {}
    async fillCategory() {}
    async fillLicense() {}
    async fillPrice() {}
    async uploadModelFiles() {}
    async uploadImages() {}
    async setCollection() {}
    async validateForm() { return true; }
    async publish() {}
    async getResult() { return { success: true, url: location.href }; }

    async waitForElement(selectors) {
      const arr = Array.isArray(selectors) ? selectors : [selectors];
      const start = Date.now();
      while (Date.now() - start < this.fallbackTimeout) {
        for (const sel of arr) {
          const el = document.querySelector(sel);
          if (el) return el;
        }
        await new Promise((r) => setTimeout(r, 250));
      }
      return null;
    }

    findBySemantic({ labels = [], placeholders = [], names = [], aria = [], role = '', testIds = [] }) {
      const lc = (v) => (v || '').toLowerCase();
      const inputs = Array.from(document.querySelectorAll('input,textarea,select,[contenteditable="true"],[role="textbox"]'));
      const scored = [];
      for (const input of inputs) {
        const scoreText = [
          input.name,
          input.id,
          input.getAttribute('placeholder'),
          input.getAttribute('aria-label'),
          input.getAttribute('data-testid'),
          (input.labels || []).length ? Array.from(input.labels).map((l) => l.textContent).join(' ') : '',
          input.closest('label')?.textContent || ''
        ].join(' ').toLowerCase();

        let score = 0;
        for (const t of labels) if (scoreText.includes(lc(t))) score += 4;
        for (const t of placeholders) if (scoreText.includes(lc(t))) score += 3;
        for (const t of names) if (scoreText.includes(lc(t))) score += 2;
        for (const t of aria) if (scoreText.includes(lc(t))) score += 2;
        for (const t of testIds) if (scoreText.includes(lc(t))) score += 3;
        if (role && (input.getAttribute('role') || '').toLowerCase() === role.toLowerCase()) score += 2;
        if (score > 0) scored.push({ input, score });
      }
      scored.sort((a, b) => b.score - a.score);
      return scored[0]?.input || null;
    }

    setNativeValue(el, value) {
      if (!el) return false;
      const prototype = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
      const descriptor = Object.getOwnPropertyDescriptor(prototype, 'value');
      descriptor?.set?.call(el, value);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }

    async fillTextField(semantic, fallbackSelectors, value) {
      let field = this.findBySemantic(semantic);
      if (!field) field = await this.waitForElement(fallbackSelectors);
      if (!field) throw new Error(`Nie znaleziono pola: ${JSON.stringify(semantic)}`);
      if (field.isContentEditable) {
        field.focus();
        field.innerText = value;
        field.dispatchEvent(new Event('input', { bubbles: true }));
        field.dispatchEvent(new Event('change', { bubbles: true }));
        return;
      }
      this.setNativeValue(field, value);
    }

    async uploadViaInput(semantic, fallbackSelectors, files) {
      let input = this.findBySemantic(semantic);
      if (!input) input = await this.waitForElement(fallbackSelectors);
      if (!input || input.type !== 'file') return false;

      const dt = new DataTransfer();
      files.forEach((f) => dt.items.add(f));
      input.files = dt.files;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }

    async uploadViaDropzone(dropSelectors, files) {
      const zone = await this.waitForElement(dropSelectors);
      if (!zone) return false;
      const dt = new DataTransfer();
      files.forEach((f) => dt.items.add(f));

      ['dragenter', 'dragover', 'drop'].forEach((type) => {
        const event = new DragEvent(type, { bubbles: true, cancelable: true, dataTransfer: dt });
        zone.dispatchEvent(event);
      });
      return true;
    }

    waitForSpaFormRefresh() {
      return new Promise((resolve) => {
        const observer = new MutationObserver(() => resolve());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => {
          observer.disconnect();
          resolve();
        }, 1200);
      });
    }

    async waitForUploadComplete() {
      const start = Date.now();
      while (Date.now() - start < 120000) {
        const busy = document.querySelector('[aria-busy="true"], .uploading, [data-uploading="true"]');
        if (!busy) return true;
        await new Promise((r) => setTimeout(r, 500));
      }
      return false;
    }

    findButtonByText(texts) {
      const buttons = Array.from(document.querySelectorAll('button, [role="button"], input[type="submit"]'));
      const words = texts.map((t) => t.toLowerCase());
      return buttons.find((btn) => words.some((t) => (btn.textContent || btn.value || '').toLowerCase().includes(t))) || null;
    }
  }

  window.BaseMarketplaceAdapter = BaseMarketplaceAdapter;
})();
