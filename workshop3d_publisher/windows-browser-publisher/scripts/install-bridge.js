const fs = require('fs');
const path = require('path');
const { randomBytes } = require('crypto');

const root = path.resolve(__dirname, '..');
const configPath = path.join(root, 'config', 'config.json');
const extensionTokenPath = path.join(root, 'extension', 'src', 'bridge-token.json');

const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'));
if (!cfg.token || cfg.token === 'CHANGE_ME_LOCAL_TOKEN') {
  cfg.token = randomBytes(24).toString('hex');
  fs.writeFileSync(configPath, JSON.stringify(cfg, null, 2));
}
fs.writeFileSync(extensionTokenPath, JSON.stringify({ token: cfg.token, host: cfg.bridgeHost || '127.0.0.1', port: cfg.bridgePort || 17373 }, null, 2));
console.log('Bridge config ready.');
