(() => {
  class PrintablesAdapter extends window.BaseMarketplaceAdapter {
    constructor() { super('printables'); }
    detectPage() { return location.hostname.includes('printables'); }
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
    async publish() { throw new Error('Adapter printables nie jest jeszcze ukończony.'); }
    async getResult() { return { success: false, url: location.href }; }
  }
  window.PrintablesAdapter = PrintablesAdapter;
})();
