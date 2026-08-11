(() => {
  class CrealityAdapter extends window.Workshop3DBaseAdapter {
    constructor() {
      super('CrealityCloud', 'crealitycloud.com', '/creator/upload', {
        modelInput: 'input[type="file"]',
        imageInput: 'input[type="file"]'
      });
    }
  }
  window.Workshop3DAdapters.creality = new CrealityAdapter();
})();
