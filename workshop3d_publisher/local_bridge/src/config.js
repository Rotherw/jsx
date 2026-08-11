import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

const DEFAULT_CONFIG = {
  watchFolder: 'F:\\Gotowe do sklepu',
  nextcloudFolder: '',
  safeMode: true,
  browser: 'chrome',
  host: '127.0.0.1',
  port: 18777,
  token: ''
};

export function runtimeDir(rootDir) {
  return path.join(rootDir, 'runtime');
}

export function configPath(rootDir) {
  return path.join(runtimeDir(rootDir), 'config.json');
}

export function loadConfig(rootDir) {
  const file = configPath(rootDir);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  if (!fs.existsSync(file)) {
    const cfg = { ...DEFAULT_CONFIG, token: crypto.randomBytes(24).toString('hex') };
    fs.writeFileSync(file, JSON.stringify(cfg, null, 2), 'utf8');
    return cfg;
  }
  const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (!parsed.token) parsed.token = crypto.randomBytes(24).toString('hex');
  return { ...DEFAULT_CONFIG, ...parsed };
}

export function saveConfig(rootDir, config) {
  const file = configPath(rootDir);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(config, null, 2), 'utf8');
}
