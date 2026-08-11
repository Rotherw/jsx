(() => {
  class MakerWorldAdapter extends window.Workshop3DBaseAdapter {
    constructor() {
      super('MakerWorld', 'makerworld.com', '/en/models/upload', { modelInput: 'input[type="file"]', imageInput: 'input[type="file"]' });
    }
  }
  window.Workshop3DAdapters.makerworld = new MakerWorldAdapter();
})();
