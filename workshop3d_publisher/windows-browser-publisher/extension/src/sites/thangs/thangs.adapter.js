(() => {
  class ThangsAdapter extends window.BaseMarketplaceAdapter {
    constructor() { super('thangs'); }
    detectPage() { return /thangs\.com/.test(location.hostname); }
    isLoggedIn() { return !document.querySelector('a[href*="login"], button[data-testid="login"]'); }
    async openPublisher() {
      if (!/upload/.test(location.href)) {
        location.href = 'https://thangs.com/designer/upload';
        await this.waitForSpaFormRefresh();
      }
    }
    async fillTitle(metadata) {
      await this.fillTextField({ labels: ['title', 'name'] }, ['input[name*="title"]', 'input[placeholder*="title"]'], metadata.title);
    }
    async fillDescription(metadata) {
      await this.fillTextField({ labels: ['description'] }, ['textarea[name*="description"]', '[contenteditable="true"]'], metadata.description || '');
    }
    async fillTags(metadata) {
      if (!metadata.tags?.length) return;
      await this.fillTextField({ labels: ['tags'] }, ['input[name*="tag"]'], metadata.tags.join(', '));
    }
    async fillCategory() {}
    async fillLicense() {}
    async fillPrice() {}
    async setCollection() {}
    async uploadModelFiles(_metadata, files) {
      const ok = await this.uploadViaInput({ labels: ['file', 'model'] }, ['input[type="file"]'], files);
      if (!ok) await this.uploadViaDropzone(['[class*="drop"]', '[data-testid*="drop"]'], files);
      await this.waitForUploadComplete();
    }
    async uploadImages(_metadata, files) {
      const ok = await this.uploadViaInput({ labels: ['image', 'thumbnail'] }, ['input[type="file"]'], files);
      if (!ok) await this.uploadViaDropzone(['[class*="drop"]', '[data-testid*="drop"]'], files);
      await this.waitForUploadComplete();
    }
    async validateForm() { return !!this.findButtonByText(['publish', 'upload', 'submit']); }
    async publish(mode) {
      if (mode === 'safe') return;
      this.findButtonByText(['publish', 'upload', 'submit'])?.click();
    }
    async getResult() { return { success: true, url: location.href }; }
  }

  window.ThangsAdapter = ThangsAdapter;
})();
