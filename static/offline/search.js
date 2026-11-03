import unicode from './unicode-data.js';
const whitespace = new Set(unicode.whitespace);
export function normalize(value) {
  const lowered = String(value || '').normalize('NFKC').toLowerCase();
  const folded = Array.from(lowered, c => unicode.casefold[c] ?? c).join('');
  let result = '';
  for (const c of folded) {
    const code = c.codePointAt(0);
    if (c === 'ـ' || c === '\u200d') continue;
    if (/\p{M}/u.test(c) && ((code >= 0x0610 && code <= 0x061a) || (code >= 0x064b && code <= 0x065f) || code === 0x0670 || (code >= 0x06d6 && code <= 0x06ed))) continue;
    result += c === 'ك' ? 'ک' : c === 'ي' ? 'ی' : c === '\u200c' || whitespace.has(code) ? ' ' : c;
  }
  return result.replace(/ +/g, ' ').replace(/^ | $/g, '');
}
export function isbnKey(value) {
  return Array.from(String(value || '').normalize('NFKC')).filter(c => !whitespace.has(c.codePointAt(0)) && !'-‐‑–—'.includes(c)).join('').toUpperCase();
}
export function compareText(a, b) {
  const left = Array.from(a, c => c.codePointAt(0)), right = Array.from(b, c => c.codePointAt(0));
  for (let i = 0; i < Math.min(left.length, right.length); i++) if (left[i] !== right[i]) return left[i] - right[i];
  return left.length - right.length;
}
export function rank(book, query, copies) {
  if (!query) return 0;
  const text = book.search, key = isbnKey(query), accessions = copies.map(c => normalize(c.accession));
  if (accessions.includes(query) || (key && text.isbn && key === text.isbn)) return 0;
  if (query === text.title || text.aliases.includes(query)) return 1;
  if (text.title.includes(query)) return 2;
  if (text.aliases.some(a => a.includes(query))) return 3;
  if ([...text.contributors, ...text.subjects].some(a => a.includes(query))) return 4;
  if (accessions.some(a => a.includes(query)) || (key && text.isbn && text.isbn.includes(key))) return 5;
  return text.summary.includes(query) ? 6 : null;
}
export function searchBooks(books, {q = '', category = '', language = '', availability = ''} = {}) {
  if (q.length > 200 || category.length > 50 || language.length > 12 || !['', 'available', 'on_loan'].includes(availability)) return [];
  const query = normalize(q), matches = [];
  for (const book of books) {
    if (category && !book.categories.some(c => c.slug === category)) continue;
    if (language && !book.languages.some(l => l.code === language)) continue;
    const copies = book.copies.filter(c => !availability || c.available === (availability === 'available'));
    if (!copies.length) continue;
    const score = rank(book, query, copies);
    if (score !== null) matches.push({book, score});
  }
  return matches.sort((a, b) => a.score - b.score || compareText(a.book.search.title, b.book.search.title) || a.book.id - b.book.id).map(x => x.book);
}
