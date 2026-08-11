import chokidar from 'chokidar';

export function createWatcher(watchFolder, onChange) {
  const watcher = chokidar.watch(watchFolder, {
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
