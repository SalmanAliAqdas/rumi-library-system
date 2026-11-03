import {validateSnapshot} from './snapshot.js';
const DB_NAME = 'rumi-library-public-offline';
const DB_VERSION = 1;
function storageError() { return new Error('storage_failed'); }
export function openStore() {
  return new Promise((resolve, reject) => {
    let request;
    try { request = indexedDB.open(DB_NAME, DB_VERSION); } catch { reject(storageError()); return; }
    let settled = false;
    const timer = setTimeout(() => { settled = true; reject(storageError()); }, 5000);
    request.onupgradeneeded = () => { const db = request.result; db.createObjectStore('state'); db.createObjectStore('covers', {keyPath: 'url'}); };
    request.onerror = request.onblocked = () => { clearTimeout(timer); settled = true; reject(storageError()); };
    request.onsuccess = () => { clearTimeout(timer); const db = request.result; if (settled) { db.close(); return; } settled = true; db.onversionchange = () => db.close(); resolve(db); };
  });
}
async function transaction(stores, mode, operation) {
  const db = await openStore();
  return new Promise((resolve, reject) => {
    let result, failure, tx;
    const timer = setTimeout(() => { failure = storageError(); try { tx.abort(); } catch { db.close(); reject(failure); } }, 10000);
    try {
      tx = db.transaction(stores, mode);
      tx.oncomplete = () => { clearTimeout(timer); db.close(); resolve(result); };
      tx.onabort = tx.onerror = () => { clearTimeout(timer); db.close(); reject(failure || storageError()); };
      operation(tx, value => { result = value; }, error => { failure = error; tx.abort(); });
    } catch { clearTimeout(timer); try { tx?.abort(); } catch { /* Already inactive. */ } db.close(); reject(storageError()); }
  });
}
export function readState() {
  return transaction(['state'], 'readonly', (tx, done) => {
    const request = tx.objectStore('state').get('active');
    request.onsuccess = () => done(request.result || {revision: null, coverRevision: null, snapshot: null, downloadedAt: null});
  });
}
const revision = () => crypto.randomUUID();
export function replaceCatalog(snapshot, expectedRevision) {
  validateSnapshot(snapshot);
  return transaction(['state', 'covers'], 'readwrite', (tx, done, abort) => {
    const store = tx.objectStore('state'), request = store.get('active');
    request.onsuccess = () => {
      try {
      if ((request.result?.revision ?? null) !== expectedRevision) { abort(new Error('catalog_changed')); return; }
      const state = {revision: revision(), coverRevision: revision(), snapshot, downloadedAt: new Date().toISOString()};
      store.put(state, 'active'); tx.objectStore('covers').clear(); done(state);
      } catch { abort(storageError()); }
    };
  });
}
export function removeCatalog() {
  return transaction(['state', 'covers'], 'readwrite', (tx, done) => {
    const state = {revision: revision(), coverRevision: revision(), snapshot: null, downloadedAt: null};
    tx.objectStore('state').put(state, 'active'); tx.objectStore('covers').clear(); done(state);
  });
}
export function removeCovers() {
  return transaction(['state', 'covers'], 'readwrite', (tx, done, abort) => {
    const store = tx.objectStore('state'), request = store.get('active');
    request.onsuccess = () => {
      try {
      const state = {...request.result, coverRevision: revision()};
      store.put(state, 'active'); tx.objectStore('covers').clear(); done(state);
      } catch { abort(storageError()); }
    };
  });
}
export function saveCover(url, blob, expected) {
  return transaction(['state', 'covers'], 'readwrite', (tx, done, abort) => {
    const request = tx.objectStore('state').get('active');
    request.onsuccess = () => {
      try {
      const current = request.result;
      if (!current?.snapshot || current.revision !== expected.revision || current.coverRevision !== expected.coverRevision) { abort(new Error('catalog_changed')); return; }
      const store = tx.objectStore('covers'), covers = store.getAll();
      covers.onsuccess = () => {
        try {
          const other = covers.result.filter(cover => cover.url !== url);
          if (blob.size > 2 * 1024 * 1024 || other.length >= 100 || other.reduce((size, cover) => size + cover.blob.size, 0) + blob.size > 20 * 1024 * 1024) { abort(storageError()); return; }
          store.put({url, blob}); done(true);
        } catch { abort(storageError()); }
      };
      } catch { abort(storageError()); }
    };
  });
}
export function readCover(url) {
  return transaction(['covers'], 'readonly', (tx, done) => { const request = tx.objectStore('covers').get(url); request.onsuccess = () => done(request.result?.blob || null); });
}
