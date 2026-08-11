(() => {
  class CultsAdapter extends window.BaseMarketplaceAdapter {
    constructor() { super('cults'); }

    detectPage() { return /cults3d\.com/.test(location.hostname); }

    isLoggedIn() {
      return !document.querySelector('a[href*="/users/sign_in"], a[href*="/login"]');
    }

    async openPublisher() {
      if (!/\/creations\/new/.test(location.pathname)) {
        location.href = 'https://cults3d.com/en/creations/new';
        await this.waitForSpaFormRefresh();
      }
    }

    async fillTitle(metadata) {
      await this.fillTextField(
        { labels: ['title', 'name', 'nazwa', 'tytuł'], placeholders: ['title'] },
        ['input[name*="title"]', 'input[placeholder*="Title"]', 'input[id*="title"]'],
        metadata.title
      );
    }

    async fillDescription(metadata) {
      await this.fillTextField(
        { labels: ['description', 'opis'], placeholders: ['description'] },
        ['textarea[name*="description"]', '[contenteditable="true"]'],
        metadata.description || ''
      );
    }

    async fillTags(metadata) {
      if (!Array.isArray(metadata.tags) || !metadata.tags.length) return;
      const tags = metadata.tags.join(', ');
      await this.fillTextField(
        { labels: ['tags', 'keywords'], placeholders: ['tag'] },
        ['input[name*="tag"]', 'input[placeholder*="tag"]'],
        tags
      );
    }

    async fillCategory(metadata) {
      if (!metadata.category) return;
      const select = this.findBySemantic({ labels: ['category', 'kategoria'], names: ['category'] }) ||
        await this.waitForElement(['select[name*="category"]']);
      if (!select) return;
      for (const option of Array.from(select.options || [])) {
        if (option.textContent.toLowerCase().includes(metadata.category.toLowerCase())) {
          select.value = option.value;
          select.dispatchEvent(new Event('change', { bubbles: true }));
          return;
        }
      }
    }

    async fillLicense(metadata) {
      if (!metadata.license) return;
      await this.fillTextField(
        { labels: ['license', 'licence'], placeholders: ['license'] },
        ['input[name*="license"]'],
        metadata.license
      );
    }

    async fillPrice(metadata) {
      if (metadata.price == null || metadata.price === '') return;
      await this.fillTextField(
        { labels: ['price', 'cena'], names: ['price'] },
        ['input[name*="price"]'],
        String(metadata.price)
      );
    }

    async setCollection(metadata) {
      if (!metadata.collection) return;
      await this.fillTextField(
        { labels: ['collection'], names: ['collection'] },
        ['input[name*="collection"]'],
        metadata.collection
      );
    }

    async uploadModelFiles(_metadata, files) {
      const done = await this.uploadViaInput(
        { labels: ['3d file', 'stl', 'model'], names: ['file'] },
        ['input[type="file"][accept*=".stl"]', 'input[type="file"]'],
        files
      );
      if (!done) {
        const dropped = await this.uploadViaDropzone(['[data-testid*="drop"]', '.dropzone', '[class*="drop"]'], files);
        if (!dropped) throw new Error('Brak pola uploadu modelu');
      }
      await this.waitForUploadComplete();
    }

    async uploadImages(_metadata, files) {
      const done = await this.uploadViaInput(
        { labels: ['image', 'thumbnail', 'photo'], names: ['image'] },
        ['input[type="file"][accept*="image"]', 'input[type="file"]'],
        files
      );
      if (!done) {
        const dropped = await this.uploadViaDropzone(['[data-testid*="image"]', '.dropzone', '[class*="drop"]'], files);
        if (!dropped) throw new Error('Brak pola uploadu obrazów');
      }
      await this.waitForUploadComplete();
    }

    async validateForm() {
      const publishButton = this.findButtonByText(['publish', 'opublikuj', 'submit']);
      return !!publishButton;
    }

    async publish(mode) {
      const button = this.findButtonByText(['publish', 'opublikuj', 'submit']);
      if (!button) throw new Error('Brak przycisku publish');
      if (mode === 'safe') {
        return;
      }
      button.click();
      await new Promise((r) => setTimeout(r, 1000));
    }

    async getResult() {
      return { success: true, url: location.href };
    }
  }

  window.CultsAdapter = CultsAdapter;
})();
