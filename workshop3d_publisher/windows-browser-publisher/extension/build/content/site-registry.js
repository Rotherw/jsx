(() => {
  const ADAPTERS = {
    cults: new window.CultsAdapter(),
    thangs: new window.ThangsAdapter(),
    creality: new window.CrealityAdapter(),
    printables: new window.PrintablesAdapter(),
    makerworld: new window.MakerworldAdapter(),
    myminifactory: new window.MyminifactoryAdapter(),
    '3dexport': new window.Export3dAdapter()
  };

  function getAdapterByMarketplace(marketplace) {
    return ADAPTERS[marketplace] || null;
  }

  function detectAdapter() {
    return Object.values(ADAPTERS).find((adapter) => adapter.detectPage()) || null;
  }

  window.SiteRegistry = {
    getAdapterByMarketplace,
    detectAdapter
  };
})();
