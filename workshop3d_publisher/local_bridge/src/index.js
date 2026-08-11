import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import { loadConfig, saveConfig, configPath } from './config.js';
import { startServer } from './server.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');

function init() {
  const cfg = loadConfig(rootDir);
  saveConfig(rootDir, cfg);
  fs.mkdirSync(path.join(rootDir, 'runtime', 'logs'), { recursive: true });
  console.log(`Initialized config: ${configPath(rootDir)}`);
  console.log(`Token: ${cfg.token}`);
}

async function start() {
  const cfg = loadConfig(rootDir);
  if (!fs.existsSync(cfg.watchFolder)) {
    console.warn(`Watch folder does not exist: ${cfg.watchFolder}`);
    console.warn('Update runtime/config.json and restart bridge.');
  }
  startServer({ config: cfg, rootDir });
  const pidFile = path.join(rootDir, 'runtime', 'bridge.pid');
  fs.writeFileSync(pidFile, String(process.pid), 'utf8');
  process.on('SIGINT', () => process.exit(0));
  process.on('SIGTERM', () => process.exit(0));
}

const cmd = process.argv[2] || 'start';
if (cmd === 'init') init();
else await start();
