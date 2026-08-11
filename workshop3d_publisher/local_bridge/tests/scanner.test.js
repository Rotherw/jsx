import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { scanProducts } from '../src/scanner.js';

function makeTmpProduct(withMetadata = false) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'w3d-'));
  const p = path.join(root, 'Castle Gate');
  fs.mkdirSync(p);
  fs.writeFileSync(path.join(p, 'castle.stl'), 'solid');
  fs.writeFileSync(path.join(p, 'thumb.png'), 'pngdata');
  if (withMetadata) {
    fs.writeFileSync(path.join(p, 'metadata.json'), JSON.stringify({ title: 'Castle Gate Pro', publish: { cults: true } }));
  }
  return root;
}

test('scanProducts infers metadata when missing', () => {
  const root = makeTmpProduct(false);
  const products = scanProducts(root);
  assert.equal(products.length, 1);
  assert.equal(products[0].validation.ready, true);
  assert.equal(products[0].metadata.publish.cults, true);
});

test('scanProducts reads metadata.json when present', () => {
  const root = makeTmpProduct(true);
  const products = scanProducts(root);
  assert.equal(products[0].name, 'Castle Gate Pro');
});
