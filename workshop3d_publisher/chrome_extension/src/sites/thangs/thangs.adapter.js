(() => {
  class ThangsAdapter extends window.Workshop3DBaseAdapter {
    constructor() {
      super('Thangs3D', 'thangs.com', '/upload', {
        modelDropZone: '[data-testid*="upload"], [class*="dropzone" i]',
        imageDropZone: '[data-testid*="image"], [class*="dropzone" i]'
      });
    }
  }
  window.Workshop3DAdapters.thangs = new ThangsAdapter();
})();
