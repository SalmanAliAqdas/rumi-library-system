import labels from './labels.js';
import {searchBooks, compareText} from './search.js';
import {MAX_BYTES, readBounded, safeCoverUrl, validateSnapshot} from './snapshot.js';
import {readState, replaceCatalog, removeCatalog, removeCovers, readCover, saveCover} from './store.js';

const $ = id => document.getElementById(id);
const languageIndex = {en: 0, ur: 1, ar: 2};
let uiLanguage = 'en', state = {revision: null, snapshot: null}, shellReady = false, busy = false, pageNumber = 1;
let statusKey = 'setup', statusExtra = '', statusError = false, activeController = null, renderNumber = 0;
const objectUrls = new Set();
let channel;
try { channel = new BroadcastChannel('rumi-library-public-offline'); } catch { /* Focus refresh also covers older browsers. */ }
try { uiLanguage = localStorage.getItem('rumi-offline-language') || 'en'; } catch { /* Storage errors are handled by the catalogue store. */ }
if (!(uiLanguage in languageIndex)) uiLanguage = 'en';
function t(key) { return labels[key]?.[languageIndex[uiLanguage]] ?? key; }
function el(tag, text, className) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; }
function link(text, href) { const node = el('a', text); node.href = href; return node; }
function notify() { channel?.postMessage('changed'); }
function setStatus(key, extra = '', error = false) { statusKey = key; statusExtra = extra; statusError = error; $('status').textContent = t(key) + (extra ? ' ' + extra : ''); $('status').classList.toggle('error', error); }
function connectivity() {
  $('connection').textContent = t(navigator.onLine ? 'browser_online' : 'browser_offline');
  document.querySelectorAll('[data-online-link]').forEach(node => node.setAttribute('aria-disabled', String(!navigator.onLine)));
}
function updateControls() {
  $('download').textContent = t(state.snapshot ? 'update_catalog' : 'download_catalog');
  $('download').disabled = busy || !shellReady;
  $('remove').hidden = !state.snapshot;
  // Removal can invalidate an in-flight update; the revision guard prevents resurrection.
  $('remove').disabled = false;
  $('cancel').hidden = !busy;
  $('download-covers').disabled = busy || !state.snapshot;
  $('remove-covers').disabled = !state.snapshot;
}
function localizedCategory(category) { return category[`name_${uiLanguage}`] || category.name; }
function options(select, records, allLabel, getValue, getLabel) {
  const previous = select.value;
  select.replaceChildren(new Option(t(allLabel), ''));
  records.sort((a, b) => compareText(getLabel(a), getLabel(b))).forEach(record => select.add(new Option(getLabel(record), getValue(record))));
  if ([...select.options].some(option => option.value === previous)) select.value = previous;
}
function translate() {
  document.documentElement.lang = uiLanguage;
  document.documentElement.dir = uiLanguage === 'en' ? 'ltr' : 'rtl';
  document.title = t('offline_catalog') + ' · Rumi Library';
  $('offline-language').value = uiLanguage;
  document.querySelectorAll('[data-i18n]').forEach(node => { node.textContent = t(node.dataset.i18n); });
  document.querySelectorAll('[data-placeholder]').forEach(node => { node.placeholder = t(node.dataset.placeholder); });
  $('progress').setAttribute('aria-label', t('downloading'));
  $('pagination').setAttribute('aria-label', t('page_navigation'));
  const books = state.snapshot?.editions || [], categories = new Map(), languages = new Map();
  books.forEach(book => { book.categories.forEach(c => categories.set(c.slug, c)); book.languages.forEach(l => languages.set(l.code, l)); });
  options($('category'), [...categories.values()], 'all_subjects', c => c.slug, localizedCategory);
  options($('language'), [...languages.values()], 'all_languages', l => l.code, l => l.name);
  const previous = $('availability').value;
  $('availability').replaceChildren(new Option(t('all_availability'), ''), new Option(t('available'), 'available'), new Option(t('on_loan'), 'on_loan'));
  $('availability').value = previous;
  connectivity(); updateControls(); setStatus(statusKey, statusExtra, statusError); render();
}
function summary() {
  $('download-summary').replaceChildren();
  if (!state.snapshot) return;
  const formatter = new Intl.DateTimeFormat(uiLanguage, {dateStyle: 'medium', timeStyle: 'short'});
  for (const [label, value] of [
    ['saved_editions', String(state.snapshot.edition_count)], ['saved_copies', String(state.snapshot.copy_count)],
    ['last_download', formatter.format(new Date(state.downloadedAt))], ['snapshot_time', formatter.format(new Date(state.snapshot.generated_at))],
  ]) { const p = el('p'); p.append(el('span', t(label) + ': '), el('strong', value)); $('download-summary').append(p); }
}
function clearImages() { renderNumber++; objectUrls.forEach(url => URL.revokeObjectURL(url)); objectUrls.clear(); }
function art(book) {
  const box = el('div', undefined, `book-art tone-${book.id % 4 + 1}`);
  const placeholder = el('div', undefined, 'cover-placeholder');
  const title = el('span', book.title, 'cover-title'); title.lang = book.original_language; title.dir = 'auto';
  placeholder.append(el('span', '✧', 'cover-ornament'), title, el('small', 'RUMI LIBRARY')); box.append(placeholder);
  const generation = renderNumber, coverUrl = safeCoverUrl(book.cover_url);
  if (coverUrl) readCover(coverUrl).then(blob => {
    if (!blob || generation !== renderNumber || !box.isConnected) return;
    const url = URL.createObjectURL(blob); objectUrls.add(url);
    const image = el('img'); image.alt = ''; image.src = url;
    image.onload = () => box.classList.add('has-cover'); image.onerror = () => image.remove(); box.append(image);
  }).catch(() => {});
  return box;
}
function savedUrl(id) { const url = new URL(location.href); url.searchParams.set('book', id); return url.pathname + url.search; }
function card(book) {
  const article = el('article', undefined, 'book-card'), anchor = link('', savedUrl(book.id)); anchor.className = 'book-link';
  const title = el('h3', book.title); title.lang = book.original_language; title.dir = 'auto';
  const names = el('p', book.contributors.map(c => c.name).join(' · '), 'credit'); names.dir = 'auto';
  anchor.append(art(book), el('div', book.categories.map(localizedCategory).join(' · '), 'card-meta'), title, names,
    el('div', book.languages.map(l => l.name).join(' / ') + ' · ' + book.copies.length + ' ◇', 'card-bottom'));
  article.append(anchor);
  if (book.is_demo) article.append(el('small', t('fictional'), 'demo-label'));
  return article;
}
function filters() { return {q: $('q').value, category: $('category').value, language: $('language').value, availability: $('availability').value}; }
function renderList() {
  $('results').replaceChildren(); $('pagination').replaceChildren(); $('result-count').textContent = '';
  if (!state.snapshot) { $('results').append(el('p', t('no_download'), 'empty')); return; }
  if (!state.snapshot.editions.length) { $('results').append(el('p', t('empty_catalog'), 'empty')); return; }
  const results = searchBooks(state.snapshot.editions, filters()), pages = Math.max(1, Math.ceil(results.length / 12));
  pageNumber = Math.min(Math.max(1, pageNumber), pages);
  $('result-count').textContent = results.length + ' ' + t('results');
  results.slice((pageNumber - 1) * 12, pageNumber * 12).forEach(book => $('results').append(card(book)));
  if (!results.length) $('results').append(el('p', t('no_results'), 'empty'));
  for (const [label, number] of [['previous', pageNumber - 1], ['next', pageNumber + 1]]) {
    const button = el('button', t(label)); button.disabled = number < 1 || number > pages;
    button.onclick = () => { pageNumber = number; writeLocation(); render(); $('saved-heading').scrollIntoView(); };
    $('pagination').append(button);
    if (label === 'previous') $('pagination').append(el('span', `${pageNumber} / ${pages}`));
  }
}
function renderDetail(id) {
  const area = $('book-detail'); area.replaceChildren();
  const url = new URL(location.href); url.searchParams.delete('book');
  area.append(link('← ' + t('catalog'), url.pathname + url.search));
  const book = state.snapshot?.editions.find(record => String(record.id) === id);
  if (!book) { area.append(el('p', t('saved_detail_missing'), 'empty')); return; }
  const grid = el('div', undefined, 'offline-book-detail'), content = el('div');
  const title = el('h1', book.title); title.lang = book.original_language; title.dir = 'auto'; content.append(title);
  if (book.is_demo) content.append(el('p', t('fictional'), 'demo-label'));
  for (const credit of book.contributors) { const p = el('p', t(credit.role) + ': '); p.append(el('bdi', credit.name)); content.append(p); }
  content.append(el('p', book.languages.map(l => l.name).join(' / ')), el('p', book.categories.map(localizedCategory).join(' · ')), el('h2', t('about')));
  const description = el('p', book.summary || t('no_summary'), 'summary'); description.dir = 'auto'; content.append(description);
  const metadata = el('dl', undefined, 'metadata');
  for (const [key, value] of [['publisher', book.publisher], ['edition', book.edition], ['year', book.year], ['ISBN', book.isbn]]) if (value) {
    const row = el('div'), detail = el('dd'); detail.append(el('bdi', String(value))); row.append(el('dt', t(key)), detail); metadata.append(row);
  }
  content.append(metadata, el('h2', t('location')), el('p', t('availability_at_update') + ' · ' + t('freshness'), 'muted'));
  const copies = el('ul', undefined, 'copy-list');
  for (const copy of book.copies) {
    const row = el('li'), location = el('div'), number = el('strong'); number.append(el('bdi', copy.accession)); location.append(number);
    const shelf = el('p', t('shelf') + ': '); shelf.append(el('bdi', copy.shelf));
    if (copy.volume) shelf.append(document.createTextNode(' · ' + t('volume') + ': '), el('bdi', copy.volume));
    location.append(shelf); row.append(location, el('span', t(copy.available ? 'available' : 'on_loan'), 'availability' + (copy.available ? '' : ' loaned'))); copies.append(row);
  }
  content.append(copies);
  const online = link(t('online_catalog'), book.url); online.dataset.onlineLink = ''; content.append(online);
  grid.append(art(book), content); area.append(grid); connectivity();
}
function render() {
  clearImages(); summary(); updateControls();
  const id = new URL(location.href).searchParams.get('book');
  $('saved-books').hidden = Boolean(id); $('book-detail').hidden = !id;
  if (id) renderDetail(id); else renderList();
}
function writeLocation() {
  const url = new URL(location.href);
  for (const [key, value] of Object.entries(filters())) { if (value) url.searchParams.set(key, value); else url.searchParams.delete(key); }
  url.searchParams.set('page', pageNumber); history.replaceState(null, '', url);
}
async function reloadState() {
  try {
    const saved = await readState();
    if (saved.snapshot) validateSnapshot(saved.snapshot);
    state = saved; translate();
  } catch (error) { setStatus(error.message === 'invalid_snapshot' ? 'invalid_snapshot' : 'storage_failed', '', true); }
}
function reportError(error) { setStatus(['invalid_snapshot', 'storage_failed', 'catalog_changed', 'snapshot_limit_exceeded'].includes(error.message) ? error.message : 'download_failed', '', true); }
async function download() {
  if (busy || !shellReady) return;
  busy = true; updateControls(); $('progress').hidden = false; $('progress').removeAttribute('value');
  activeController = new AbortController();
  const timer = setTimeout(() => activeController?.abort(), 45000), expectedRevision = state.revision;
  setStatus('downloading');
  try {
    const response = await fetch('/catalog/public-snapshot.json', {credentials: 'omit', cache: 'no-store', redirect: 'error', signal: activeController.signal});
    if (response.status === 503 && response.headers.get('X-Rumi-Snapshot-Error') === 'limit') throw new Error('snapshot_limit_exceeded');
    if (!(response.headers.get('content-type') || '').includes('application/json')) throw new Error('invalid_snapshot');
    const bytes = await readBounded(response, {onProgress: (received, total) => {
      if (total) { $('progress').max = total; $('progress').value = received; }
      setStatus('downloading', `${Math.ceil(received / 1024)} KB`);
    }});
    if (activeController.signal.aborted) throw new Error('download_failed');
    let snapshot;
    try { snapshot = validateSnapshot(JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes))); } catch { throw new Error('invalid_snapshot'); }
    setStatus('validating');
    state = await replaceCatalog(snapshot, expectedRevision);
    notify(); translate(); setStatus('download_success');
  } catch (error) { if (error.message === 'catalog_changed') await reloadState(); reportError(error); }
  finally { clearTimeout(timer); busy = false; activeController = null; $('progress').hidden = true; updateControls(); }
}
async function covers() {
  if (busy || !state.snapshot) return;
  busy = true; updateControls(); activeController = new AbortController();
  const expected = {...state}, queue = [...new Set(state.snapshot.editions.map(book => safeCoverUrl(book.cover_url)).filter(Boolean))].slice(0, 100);
  let saved = 0, attempted = 0, usedBytes = 0;
  try {
    await Promise.all(Array.from({length: 3}, async () => {
      while (queue.length && usedBytes < MAX_BYTES && !activeController.signal.aborted) {
        const url = queue.shift(); attempted++;
        const controller = new AbortController(), abort = () => controller.abort();
        activeController.signal.addEventListener('abort', abort, {once: true});
        const timer = setTimeout(abort, 12000);
        try {
          const response = await fetch(url, {mode: 'cors', credentials: 'omit', referrerPolicy: 'no-referrer', redirect: 'error', signal: controller.signal});
          const type = (response.headers.get('content-type') || '').split(';')[0];
          if (!/^image\/(png|jpeg|webp|gif|avif)$/.test(type)) continue;
          const data = await readBounded(response, {limit: 2 * 1024 * 1024});
          if (activeController.signal.aborted) continue;
          if (usedBytes + data.byteLength > MAX_BYTES) { queue.length = 0; continue; }
          usedBytes += data.byteLength;
          await saveCover(url, new Blob([data], {type}), expected); saved++;
        } catch { /* Optional covers cannot invalidate a successful core download. */ }
        finally { clearTimeout(timer); activeController.signal.removeEventListener('abort', abort); }
        setStatus('covers_done', `${saved} / ${attempted}`);
      }
    }));
    setStatus('covers_done', `${saved} / ${attempted}`); notify(); render();
  } finally { busy = false; activeController = null; updateControls(); }
}
async function setupWorker() {
  if (!isSecureContext || !('serviceWorker' in navigator)) { setStatus('https_required', '', true); return; }
  let timeout;
  try {
    const existing = await navigator.serviceWorker.getRegistration('/offline/');
    if (existing?.active) {
      shellReady = true;
      // Check updates in the background; failure must not disable the working shell.
      existing.update().catch(() => {});
    } else await navigator.serviceWorker.register('/offline/sw.js', {scope: '/offline/', updateViaCache: 'none'});
    await Promise.race([navigator.serviceWorker.ready, new Promise((_, reject) => { timeout = setTimeout(() => reject(new Error()), 20000); })]);
    shellReady = true; if (!statusError) setStatus(state.snapshot ? 'freshness' : 'no_download');
  } catch { setStatus('shell_failed', '', true); }
  finally { clearTimeout(timeout); updateControls(); }
}
$('download').onclick = download;
$('cancel').onclick = () => activeController?.abort();
$('download-covers').onclick = covers;
$('remove').onclick = async () => {
  if (!confirm(t('confirm_remove'))) return;
  activeController?.abort();
  try { state = await removeCatalog(); notify(); translate(); setStatus('removed'); } catch (error) { reportError(error); }
};
$('remove-covers').onclick = async () => {
  if (!confirm(t('confirm_covers'))) return;
  activeController?.abort();
  try { state = await removeCovers(); notify(); render(); setStatus('covers_removed'); } catch (error) { reportError(error); }
};
$('offline-language').onchange = () => {
  uiLanguage = $('offline-language').value;
  try { localStorage.setItem('rumi-offline-language', uiLanguage); } catch { /* UI still switches in memory. */ }
  translate();
};
$('offline-search').onsubmit = event => { event.preventDefault(); pageNumber = 1; writeLocation(); render(); };
$('display').onclick = () => {
  document.body.classList.toggle('display-mode'); $('display').textContent = t(document.body.classList.contains('display-mode') ? 'exit_display' : 'display');
  $('fullscreen').hidden = !document.fullscreenEnabled || !document.body.classList.contains('display-mode');
};
$('fullscreen').onclick = async () => { try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); } catch { $('fullscreen').hidden = true; } };
document.addEventListener('click', event => {
  const anchor = event.target.closest('a');
  if (anchor?.hasAttribute('data-online-link') && !navigator.onLine) { event.preventDefault(); setStatus('online_required', '', true); }
});
let installPrompt;
window.addEventListener('beforeinstallprompt', event => { event.preventDefault(); installPrompt = event; $('install').hidden = false; });
$('install').onclick = async () => { if (!installPrompt) return; try { await installPrompt.prompt(); await installPrompt.userChoice; } finally { installPrompt = null; $('install').hidden = true; } };
window.addEventListener('appinstalled', () => { installPrompt = null; $('install').hidden = true; });
window.addEventListener('online', connectivity); window.addEventListener('offline', connectivity);
window.addEventListener('focus', () => { if (!busy) reloadState(); });
if (channel) channel.onmessage = () => { if (!busy) reloadState(); };
window.addEventListener('pagehide', () => { activeController?.abort(); clearImages(); });
const parameters = new URL(location.href).searchParams;
$('q').value = (parameters.get('q') || '').slice(0, 200);
pageNumber = Math.max(1, Math.min(10000, Number(parameters.get('page')) || 1));
await reloadState();
for (const key of ['category', 'language', 'availability']) if ([...$(key).options].some(o => o.value === parameters.get(key))) $(key).value = parameters.get(key);
render(); await setupWorker();
