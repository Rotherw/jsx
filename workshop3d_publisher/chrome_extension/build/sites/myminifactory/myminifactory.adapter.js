(() => {
  class MyMiniFactoryAdapter extends window.Workshop3DBaseAdapter {
    constructor() {
      super('MyMiniFactory', 'myminifactory.com', '/users/upload', { modelInput: 'input[type="file"]', imageInput: 'input[type="file"]' });
    }
  }
  window.Workshop3DAdapters.myminifactory = new MyMiniFactoryAdapter();
})();
