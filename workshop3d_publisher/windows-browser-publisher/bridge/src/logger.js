const fs = require('fs');
const path = require('path');
const { LOG_PATH } = require('./config');

function logLine(line) {
  const out = `${new Date().toISOString()} ${line}\n`;
  fs.mkdirSync(path.dirname(LOG_PATH), { recursive: true });
  fs.appendFileSync(LOG_PATH, out, 'utf8');
  console.log(line);
}

function format(model, marketplace, action, result) {
  return `[${model}] [${marketplace}] ${action} ${result}`;
}

module.exports = { logLine, format };
