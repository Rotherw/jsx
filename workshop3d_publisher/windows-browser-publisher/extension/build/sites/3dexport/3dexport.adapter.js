(() => {
  class Export3dAdapter extends window.BaseMarketplaceAdapter {
    constructor() { super('export3d'); }
    detectPage() { return location.hostname.includes('3dexport'); }
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
    async publish() { throw new Error('Adapter export3d nie jest jeszcze ukończony.'); }
    async getResult() { return { success: false, url: location.href }; }
  }
  window.Export3dAdapter = Export3dAdapter;
})();
