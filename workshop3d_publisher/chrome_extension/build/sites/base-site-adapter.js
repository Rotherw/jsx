(() => {
  class BaseSiteAdapter {
    constructor(name, hostMatch, publishPath, selectors = {}) {
      this.name = name;
      this.hostMatch = hostMatch;
      this.publishPath = publishPath;
      this.selectors = selectors;
      this.logs = [];
    }

    log(model, action, result) {
      this.logs.push({ model, marketplace: this.name, action, result, date: new Date().toISOString() });
    }

    detectPage() {
      return location.hostname.includes(this.hostMatch);
    }

    isLoggedIn() {
      const loggedOutHints = ['log in', 'sign in', 'zaloguj'];
      const btn = window.W3D_DOM.queryByText(document, 'button,a', loggedOutHints);
      return !btn;
    }

    openPublisher() {
      if (this.publishPath && !location.pathname.includes(this.publishPath)) {
        location.href = `https://${location.hostname}${this.publishPath}`;
      }
    }

    _fill(hints, value, modelName, fieldName) {
      const field = window.W3D_DOM.findField(document, hints);
      if (!field) {
        this.log(modelName, `Looking for ${fieldName} input`, 'ERROR: element not found');
        return false;
      }
      window.W3D_DOM.setNativeValue(field, value);
      this.log(modelName, `Fill ${fieldName}`, 'SUCCESS');
      return true;
    }

    fillTitle(product) { return this._fill(['title', 'name', 'tytuł'], product.metadata.title || product.name, product.name, 'Title'); }
    fillDescription(product) { return this._fill(['description', 'opis'], product.metadata.description || '', product.name, 'Description'); }
    fillTags(product) { return this._fill(['tags', 'tagi', 'keywords'], (product.metadata.tags || []).join(', '), product.name, 'Tags'); }
    fillCategory(product) { return this._fill(['category', 'kategoria'], product.metadata.category || '', product.name, 'Category'); }
    fillLicense(product) { return this._fill(['license', 'licence', 'licencja'], product.metadata.license || '', product.name, 'License'); }
    fillPrice(product) { return this._fill(['price', 'cena'], product.metadata.price ?? '', product.name, 'Price'); }
    setCollection(product) { return this._fill(['collection', 'kolekcja'], product.metadata.collection || '', product.name, 'Collection'); }

    async uploadModelFiles(product, runtime) {
      const input = document.querySelector(this.selectors.modelInput || 'input[type="file"]');
      const dropZone = document.querySelector(this.selectors.modelDropZone || '[data-testid*="upload"], [class*="drop" i]');
      const modelFiles = (product.files || []).filter((f) => f.type === 'model').map((f) => f.name);
      if (!modelFiles.length) {
        this.log(product.name, 'Uploading model files', 'ERROR: no model files');
        return false;
      }

      const files = [];
      for (const fileName of modelFiles) {
        try {
          files.push(await window.W3D_Upload.fetchFileFromBridge(runtime.bridgeBaseUrl, runtime.token, product.id, fileName));
        } catch (error) {
          this.log(product.name, `Downloading ${fileName}`, `ERROR: ${error.message}`);
        }
      }
      if (!files.length) return false;

      if (input) {
        await window.W3D_Upload.assignToInput(input, files);
        this.log(product.name, 'Uploading model files', 'SUCCESS');
        return true;
      }
      if (dropZone) {
        await window.W3D_Upload.dragDropUpload(dropZone, files);
        this.log(product.name, 'Uploading model files by drag/drop', 'SUCCESS');
        return true;
      }
      this.log(product.name, 'Looking for model upload target', 'ERROR: target not found');
      return false;
    }

    async uploadImages(product, runtime) {
      const input = document.querySelector(this.selectors.imageInput || 'input[type="file"]');
      const dropZone = document.querySelector(this.selectors.imageDropZone || '[data-testid*="image"], [class*="drop" i]');
      const imageFiles = (product.files || []).filter((f) => f.type === 'image').map((f) => f.name);
      if (!imageFiles.length) {
        this.log(product.name, 'Uploading images', 'ERROR: no image files');
        return false;
      }
      const files = [];
      for (const fileName of imageFiles) {
        try {
          files.push(await window.W3D_Upload.fetchFileFromBridge(runtime.bridgeBaseUrl, runtime.token, product.id, fileName));
        } catch (error) {
          this.log(product.name, `Downloading ${fileName}`, `ERROR: ${error.message}`);
        }
      }
      if (!files.length) return false;

      if (input) {
        await window.W3D_Upload.assignToInput(input, files);
        this.log(product.name, 'Uploading images', 'SUCCESS');
        return true;
      }
      if (dropZone) {
        await window.W3D_Upload.dragDropUpload(dropZone, files);
        this.log(product.name, 'Uploading images by drag/drop', 'SUCCESS');
        return true;
      }
      this.log(product.name, 'Looking for image upload target', 'ERROR: target not found');
      return false;
    }

    validateForm(product) {
      const titleField = window.W3D_DOM.findField(document, ['title', 'name']);
      const descField = window.W3D_DOM.findField(document, ['description', 'opis']);
      const ok = Boolean(titleField && descField);
      this.log(product.name, 'Validate form', ok ? 'SUCCESS' : 'ERROR: required fields missing');
      return ok;
    }

    publish() {
      const btn = window.W3D_DOM.queryByText(document, 'button,[role="button"],input[type="submit"]', ['publish', 'opublikuj', 'submit']);
      if (!btn) return false;
      btn.click();
      return true;
    }

    getResult() {
      const url = location.href;
      return { success: true, url, logs: this.logs };
    }
  }

  window.Workshop3DAdapters = window.Workshop3DAdapters || {};
  window.Workshop3DBaseAdapter = BaseSiteAdapter;
})();
