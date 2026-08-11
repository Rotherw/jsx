"use strict";

const status = document.getElementById("status");
const bootstrap = globalThis.WORKSHOP3D_BOOTSTRAP || {};
const serverUrl = String(bootstrap.serverUrl || "http://127.0.0.1:5000").replace(/\/$/, "");
const pairingKey = String(bootstrap.pairingKey || "").trim();

async function saveAutomaticSettings() {
  await chrome.storage.local.set({ serverUrl, pairingKey });
}

async function testConnection() {
  await saveAutomaticSettings();
  if (!pairingKey) {
    status.className = "bad";
    status.textContent = "Instalator nie przygotował połączenia. Uruchom ponownie plik 1_ZAINSTALUJ.";
    return;
  }
  try {
    const response = await fetch(`${serverUrl}/api/browser/heartbeat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-WorkShop3D-Key": pairingKey,
      },
      body: JSON.stringify({ version: chrome.runtime.getManifest().version }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    status.className = "ok";
    status.textContent = "Połączono. Niczego więcej nie musisz ustawiać.";
  } catch (error) {
    status.className = "bad";
    status.textContent = `Publisher jeszcze się uruchamia (${error.message}). Sprawdzę ponownie automatycznie.`;
    setTimeout(testConnection, 3000);
  }
}

document.getElementById("dashboard").addEventListener("click", () => {
  void chrome.tabs.create({ url: serverUrl, active: true });
});
void testConnection();
