import chokidar from 'chokidar';
import path from 'path';

function normalizeWatchPath(input) {
  if (!input) throw new Error('watch path is empty');
  const resolved = path.resolve(String(input));
  if (!path.isAbsolute(resolved)) throw new Error('watch path must be absolute');
  return resolved;
}

export function createWatcher(watchFolder, onChange) {
  const safeWatchFolder = normalizeWatchPath(watchFolder);
  const watcher = chokidar.watch(safeWatchFolder, {
    ignoreInitial: true,
    depth: 2,
    awaitWriteFinish: {
      stabilityThreshold: 1200,
      pollInterval: 200
    }
  });

  const handler = () => onChange();
  watcher.on('add', handler).on('change', handler).on('unlink', handler).on('addDir', handler).on('unlinkDir', handler);
  return watcher;
}
