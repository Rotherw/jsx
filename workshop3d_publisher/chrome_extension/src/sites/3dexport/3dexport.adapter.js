(() => {
  class ExportAdapter extends window.Workshop3DBaseAdapter {
    constructor() {
      super('3DExport', '3dexport.com', '/upload-model', { modelInput: 'input[type="file"]', imageInput: 'input[type="file"]' });
    }
  }
  window.Workshop3DAdapters['3dexport'] = new ExportAdapter();
})();
