import fs from 'fs';
import path from 'path';

const root = path.resolve(process.cwd(), 'src');
const out = path.resolve(process.cwd(), 'build');

fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });

function copyRecursive(src, dst) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dst, { recursive: true });
    for (const child of fs.readdirSync(src)) copyRecursive(path.join(src, child), path.join(dst, child));
    return;
  }
  fs.copyFileSync(src, dst);
}

copyRecursive(root, out);
console.log(`Extension build ready: ${out}`);
