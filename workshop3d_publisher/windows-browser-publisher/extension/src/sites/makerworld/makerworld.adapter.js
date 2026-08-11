(() => {
  class MakerworldAdapter extends window.BaseMarketplaceAdapter {
    constructor() { super('makerworld'); }
    detectPage() { return location.hostname.includes('makerworld'); }
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
    async validateForm() { return false; }
    async publish() { throw new Error('Adapter makerworld nie jest jeszcze ukończony.'); }
    async getResult() { return { success: false, url: location.href }; }
  }
  window.MakerworldAdapter = MakerworldAdapter;
})();
