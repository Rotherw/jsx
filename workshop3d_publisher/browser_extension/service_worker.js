"use strict";

const EXTENSION_VERSION = chrome.runtime.getManifest().version;
const DEFAULT_SERVER = "http://127.0.0.1:5000";
let polling = false;

chrome.runtime.onInstalled.addListener((details) => {
  chrome.alarms.create("workshop3d-poll", { periodInMinutes: 0.5 });
  if (details.reason === "install") chrome.runtime.openOptionsPage();
  void pollBridge();
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create("workshop3d-poll", { periodInMinutes: 0.5 });
  void pollBridge();
});

chrome.action.onClicked.addListener(() => chrome.runtime.openOptionsPage());
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "workshop3d-poll") void pollBridge();
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url || changeInfo.status === "complete") {
    void inspectActiveJobs(tabId, tab.url || changeInfo.url || "");
  }
});

async function settings() {
  const stored = await chrome.storage.local.get(["serverUrl", "pairingKey"]);
  return {
    serverUrl: String(stored.serverUrl || DEFAULT_SERVER).replace(/\/$/, ""),
    pairingKey: String(stored.pairingKey || "").trim(),
  };
}

async function bridgeFetch(path, init = {}) {
  const cfg = await settings();
  if (!cfg.pairingKey) throw new Error("Brak kodu parowania w rozszerzeniu.");
  const headers = new Headers(init.headers || {});
  headers.set("X-WorkShop3D-Key", cfg.pairingKey);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  return fetch(`${cfg.serverUrl}${path}`, { ...init, headers, cache: "no-store" });
}

async function pollBridge() {
  if (polling) return;
  polling = true;
  try {
    await inspectActiveJobs();
    const heartbeat = await bridgeFetch("/api/browser/heartbeat", {
      method: "POST",
      body: JSON.stringify({ version: EXTENSION_VERSION }),
    });
    if (!heartbeat.ok) throw new Error(`Połączenie odrzucone (${heartbeat.status}).`);

    const response = await bridgeFetch("/api/browser/jobs/next");
    if (response.status === 204) return;
    if (!response.ok) throw new Error(`Nie można pobrać zadania (${response.status}).`);
    const job = await response.json();
    await processJob(job);
  } catch (error) {
    // Connection errors are expected while the Windows app is closed. Keep
    // them local; the options page gives the user an explicit connection test.
    console.debug("[WorkShop3D]", error);
  } finally {
    polling = false;
  }
}

async function processJob(job) {
  let tab;
  try {
    tab = await openOrReuseTab(job.target_url);
    if (job.platform === "thangs") await prepareThangs(tab.id);
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: fillStoreForm,
      args: [job],
    });
    const outcome = results[0] && results[0].result;
    if (!outcome) throw new Error("Strona nie zwróciła wyniku wypełniania.");

    if (outcome.status === "READY_FOR_REVIEW" || outcome.status === "SUBMITTED") {
      await rememberActiveJob(job, tab.id);
    }
    await reportResult(job.id, {
      status: outcome.status,
      url: outcome.url || tab.url || job.target_url,
      message: outcome.message || "Formularz został otwarty w Chrome.",
    });
    await chrome.tabs.update(tab.id, { active: true });
  } catch (error) {
    await reportResult(job.id, {
      status: "NEEDS_ATTENTION",
      url: tab && tab.url ? tab.url : job.target_url,
      message: `Chrome nie dokończył formularza: ${String(error.message || error)}`,
    });
  }
}

async function openOrReuseTab(targetUrl) {
    const target = new URL(targetUrl);
    const tabs = await chrome.tabs.query({});
  const matching = tabs
    .filter((tab) => {
      try { return new URL(tab.url || "").hostname === target.hostname; }
      catch (_) { return false; }
    })
    .sort((a, b) => Number(b.lastAccessed || 0) - Number(a.lastAccessed || 0));

  const exact = matching.find((tab) => {
    try {
      const current = new URL(tab.url || "");
      return current.pathname === target.pathname;
    } catch (_) { return false; }
  });

  let tab;
  if (exact) {
    tab = await chrome.tabs.update(exact.id, { active: true });
  } else {
    // Keep unrelated/open work intact. Put the uploader in the same existing
    // Chrome window instead of navigating a listing or edit tab away.
    const active = tabs.find((item) => item.active && !item.incognito);
    const create = { url: targetUrl, active: true };
    if (active && Number.isInteger(active.windowId)) create.windowId = active.windowId;
    tab = await chrome.tabs.create(create);
  }
  await waitForTab(tab.id);
  return chrome.tabs.get(tab.id);
}

function waitForTab(tabId, timeoutMs = 30000) {
  return new Promise((resolve) => {
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      chrome.tabs.onUpdated.removeListener(listener);
      resolve();
    };
    const listener = (changedId, info) => {
      if (changedId === tabId && info.status === "complete") finish();
    };
    chrome.tabs.onUpdated.addListener(listener);
    chrome.tabs.get(tabId).then((tab) => {
      if (tab.status === "complete") finish();
    }).catch(finish);
    setTimeout(finish, timeoutMs);
  });
}

async function prepareThangs(tabId) {
  // Thangs exposes the uploader through Add new -> Upload & Edit. It is a SPA,
  // so a few short, idempotent passes are more reliable than a brittle selector.
  for (let attempt = 0; attempt < 6; attempt += 1) {
    const result = await chrome.scripting.executeScript({
      target: { tabId },
      func: thangsStep,
    });
    const state = result[0] && result[0].result;
    if (state === "FORM") return;
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}

function thangsStep() {
  if (document.querySelector('input[type="file"]')) return "FORM";
  const normalize = (value) => String(value || "").trim().toLowerCase().replace(/\s+/g, " ");
  const visible = (el) => {
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  };
  const controls = [...document.querySelectorAll('button, a, [role="button"]')].filter(visible);
  const wanted = ["upload & edit", "upload and edit", "add new"];
  for (const label of wanted) {
    const control = controls.find((el) => normalize(el.innerText || el.textContent) === label);
    if (control) {
      control.click();
      return `CLICKED:${label}`;
    }
  }
  return "WAIT";
}

async function reportResult(jobId, body) {
  try {
    await bridgeFetch(`/api/browser/jobs/${encodeURIComponent(jobId)}/result`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  } catch (error) {
    console.debug("[WorkShop3D] result not delivered", error);
  }
}

async function rememberActiveJob(job, tabId) {
  const stored = await chrome.storage.local.get("activeJobs");
  const activeJobs = stored.activeJobs || {};
  activeJobs[job.id] = {
    id: job.id,
    tabId,
    platform: job.platform,
    success_hosts: job.success_hosts,
    success_paths: job.success_paths,
  };
  await chrome.storage.local.set({ activeJobs });
}

async function inspectActiveJobs(onlyTabId = null, hintedUrl = "") {
  const stored = await chrome.storage.local.get("activeJobs");
  const activeJobs = stored.activeJobs || {};
  let changed = false;
  for (const [jobId, job] of Object.entries(activeJobs)) {
    if (onlyTabId !== null && Number(job.tabId) !== Number(onlyTabId)) continue;
    let url = hintedUrl;
    if (!url) {
      try { url = (await chrome.tabs.get(job.tabId)).url || ""; }
      catch (_) {
        delete activeJobs[jobId];
        changed = true;
        continue;
      }
    }
    if (isSuccessUrl(job, url)) {
      await reportResult(jobId, {
        status: "PUBLISHED",
        url,
        message: "Chrome wykrył stronę gotowej oferty w sklepie.",
      });
      delete activeJobs[jobId];
      changed = true;
    }
  }
  if (changed) await chrome.storage.local.set({ activeJobs });
}

function isSuccessUrl(job, value) {
  try {
    const url = new URL(value);
    if (!(job.success_hosts || []).includes(url.hostname)) return false;
    if (job.platform === "thangs") {
      return (job.success_paths || []).every((fragment) => url.pathname.includes(fragment));
    }
    return (job.success_paths || []).some((fragment) => url.pathname.includes(fragment));
  } catch (_) {
    return false;
  }
}

// This function is serialized by chrome.scripting and runs inside the store
// page. Keep it self-contained: it cannot reference service-worker globals.
async function fillStoreForm(job) {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const normalize = (value) => String(value || "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().replace(/\s+/g, " ").trim();
  const visible = (el) => {
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  };
  const descriptor = (el) => {
    const labels = [];
    if (el.labels) labels.push(...[...el.labels].map((label) => label.innerText));
    const closest = el.closest("label");
    if (closest) labels.push(closest.innerText);
    return normalize([
      el.name, el.id, el.placeholder, el.getAttribute("aria-label"),
      el.getAttribute("data-testid"), ...labels,
    ].filter(Boolean).join(" "));
  };
  const score = (el, terms) => {
    const text = descriptor(el);
    let result = 0;
    for (let index = 0; index < terms.length; index += 1) {
      if (text.includes(normalize(terms[index]))) result = Math.max(result, 100 - index);
    }
    return result;
  };
  const pick = (selector, terms) => [...document.querySelectorAll(selector)]
    .filter((el) => !el.disabled && visible(el))
    .map((el) => ({ el, value: score(el, terms) }))
    .filter((item) => item.value > 0)
    .sort((a, b) => b.value - a.value)[0]?.el || null;
  const setValue = (el, value) => {
    if (!el || value === undefined || value === null || value === "") return false;
    el.focus();
    if (el.isContentEditable) {
      el.textContent = String(value);
    } else {
      const proto = el instanceof HTMLTextAreaElement
        ? HTMLTextAreaElement.prototype
        : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
      if (setter) setter.call(el, String(value));
      else el.value = String(value);
    }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.blur();
    return true;
  };

  const loginUrl = /\/(login|sign-in|signin|auth)(\/|\?|$)/i.test(location.href);
  const bodyText = normalize(document.body?.innerText || "");
  if (loginUrl || (bodyText.includes("sign in to continue") && !document.querySelector('input[type="file"]'))) {
    return {
      status: "NEEDS_ATTENTION",
      url: location.href,
      message: "Ta karta wymaga zalogowania. Zaloguj się w Chrome i kliknij ponowienie w panelu.",
    };
  }

  // Give client-rendered forms a moment to mount.
  for (let wait = 0; wait < 12; wait += 1) {
    if (document.querySelector('input, textarea, [contenteditable="true"]')) break;
    await sleep(500);
  }

  const meta = job.metadata || {};
  const filled = [];
  const title = pick('input:not([type]), input[type="text"]', [
    "model name", "creation name", "title", "name", "tytul", "nazwa",
  ]);
  if (setValue(title, meta.title)) filled.push("tytuł");

  const description = pick('textarea, [contenteditable="true"]', [
    "description", "details", "about", "opis",
  ]);
  if (setValue(description, meta.description)) filled.push("opis");

  const shortDescription = pick('input:not([type]), input[type="text"], textarea', [
    "short description", "summary", "subtitle", "krotki opis",
  ]);
  if (shortDescription !== description && setValue(shortDescription, meta.short_description)) {
    filled.push("krótki opis");
  }

  const price = pick('input[type="number"], input[inputmode="decimal"], input[inputmode="numeric"], input[type="text"]', [
    "price", "download price", "cena",
  ]);
  if (setValue(price, meta.price)) filled.push("cena");

  const tags = pick('input:not([type]), input[type="text"], textarea', [
    "tags", "keywords", "tagi", "slowa kluczowe",
  ]);
  if (setValue(tags, (meta.tags || []).join(", "))) filled.push("tagi");

  const category = pick("select", ["category", "type", "kategoria"]);
  if (category && meta.category) {
    const wanted = normalize(meta.category);
    const option = [...category.options].find((item) => normalize(item.textContent).includes(wanted));
    if (option) {
      category.value = option.value;
      category.dispatchEvent(new Event("change", { bubbles: true }));
      filled.push("kategoria");
    }
  }

  // If a store exposes an AI declaration, always set it to the true metadata
  // value. Never hard-code "not AI".
  const aiCheckbox = pick('input[type="checkbox"], input[type="radio"]', [
    "made with ai", "generated with ai", "artificial intelligence", "ai generated",
  ]);
  if (aiCheckbox && aiCheckbox.checked !== Boolean(meta.made_with_ai)) {
    aiCheckbox.click();
    filled.push("deklaracja AI");
  }

  const inputs = [...document.querySelectorAll('input[type="file"]')];
  let uploaded = 0;
  const downloaded = new Map();
  const loadFile = async (item) => {
    if (downloaded.has(item.url)) return downloaded.get(item.url);
    const response = await fetch(item.url, { cache: "no-store" });
    if (!response.ok) throw new Error(`Nie można pobrać ${item.name} (${response.status}).`);
    const file = new File([await response.blob()], item.name, { type: item.mime || "application/octet-stream" });
    downloaded.set(item.url, file);
    return file;
  };

  for (let index = 0; index < inputs.length; index += 1) {
    const input = inputs[index];
    const text = `${descriptor(input)} ${normalize(input.accept)}`;
    const wantsImages = /image|photo|picture|cover|preview|thumbnail|gallery|grafik|zdjec/.test(text);
    const wantsModels = /stl|3mf|glb|model|3d|archive|zip|file|plik/.test(text);
    let selected;
    if (wantsImages && !wantsModels) selected = job.files.filter((item) => item.kind === "image");
    else if (wantsModels && !wantsImages) selected = job.files.filter((item) => item.kind === "model");
    else if (inputs.length === 1) selected = [...job.files];
    else selected = index === 0
      ? job.files.filter((item) => item.kind === "model")
      : job.files.filter((item) => item.kind === "image");
    if (!input.multiple) selected = selected.slice(0, 1);
    if (!selected.length) continue;

    const transfer = new DataTransfer();
    for (const item of selected) transfer.items.add(await loadFile(item));
    input.files = transfer.files;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    uploaded += transfer.files.length;
  }

  if (!inputs.length) {
    return {
      status: "NEEDS_ATTENTION",
      url: location.href,
      message: "Nie znaleziono pola do wgrania plików. Strona mogła zmienić formularz albo wymaga dodatkowego kliknięcia.",
    };
  }
  if (!uploaded) {
    return {
      status: "NEEDS_ATTENTION",
      url: location.href,
      message: "Formularz jest otwarty, ale Chrome nie przypisał plików do żadnego pola.",
    };
  }

  await sleep(1000);
  if (job.auto_submit) {
    const wanted = job.publish_as === "draft"
      ? ["save draft", "draft", "zapisz szkic"]
      : ["publish model", "publish", "submit", "create", "list model", "opublikuj"];
    const buttons = [...document.querySelectorAll('button, [role="button"], input[type="submit"]')]
      .filter((el) => !el.disabled && visible(el));
    const submit = buttons
      .map((el) => ({ el, text: normalize(el.innerText || el.value || el.getAttribute("aria-label")) }))
      .find((item) => wanted.some((label) => item.text === normalize(label) || item.text.includes(normalize(label))))?.el;
    if (submit) {
      submit.click();
      return {
        status: "SUBMITTED",
        url: location.href,
        message: `Wgrano ${uploaded} plików, uzupełniono ${filled.join(", ") || "dostępne pola"} i kliknięto przycisk wysłania. Chrome czeka na adres gotowej oferty.`,
      };
    }
  }

  return {
    status: "READY_FOR_REVIEW",
    url: location.href,
    message: `Wgrano ${uploaded} plików i uzupełniono ${filled.join(", ") || "dostępne pola"}. Sprawdź formularz i kliknij publikację w sklepie.`,
  };
}

// Keep a fast poll while the service worker is alive; alarms wake it back up.
setInterval(() => void pollBridge(), 5000);
void pollBridge();
