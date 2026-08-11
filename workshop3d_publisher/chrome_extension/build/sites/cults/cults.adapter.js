(() => {
  class CultsAdapter extends window.Workshop3DBaseAdapter {
    constructor() {
      super('Cults3D', 'cults3d.com', '/en/3d-model/new', {
        modelInput: 'input[type="file"][accept*=".stl"], input[type="file"][multiple]',
        imageInput: 'input[type="file"][accept*="image"], input[type="file"][multiple]'
      });
    }
  }
  window.Workshop3DAdapters.cults = new CultsAdapter();
})();
