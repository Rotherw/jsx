(() => {
  class CrealityAdapter extends window.BaseMarketplaceAdapter {
    constructor() { super('creality'); }
    detectPage() {
      return /crealitycloud\.com|crealitycloud\.cn/.test(location.hostname);
    }
    isLoggedIn() { return !document.querySelector('a[href*="login"], button[class*="login"]'); }
    async openPublisher() {
      if (!/upload|model/.test(location.href)) {
        location.href = /\.cn$/.test(location.hostname)
          ? 'https://www.crealitycloud.cn/model/upload'
          : 'https://www.crealitycloud.com/model/upload';
        await this.waitForSpaFormRefresh();
      }
    }
    async fillTitle(metadata) { await this.fillTextField({ labels: ['title', 'name'] }, ['input[name*="title"]'], metadata.title); }
    async fillDescription(metadata) { await this.fillTextField({ labels: ['description'] }, ['textarea[name*="description"]', '[contenteditable="true"]'], metadata.description || ''); }
    async fillTags(metadata) {
      if (!metadata.tags?.length) return;
      await this.fillTextField({ labels: ['tags'] }, ['input[name*="tag"]'], metadata.tags.join(', '));
    }
    async fillCategory(metadata) {
      if (!metadata.category) return;
      await this.fillTextField({ labels: ['category'] }, ['input[name*="category"]'], metadata.category);
    }
    async fillLicense(metadata) {
      if (!metadata.license) return;
      await this.fillTextField({ labels: ['license'] }, ['input[name*="license"]'], metadata.license);
    }
    async fillPrice(metadata) {
      if (metadata.price == null) return;
      await this.fillTextField({ labels: ['price'] }, ['input[name*="price"]'], String(metadata.price));
    }
    async setCollection() {}
    async uploadModelFiles(_metadata, files) {
      const ok = await this.uploadViaInput({ labels: ['file', 'model', '3d'] }, ['input[type="file"]'], files);
      if (!ok) await this.uploadViaDropzone(['[class*="drop"]', '[data-testid*="drop"]'], files);
      await this.waitForUploadComplete();
    }
    async uploadImages(_metadata, files) {
      const ok = await this.uploadViaInput({ labels: ['image', 'cover'] }, ['input[type="file"]'], files);
      if (!ok) await this.uploadViaDropzone(['[class*="drop"]', '[data-testid*="drop"]'], files);
      await this.waitForUploadComplete();
    }
    async validateForm() { return !!this.findButtonByText(['publish', 'submit', 'save']); }
    async publish(mode) {
      if (mode === 'safe') return;
      this.findButtonByText(['publish', 'submit', 'save'])?.click();
    }
    async getResult() { return { success: true, url: location.href }; }
  }

  window.CrealityAdapter = CrealityAdapter;
})();
