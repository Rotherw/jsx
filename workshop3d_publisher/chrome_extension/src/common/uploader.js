(() => {
  async function fetchFileFromBridge(bridgeBaseUrl, token, productId, fileName) {
    const url = `${bridgeBaseUrl}/api/products/${encodeURIComponent(productId)}/file?path=${encodeURIComponent(fileName)}&token=${encodeURIComponent(token)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`file download failed: ${fileName}`);
    const blob = await res.blob();
    const ext = fileName.split('.').pop();
    return new File([blob], fileName, { type: blob.type || `application/${ext}`, lastModified: Date.now() });
  }

  async function assignToInput(input, files) {
    const dt = new DataTransfer();
    files.forEach((f) => dt.items.add(f));
    input.files = dt.files;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  async function dragDropUpload(dropZone, files) {
    const dt = new DataTransfer();
    files.forEach((f) => dt.items.add(f));
    for (const eventName of ['dragenter', 'dragover', 'drop']) {
      dropZone.dispatchEvent(new DragEvent(eventName, { bubbles: true, cancelable: true, dataTransfer: dt }));
    }
  }

  window.W3D_Upload = { fetchFileFromBridge, assignToInput, dragDropUpload };
})();
