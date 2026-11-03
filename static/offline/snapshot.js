import {normalize, isbnKey} from './search.js';
export const MAX_BYTES = 20 * 1024 * 1024;
const fail = () => { throw new Error('invalid_snapshot'); };
function object(value, keys) {
  if (!value || Array.isArray(value) || typeof value !== 'object' || Object.keys(value).sort().join('|') !== [...keys].sort().join('|')) fail();
}
function text(value, max = 100000) { if (typeof value !== 'string' || value.length > max) fail(); }
function array(value, max) { if (!Array.isArray(value) || value.length > max) fail(); }
function same(value, expected) { if (JSON.stringify(value) !== JSON.stringify(expected)) fail(); }
export function safeCoverUrl(value) {
  if (!value) return '';
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : ''; } catch { return ''; }
}
export function validateSnapshot(snapshot) {
  object(snapshot, ['schema_version', 'normalization_version', 'generated_at', 'edition_count', 'copy_count', 'editions']);
  if (snapshot.schema_version !== 1 || snapshot.normalization_version !== 1) fail();
  text(snapshot.generated_at, 40);
  if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}\+00:00$/.test(snapshot.generated_at) || !Number.isFinite(Date.parse(snapshot.generated_at))) fail();
  array(snapshot.editions, 5000);
  const ids = new Set(), accessions = new Set(); let copies = 0;
  for (const book of snapshot.editions) {
    object(book, ['id', 'title', 'original_language', 'aliases', 'contributors', 'languages', 'categories', 'isbn', 'publisher', 'edition', 'year', 'summary', 'cover_url', 'is_demo', 'url', 'copies', 'search']);
    if (!Number.isSafeInteger(book.id) || book.id < 1 || ids.has(book.id)) fail();
    ids.add(book.id);
    for (const key of ['title', 'original_language', 'isbn', 'publisher', 'edition', 'summary', 'cover_url', 'url']) text(book[key]);
    if (!book.title || book.url !== `/books/${book.id}/` || typeof book.is_demo !== 'boolean' || !(book.year === null || Number.isInteger(book.year))) fail();
    array(book.aliases, 1000); book.aliases.forEach(a => text(a));
    array(book.contributors, 1000);
    book.contributors.forEach(person => { object(person, ['name', 'role']); text(person.name, 200); if (!['author', 'translator', 'editor', 'commentator'].includes(person.role)) fail(); });
    array(book.languages, 1000);
    book.languages.forEach(lang => { object(lang, ['code', 'name']); text(lang.code, 12); text(lang.name, 60); });
    array(book.categories, 1000);
    book.categories.forEach(category => { object(category, ['slug', 'name', 'name_ur', 'name_ar']); text(category.slug, 50); ['name', 'name_ur', 'name_ar'].forEach(k => text(category[k], 100)); });
    array(book.copies, 10000); if (!book.copies.length) fail();
    for (const copy of book.copies) {
      object(copy, ['accession', 'volume', 'shelf', 'available']);
      text(copy.accession, 24); text(copy.volume, 80); text(copy.shelf, 60);
      if (!/^RL-\d{6,}$/.test(copy.accession) || accessions.has(copy.accession) || typeof copy.available !== 'boolean') fail();
      accessions.add(copy.accession); copies++;
    }
    object(book.search, ['title', 'aliases', 'contributors', 'subjects', 'isbn', 'summary']);
    const expected = {title: normalize(book.title), aliases: book.aliases.map(normalize), contributors: book.contributors.map(p => normalize(p.name)), subjects: book.categories.flatMap(c => ['name', 'name_ur', 'name_ar'].map(k => normalize(c[k]))), isbn: isbnKey(book.isbn), summary: normalize(book.summary)};
    for (const key of Object.keys(expected)) same(book.search[key], expected[key]);
  }
  if (snapshot.edition_count !== ids.size || snapshot.copy_count !== copies || copies > 10000) fail();
  return snapshot;
}
export async function readBounded(response, {limit = MAX_BYTES, onProgress = () => {}} = {}) {
  if (!response.ok || response.redirected) throw new Error('download_failed');
  const declared = Number(response.headers.get('content-length'));
  if (declared > limit) fail();
  const reader = response.body?.getReader();
  if (!reader) { const buffer = await response.arrayBuffer(); if (buffer.byteLength > limit) fail(); return new Uint8Array(buffer); }
  const chunks = []; let size = 0;
  try {
    while (true) {
      const {done, value} = await reader.read(); if (done) break;
      size += value.byteLength;
      if (size > limit) fail();
      chunks.push(value); onProgress(size, declared || null);
    }
  } catch (error) { await reader.cancel().catch(() => {}); throw error; }
  const all = new Uint8Array(size); let offset = 0;
  chunks.forEach(chunk => { all.set(chunk, offset); offset += chunk.length; });
  return all;
}
