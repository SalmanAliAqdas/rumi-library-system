# Optional metadata assistance

On **Add a book** or **Edit edition**, expand **Optional book information**.
Enter ISBN, or title and optional author (English/Urdu/Arabic accepted), then
**Find suggestions**. At most five work results or one ISBN edition are shown.
Search can return nothing; every field and normal Save remain usable manually.

Review the title, contributors, publisher, publication date/year, description,
cover and Open Library link. Missing provider fields are omitted. Title search
uses work-level search: publisher, year, ISBN and cover may be from different
editions. Confirm against the physical book, especially volumes and translations.
ISBN details may have descriptions that title search does not provide.

Select exactly which available fields to apply. Only empty draft fields are
preselected; populated fields require both selection and explicit replacement
confirmation. **Apply selected fields to draft** does not save inventory. Review
the resulting normal form, edit anything, then **Save**. Contributors are suggested
for review: add/select them through the existing contributor controls and choose
their correct roles. They are never created automatically. Physical copies,
accessions, shelves, volumes, visibility, categories/languages and loans are never
changed by lookup. JavaScript enables selection of a result; manual entry works
without it. Preview tokens expire after one hour; signed attribution already
applied to a draft can survive a longer editing session.

The last applied source URL and retrieval timestamp are retained privately on the
edition and shown on its edit form, including after saving. These describe a
suggestion source, not a claim that every current field still matches that source.
Metadata remains editable. No public browsing, background task, bulk enrichment,
AI summary or automatic provider request is involved. Google Books is disabled;
no Google credential, billing setup, payment card or API subscription is needed.

Provider policy checked November 5, 2026:

- [Open Library API policy](https://openlibrary.org/developers/api) permits light
  public API use, caps unidentified requests at one per second, and asks frequent
  clients to identify a contact. This app identifies `RumiLibrary/1.0` and reserves
  at most one request every two seconds using shared database updates. For more
  frequent sustained use, agree an identified contact with the provider before
  changing the policy. Do not spread requests across IPs or bulk harvest.
- [Search API](https://openlibrary.org/dev/docs/api/search) and
  [Books API](https://openlibrary.org/dev/docs/api/books) are used server-side at
  fixed HTTPS paths. No returned or user-supplied URL is fetched. Requests have
  four-second socket timeouts, a response deadline and a 512 KiB cap. Redirects,
  malformed JSON/data, 429s and outages yield a friendly retry/manual-entry message.
- [Licensing](https://openlibrary.org/developers/licensing): Internet Archive does
  not assert new rights over its database; individual contributions may still have
  rights restrictions. A source link is retained; this does not promise all covers
  or descriptions are public domain. Review permission to reuse material before
  publishing it; prefer your own description or no cover when uncertain.

Descriptions are stripped to bounded plain text and template-escaped. Provider
cover URLs are constructed only from validated numeric Open Library cover IDs on
`covers.openlibrary.org`; arbitrary returned cover URLs are discarded. Browsers
load covers without referrer; there is no server image proxy. Offline cover
downloads remain separate, opt-in, bounded and subject to CORS. There are no
provider credentials in browser responses. Shared throttling's PostgreSQL
concurrency behavior must be verified on the separate test database before launch.
