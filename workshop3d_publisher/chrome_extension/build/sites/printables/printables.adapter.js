(() => {
  class PrintablesAdapter extends window.Workshop3DBaseAdapter {
    constructor() {
      super('Printables', 'printables.com', '/model/new', { modelInput: 'input[type="file"]', imageInput: 'input[type="file"]' });
    }
  }
  window.Workshop3DAdapters.printables = new PrintablesAdapter();
})();
