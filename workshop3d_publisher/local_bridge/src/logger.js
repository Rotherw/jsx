import fs from 'fs';
import path from 'path';

export class Logger {
  constructor(logPath) {
    this.logPath = logPath;
    fs.mkdirSync(path.dirname(logPath), { recursive: true });
  }

  log(model, marketplace, action, result) {
    const line = `${new Date().toISOString()} [${model}] [${marketplace}] ${action} ${result}`;
    fs.appendFileSync(this.logPath, `${line}\n`, 'utf8');
    return line;
  }
}
