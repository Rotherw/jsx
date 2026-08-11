import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

const MODEL_EXT = new Set(['.stl', '.3mf', '.glb', '.obj', '.zip']);
const IMAGE_EXT = new Set(['.png', '.jpg', '.jpeg', '.webp']);

function inferMetadata(folderName, modelFiles, imageFiles) {
  const title = folderName.replace(/[_-]+/g, ' ').trim();
  const tags = [title.split(' ')[0], 'WorkShop3D'].filter(Boolean);
  return {
    title,
    description: `${title} 3D model package.`,
    tags,
    category: '',
    price: null,
    license: '',
    collection: '',
    brands: ['WorkShop3D', 'KF2.pl'],
    publish: {
      cults: true,
      thangs: true,
      creality: true,
      printables: false,
      makerworld: false,
      myminifactory: false,
      '3dexport': false
    },
    files: {
      models: modelFiles.map((f) => f.name),
      images: imageFiles.map((f) => f.name)
    }
  };
}

function readMetadata(folderPath, folderName, modelFiles, imageFiles) {
  const metadataPath = path.join(folderPath, 'metadata.json');
  if (!fs.existsSync(metadataPath)) {
    return inferMetadata(folderName, modelFiles, imageFiles);
  }
  try {
    const parsed = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
    return {
      ...inferMetadata(folderName, modelFiles, imageFiles),
      ...parsed,
      publish: { ...inferMetadata(folderName, modelFiles, imageFiles).publish, ...(parsed.publish || {}) }
    };
  } catch {
    return inferMetadata(folderName, modelFiles, imageFiles);
  }
}

function fileTypeByExt(ext) {
  if (MODEL_EXT.has(ext)) return 'model';
  if (IMAGE_EXT.has(ext)) return 'image';
  return 'other';
}

function readPublishState(folderPath) {
  const file = path.join(folderPath, 'publish-state.json');
  if (!fs.existsSync(file)) return {};
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return {};
  }
}

export function savePublishState(folderPath, nextState) {
  const file = path.join(folderPath, 'publish-state.json');
  fs.writeFileSync(file, JSON.stringify(nextState, null, 2), 'utf8');
}

export function scanProducts(watchFolder) {
  if (!watchFolder || !fs.existsSync(watchFolder)) return [];
  const entries = fs.readdirSync(watchFolder, { withFileTypes: true }).filter((d) => d.isDirectory());

  const products = entries.map((entry) => {
    const folderPath = path.join(watchFolder, entry.name);
    const files = fs.readdirSync(folderPath, { withFileTypes: true })
      .filter((f) => f.isFile())
      .map((f) => {
        const abs = path.join(folderPath, f.name);
        const ext = path.extname(f.name).toLowerCase();
        const stat = fs.statSync(abs);
        return {
          name: f.name,
          path: abs,
          ext,
          type: fileTypeByExt(ext),
          size: stat.size,
          mtime: stat.mtime.toISOString()
        };
      });

    const modelFiles = files.filter((f) => f.type === 'model');
    const imageFiles = files.filter((f) => f.type === 'image');
    const metadata = readMetadata(folderPath, entry.name, modelFiles, imageFiles);
    const publishState = readPublishState(folderPath);
    const id = crypto.createHash('sha1').update(folderPath).digest('hex').slice(0, 12);
    const ready = modelFiles.length > 0 && imageFiles.length > 0;

    return {
      id,
      name: metadata.title || entry.name,
      folderName: entry.name,
      folderPath,
      metadata,
      files,
      thumbnail: imageFiles[0]?.name || null,
      publishState,
      status: ready ? 'GOTOWE' : 'NOWE',
      validation: {
        ready,
        hasModel: modelFiles.length > 0,
        hasImage: imageFiles.length > 0
      },
      warnings: []
    };
  });

  const seen = new Map();
  for (const p of products) {
    const normalized = p.name.toLowerCase().replace(/[^a-z0-9]+/g, '');
    if (!normalized) continue;
    const list = seen.get(normalized) || [];
    list.push(p.id);
    seen.set(normalized, list);
  }
  for (const p of products) {
    const normalized = p.name.toLowerCase().replace(/[^a-z0-9]+/g, '');
    const list = seen.get(normalized) || [];
    if (list.length > 1) p.warnings.push('Possible duplicate');
  }

  return products;
}
