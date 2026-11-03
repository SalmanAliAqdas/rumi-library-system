import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {normalize, isbnKey, searchBooks} from '../static/offline/search.js';
import {validateSnapshot, readBounded} from '../static/offline/snapshot.js';

const fixtures = JSON.parse(fs.readFileSync(new URL('./fixtures/search_parity.json', import.meta.url)));
const books = fixtures.books.map(source => {
  const aliases = source.aliases ? source.aliases.split('\n') : [];
  return {...source, original_language: 'en', aliases, contributors: [], categories: [], languages: [], publisher: '', edition: '', year: null, cover_url: '', is_demo: true, url: `/books/${source.id}/`, copies: [{accession: `RL-${String(source.id).padStart(6, '0')}`, volume: '', shelf: 'Fixture', available: true}], search: {title: normalize(source.title), aliases: aliases.map(normalize), contributors: [], subjects: [], isbn: isbnKey(source.isbn), summary: normalize(source.summary)}};
});
const snapshot = () => ({schema_version: 1, normalization_version: 1, generated_at: '2026-11-03T01:00:00.000000+00:00', edition_count: books.length, copy_count: books.length, editions: structuredClone(books)});
test('normalization and ranking match shared Python fixtures', () => {
  for (const [text, expected] of fixtures.normalization) assert.equal(normalize(text), expected, text);
  for (const [q, expected] of fixtures.ranking) assert.deepEqual(searchBooks(books, {q}).map(b => b.id), expected, q);
});
test('snapshot validation rejects private, inconsistent, malformed and future structures', () => {
  assert.equal(validateSnapshot(snapshot()).editions.length, 6);
  for (const change of [s => s.schema_version++, s => s.copy_count++, s => s.editions[0].borrower = 'private', s => s.editions[0].copies = [], s => s.editions[0].search.title = 'corrupt', s => s.editions[0].url = '/admin/', s => s.editions[0].copies[0].available = 'yes', s => s.editions.push(s.editions[0])]) {
    const value = snapshot(); change(value); assert.throws(() => validateSnapshot(value), /invalid_snapshot/);
  }
});
test('empty catalogue is valid and bounded search yields no result for invalid input', () => {
  assert.equal(validateSnapshot({...snapshot(), edition_count: 0, copy_count: 0, editions: []}).edition_count, 0);
  assert.deepEqual(searchBooks(books, {q: 'x'.repeat(201)}), []);
  assert.deepEqual(searchBooks(books, {availability: 'private'}), []);
});
test('stream reader enforces bounds, rejects HTTP errors and reports progress', async () => {
  let progress = 0;
  assert.equal((await readBounded(new Response('abc'), {onProgress: n => progress = n})).length, 3);
  assert.equal(progress, 3);
  await assert.rejects(readBounded(new Response('abc'), {limit: 2}), /invalid_snapshot/);
  await assert.rejects(readBounded(new Response('', {status: 503})), /download_failed/);
});
test('bounded rendering search handles a thousand editions without creating result DOM', () => {
  const thousand = Array.from({length: 1000}, (_, i) => ({...books[0], id: i + 1}));
  const start = performance.now();
  for (let n = 0; n < 10; n++) assert.equal(searchBooks(thousand, {q: 'Garden'}).length, 1000);
  assert.ok(performance.now() - start < 5000, 'ten 1000-edition searches should complete within five seconds');
});
