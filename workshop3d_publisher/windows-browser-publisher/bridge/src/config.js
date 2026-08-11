const fs = require('fs');
const path = require('path');
const { nanoid } = require('nanoid');

const ROOT = path.resolve(__dirname, '..', '..');
const CONFIG_DIR = path.join(ROOT, 'config');
const CONFIG_PATH = path.join(CONFIG_DIR, 'config.json');
const LOG_DIR = path.join(ROOT, 'bridge', 'logs');
const LOG_PATH = path.join(LOG_DIR, 'publisher.log');

const DEFAULT_CONFIG = {
  watchFolder: 'F:\\Gotowe do sklepu',
  nextcloudFolder: '',
  safeMode: true,
  browser: 'chrome',
  bridgeHost: '127.0.0.1',
  bridgePort: 17373,
  token: ''
};

function ensureDir(p) {
  if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true });
}

function readJson(filePath, fallback) {
  try {
    if (!fs.existsSync(filePath)) return fallback;
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return fallback;
  }
}

function writeJson(filePath, obj) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, JSON.stringify(obj, null, 2), 'utf8');
}

function ensureConfig() {
  ensureDir(CONFIG_DIR);
  ensureDir(LOG_DIR);
  const config = { ...DEFAULT_CONFIG, ...readJson(CONFIG_PATH, {}) };
  if (!config.token || config.token === 'CHANGE_ME_LOCAL_TOKEN') {
    config.token = nanoid(40);
  }
  writeJson(CONFIG_PATH, config);
  return config;
}

function loadConfig() {
  return { ...DEFAULT_CONFIG, ...readJson(CONFIG_PATH, {}) };
}

module.exports = {
  ROOT,
  LOG_PATH,
  CONFIG_PATH,
  ensureConfig,
  loadConfig,
  writeJson,
  readJson
};
