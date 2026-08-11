const fs = require('fs');
const path = require('path');
const { readJson, writeJson } = require('./config');

const MODEL_EXTENSIONS = new Set(['.stl', '.3mf', '.glb', '.obj', '.zip']);
const IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.webp']);

function listFilesRecursive(dir) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const name of fs.readdirSync(dir)) {
    const fullPath = path.join(dir, name);
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      out.push(...listFilesRecursive(fullPath));
    } else {
      out.push(fullPath);
    }
  }
  return out;
}

function parseMetadata(folderPath, files) {
  const metadataPath = path.join(folderPath, 'metadata.json');
  const fallbackTitle = path.basename(folderPath);
  const firstModel = files.find((f) => MODEL_EXTENSIONS.has(path.extname(f).toLowerCase()));
  const inferredTitle = firstModel ? path.basename(firstModel, path.extname(firstModel)) : fallbackTitle;
  const defaults = {
    title: inferredTitle || fallbackTitle,
    description: `Model 3D: ${inferredTitle || fallbackTitle}`,
    tags: [],
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
    }
  };

  const loaded = readJson(metadataPath, {});
  const merged = {
    ...defaults,
    ...loaded,
    tags: Array.isArray(loaded.tags) ? loaded.tags : defaults.tags,
    brands: Array.isArray(loaded.brands) && loaded.brands.length ? loaded.brands : defaults.brands,
    publish: { ...defaults.publish, ...(loaded.publish || {}) }
  };

  if (!fs.existsSync(metadataPath)) {
    writeJson(metadataPath, merged);
  }

  return merged;
}

function getPublishStatePath(folderPath) {
  return path.join(folderPath, 'publish-state.json');
}

function loadPublishState(folderPath) {
  return readJson(getPublishStatePath(folderPath), {});
}

function updatePublishState(folderPath, marketplace, state) {
  const pathState = getPublishStatePath(folderPath);
  const current = readJson(pathState, {});
  current[marketplace] = {
    ...state,
    date: new Date().toISOString()
  };
  writeJson(pathState, current);
  return current;
}

function isReadyProduct(files) {
  const models = files.filter((f) => MODEL_EXTENSIONS.has(path.extname(f).toLowerCase()));
  const images = files.filter((f) => IMAGE_EXTENSIONS.has(path.extname(f).toLowerCase()));
  return models.length > 0 && images.length > 0;
}

function toRelative(folderPath, fullPath) {
  return path.relative(folderPath, fullPath).replace(/\\/g, '/');
}

function mapProduct(folderPath) {
  const allFiles = listFilesRecursive(folderPath);
  const metadata = parseMetadata(folderPath, allFiles);
  const files = allFiles.map((fullPath) => ({
    name: path.basename(fullPath),
    relativePath: toRelative(folderPath, fullPath),
    fullPath,
    ext: path.extname(fullPath).toLowerCase()
  }));

  const modelFiles = files.filter((f) => MODEL_EXTENSIONS.has(f.ext));
  const imageFiles = files.filter((f) => IMAGE_EXTENSIONS.has(f.ext));

  return {
    id: path.basename(folderPath),
    folderPath,
    title: metadata.title,
    metadata,
    files,
    modelFiles,
    imageFiles,
    ready: isReadyProduct(allFiles),
    publishState: loadPublishState(folderPath)
  };
}

function scanProducts(watchFolder) {
  if (!fs.existsSync(watchFolder)) return [];
  return fs
    .readdirSync(watchFolder)
    .map((name) => path.join(watchFolder, name))
    .filter((p) => fs.existsSync(p) && fs.statSync(p).isDirectory())
    .map(mapProduct);
}

module.exports = {
  scanProducts,
  updatePublishState
};
