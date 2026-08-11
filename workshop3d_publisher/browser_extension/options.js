"use strict";

const server = document.getElementById("server");
const key = document.getElementById("key");
const status = document.getElementById("status");

async function load() {
  const stored = await chrome.storage.local.get(["serverUrl", "pairingKey"]);
  server.value = stored.serverUrl || "http://127.0.0.1:5000";
  key.value = stored.pairingKey || "";
}

async function save() {
  const serverUrl = server.value.trim().replace(/\/$/, "");
  const pairingKey = key.value.trim();
  await chrome.storage.local.set({ serverUrl, pairingKey });
  status.className = "ok";
  status.textContent = "Zapisano. Rozszerzenie może teraz odbierać zadania z panelu.";
}

async function testConnection() {
  await save();
  try {
    const response = await fetch(`${server.value.trim().replace(/\/$/, "")}/api/browser/heartbeat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-WorkShop3D-Key": key.value.trim(),
      },
      body: JSON.stringify({ version: chrome.runtime.getManifest().version }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    status.className = "ok";
    status.textContent = "Połączono. Możesz zamknąć tę kartę i wrócić do panelu WorkShop3D.";
  } catch (error) {
    status.className = "bad";
    status.textContent = `Brak połączenia: ${error.message}. Uruchom aplikację Windows i sprawdź kod.`;
  }
}

document.getElementById("save").addEventListener("click", save);
document.getElementById("test").addEventListener("click", testConnection);
void load();
