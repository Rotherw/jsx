const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const src = path.join(root, 'extension', 'src');
const out = path.join(root, 'extension', 'build');
const manifestSrc = path.join(root, 'extension', 'manifest.json');

function copyDir(srcDir, outDir) {
  fs.mkdirSync(outDir, { recursive: true });
  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const from = path.join(srcDir, entry.name);
    const to = path.join(outDir, entry.name);
    if (entry.isDirectory()) copyDir(from, to);
    else fs.copyFileSync(from, to);
  }
}

if (fs.existsSync(out)) fs.rmSync(out, { recursive: true, force: true });
copyDir(src, out);
fs.copyFileSync(manifestSrc, path.join(out, 'manifest.json'));
console.log(`Extension build ready: ${out}`);
