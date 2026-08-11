const express = require('express');
const fs = require('fs');
const path = require('path');
const chokidar = require('chokidar');
const { rateLimit } = require('express-rate-limit');
const { ensureConfig, loadConfig, writeJson } = require('./config');
const { scanProducts, updatePublishState } = require('./models');
const { logLine, format } = require('./logger');

const config = ensureConfig();
const app = express();
app.use(express.json({ limit: '10mb' }));

let productsCache = [];
let currentConfig = config;

const apiLimiter = rateLimit({
  windowMs: 60_000,
  limit: 240,
  standardHeaders: 'draft-7',
  legacyHeaders: false
});

const healthLimiter = rateLimit({
  windowMs: 60_000,
  limit: 60,
  standardHeaders: 'draft-7',
  legacyHeaders: false
});

const fileLimiter = rateLimit({
  windowMs: 60_000,
  limit: 120,
  standardHeaders: 'draft-7',
  legacyHeaders: false
});

app.use(cors);
app.use(auth);
app.use(apiLimiter);

app.get('/health', healthLimiter, (_req, res) => {
  res.json({
    ok: true,
    host: currentConfig.bridgeHost,
    port: currentConfig.bridgePort,
    watchFolderExists: fs.existsSync(currentConfig.watchFolder)
  });
});

app.get('/config', (_req, res) => {
  const safeConfig = { ...currentConfig };
  delete safeConfig.token;
  res.json(safeConfig);
});

app.put('/config', (req, res) => {
  currentConfig = { ...currentConfig, ...req.body };
  writeJson(path.join(__dirname, '..', '..', 'config', 'config.json'), currentConfig);
  rescan();
  res.json({ ok: true });
});

app.get('/models', (_req, res) => {
  res.json({ items: productsCache });
});

app.get('/model-file', fileLimiter, (req, res) => {
  const { modelId, file } = req.query;
  const item = productsCache.find((x) => x.id === modelId);
  if (!item) return res.status(404).json({ error: 'MODEL_NOT_FOUND' });
  const found = item.files.find((f) => f.relativePath === file || f.name === file);
  if (!found) return res.status(404).json({ error: 'FILE_NOT_FOUND' });
  res.sendFile(found.fullPath);
});

app.post('/publish-state', (req, res) => {
  const { modelId, marketplace, published, url, error } = req.body || {};
  if (!modelId || !marketplace) return res.status(400).json({ error: 'MISSING_DATA' });
  const item = productsCache.find((x) => x.id === modelId);
  if (!item) return res.status(404).json({ error: 'MODEL_NOT_FOUND' });

  const state = updatePublishState(item.folderPath, marketplace, { published: !!published, url: url || '', error: error || '' });
  logLine(format(item.title, marketplace, 'Publish state update', published ? 'SUCCESS' : `ERROR: ${error || 'Unknown error'}`));
  rescan();
  res.json({ ok: true, state });
});

app.post('/log', (req, res) => {
  const { model, marketplace, action, result } = req.body || {};
  logLine(format(model || 'Unknown', marketplace || 'Unknown', action || 'Action', result || 'UNKNOWN'));
  res.json({ ok: true });
});

function startWatcher() {
  if (!fs.existsSync(currentConfig.watchFolder)) {
    fs.mkdirSync(currentConfig.watchFolder, { recursive: true });
  }
  const watcher = chokidar.watch(currentConfig.watchFolder, {
    ignoreInitial: true,
    awaitWriteFinish: { stabilityThreshold: 1200, pollInterval: 100 }
  });
  const queueRescan = () => {
    setTimeout(rescan, 200);
  };
  watcher.on('add', queueRescan);
  watcher.on('change', queueRescan);
  watcher.on('unlink', queueRescan);
  watcher.on('addDir', queueRescan);
  watcher.on('unlinkDir', queueRescan);
}

function main() {
  currentConfig = loadConfig();
  rescan();
  startWatcher();
  app.listen(currentConfig.bridgePort, currentConfig.bridgeHost, () => {
    logLine(`[Bridge] Listening on http://${currentConfig.bridgeHost}:${currentConfig.bridgePort}`);
  });
}

main();
