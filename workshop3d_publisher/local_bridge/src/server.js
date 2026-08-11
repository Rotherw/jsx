import express from 'express';
import cors from 'cors';
import fs from 'fs';
import mime from 'mime-types';
import { WebSocketServer } from 'ws';
import { scanProducts, savePublishState } from './scanner.js';
import { createWatcher } from './watcher.js';
import { saveConfig } from './config.js';
import { Logger } from './logger.js';

function authMiddleware(config) {
  return (req, res, next) => {
    const token = req.header('x-publisher-token') || req.query.token;
    if (token !== config.token) return res.status(401).json({ error: 'unauthorized' });
    next();
  };
}

export function startServer({ config, rootDir }) {
  const app = express();
  const logger = new Logger(`${rootDir}/runtime/logs/publisher.log`);
  app.use(express.json({ limit: '20mb' }));
  app.use(cors({ origin: true }));

  let products = scanProducts(config.watchFolder);

  const refresh = () => {
    products = scanProducts(config.watchFolder);
    const payload = JSON.stringify({ type: 'products.updated', products });
    wss.clients.forEach((client) => {
      if (client.readyState === 1) client.send(payload);
    });
  };

  app.get('/health', (_req, res) => res.json({ ok: true, host: config.host, port: config.port }));

  app.use('/api', authMiddleware(config));

  app.get('/api/config', (_req, res) => {
    res.json({
      watchFolder: config.watchFolder,
      nextcloudFolder: config.nextcloudFolder,
      safeMode: config.safeMode,
      browser: config.browser,
      host: config.host,
      port: config.port
    });

    app.post('/api/config', (req, res) => {
      const next = {
        ...config,
        watchFolder: req.body.watchFolder || config.watchFolder,
        nextcloudFolder: req.body.nextcloudFolder || '',
        safeMode: req.body.safeMode ?? config.safeMode,
        browser: req.body.browser || config.browser
      };
      saveConfig(rootDir, next);
      config.watchFolder = next.watchFolder;
      config.nextcloudFolder = next.nextcloudFolder;
      config.safeMode = next.safeMode;
      config.browser = next.browser;
      refresh();
      res.json({ ok: true });
    });
  });

  app.get('/api/products', (_req, res) => res.json(products));

  app.get('/api/products/:id', (req, res) => {
    const found = products.find((p) => p.id === req.params.id);
    if (!found) return res.status(404).json({ error: 'not found' });
    res.json(found);
  });

  app.get('/api/products/:id/file', (req, res) => {
    const found = products.find((p) => p.id === req.params.id);
    if (!found) return res.status(404).json({ error: 'not found' });
    const relative = String(req.query.path || '');
    const file = found.files.find((f) => f.name === relative);
    if (!file) return res.status(404).json({ error: 'file not found' });
    const contentType = mime.lookup(file.name) || 'application/octet-stream';
    res.setHeader('Content-Type', contentType);
    fs.createReadStream(file.path).pipe(res);
  });

  app.post('/api/products/:id/publish-state', (req, res) => {
    const found = products.find((p) => p.id === req.params.id);
    if (!found) return res.status(404).json({ error: 'not found' });

    const { marketplace, published, url, error } = req.body || {};
    if (!marketplace) return res.status(400).json({ error: 'marketplace required' });

    const state = { ...found.publishState };
    state[marketplace] = {
      published: Boolean(published),
      url: url || null,
      error: error || null,
      date: new Date().toISOString()
    };

    savePublishState(found.folderPath, state);
    logger.log(found.name, marketplace, 'Save publish state', published ? 'SUCCESS' : `ERROR: ${error || 'unknown'}`);
    refresh();
    res.json({ ok: true, state: state[marketplace] });
  });

  app.post('/api/logs', (req, res) => {
    const { model = 'Unknown', marketplace = 'General', action = 'Action', result = 'INFO' } = req.body || {};
    const line = logger.log(model, marketplace, action, result);
    res.json({ ok: true, line });
  });

  const server = app.listen(config.port, config.host, () => {
    logger.log('SYSTEM', 'Bridge', `Listening on ${config.host}:${config.port}`, 'SUCCESS');
  });

  const wss = new WebSocketServer({ server, path: '/ws' });
  wss.on('connection', (ws, req) => {
    const url = new URL(req.url, `http://${config.host}:${config.port}`);
    if (url.searchParams.get('token') !== config.token) {
      ws.close(1008, 'unauthorized');
      return;
    }
    ws.send(JSON.stringify({ type: 'products.updated', products }));
  });

  const watchers = [];
  if (config.watchFolder && fs.existsSync(config.watchFolder)) watchers.push(createWatcher(config.watchFolder, refresh));
  if (config.nextcloudFolder && fs.existsSync(config.nextcloudFolder) && config.nextcloudFolder !== config.watchFolder) {
    watchers.push(createWatcher(config.nextcloudFolder, refresh));
  }

  return {
    close: async () => {
      for (const watcher of watchers) await watcher.close();
      wss.close();
      server.close();
    }
  };
}
