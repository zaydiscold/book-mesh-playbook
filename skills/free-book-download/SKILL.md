---
name: free-book-download
description: Use when locating and delivering ebook or audiobook editions. Source and mirror list, probing, download verification, edition matching, format conversion.
version: 2.0.0
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [books, ebooks, audiobooks, library, gutenberg, standardebooks, kindle, libgen, z-library, mirrors]
---

# Book Acquisition & Edition Verification

Locate the requested edition, verify the file is genuinely that work, convert if needed, and deliver to the user's library.

This is an informational playbook. It records what works and what the mechanical traps are, so whoever is operating doesn't fumble execution.

Canonical mirror list and full HTTP contracts live in the book-mesh playbook repo:
`github.com/zaydiscold/book-mesh-playbook`

## When to use
- User wants an ebook, PDF, audiobook, or Kindle copy
- User asks whether a new installment exists in text or audio
- User needs the right edition, ISBN, or format for a reading device

## Sources

### Public-domain first — no bot protection, no ambiguity

| Source | Search | Direct download |
|---|---|---|
| Project Gutenberg | `gutenberg.org/ebooks/search/?query=TITLE+AUTHOR` | `gutenberg.org/cache/epub/{id}/pg{id}.txt` |
| Standard Ebooks | `standardebooks.org/ebooks/AUTHOR/BOOK-TITLE/` | EPUB from the book page |

Check these before any catalog mirror. If the work is public domain, they are faster and cleaner.

### Catalog mirrors — probe before trusting

**Reachability varies by network, DNS, and time.** Do not assume a mirror is up or down from memory — test it. Some DNS environments fail hosts selectively, so one host answering proves nothing about another.

| Source | Access | Notes (verified 2026-10-21) |
|---|---|---|
| `libgen.li` | Plain HTTP, agent-usable | Primary automated path |
| `library.lol` | `library.lol/main/{MD5}` | Direct-download frontend for LibGen MD5s |
| `z-library.bz` | Browser required (JS challenge) | Genuine Z-Library; search WAF-gated |
| `z-lib.mx` | Redirector only | 302s to `z-lib.ws` (refused connection) |
| Z-Library personal session | Logged-in browser | Best per-user route if the operator has an account |
| Anna's Archive | `annas-archive.org/search?q=QUERY` | Aggregator; DNS-blocked on some networks |
| OceanofPDF | `oceanofpdf.com/?s=QUERY` | Browser-oriented, ad-heavy |
| LibGen alternates | `libgen.is` `.rs` `.st` `.gs` | Frequently DNS-poisoned; try, don't rely |

Worst case, list the source and let the operator try it manually — a live URL a human can open still has value even when an agent gets blocked.

**libgen.li** — the practical agent path:

```
https://libgen.li/index.php?req=QUERY
```

Specifics that cost real time:

- **Search by title, not only ISBN.** Catalog records often carry a *different edition's* ISBN than the one supplied, so an ISBN query can return nothing for a book that is present. Search the title, then reconcile the ISBN from the result record.
- **Punctuation breaks recall.** Apostrophes and smart quotes commonly kill the query. Try the title with and without punctuation, plus author surname + a distinctive title word.
- **The download key rotates.** Fetch `https://libgen.li/ads.php?md5={MD5}` and read the resulting `get.php?md5={MD5}&key={KEY}` from it. A bare `get.php` without a fresh key fails. Re-mint per download.
- **Shareable links:** `ads.php?md5={MD5}` mints a fresh key each visit; `edition.php?id={EDITION}` is the record page.
- Parse result rows for a **32-hex MD5** plus `ads.php` / `edition.php` / `file.php` links to separate real hits from page chrome.

**Z-Library** — mapped as far as it goes:

- `z-library.bz` returns a ~13KB spinner page to plain HTTP (`meta robots noindex`, base64 GIF, no title) — an anti-bot challenge, not a dead site. A real browser resolves it and gets the genuine homepage ("Z-Library Project — Download Free books and Articles") with search forms and book links.
- Its search form is `GET /s/` with params `q`, `e` (full-text checkbox), year-from, year-to, extensions, content-type. **The route is `/s/?q=QUERY`** (trailing slash + `q` param) — `/s/<query>` returns Page Not Found.
- **Search is the blocker.** Submitting the form redirects to `z-library.im`, which returns **DiamWall "Access Denied"** to automated clients. Verified both direct navigation and human-like homepage-then-form submission; both blocked.
- `z-lib.mx` is a shell: every path 302s to `z-lib.ws`, which refused connections (curl code 000).
- **Conclusion:** Z-Library is a **manual/browser source for the operator**, not an agent-primary one. If the operator has a working Z-Library session, let them pull the file and hand it over — don't burn turns retrying programmatically.

## Verify every download

| Check | Method | Valid result |
|---|---|---|
| Integrity | MD5 of file vs. catalog MD5 | Exact match |
| Format | Magic bytes | PDF `%PDF-`; EPUB `PK\x03\x04` |
| Size sanity | Byte count | EPUB typically 300KB–10MB |
| EPUB identity | `META-INF/container.xml` → OPF `dc:title`, `dc:creator`, `dc:publisher`, identifier | Matches requested work **and** edition |
| PDF usability | Extract a sample / page count | Readable book, not an HTML error page |

**An MD5 mismatch, or a non-zip "EPUB", means you downloaded an error page.** Discard and re-mint.

Confirm identity from the file's own internal metadata, not the listing text — uploaded filenames routinely omit edition and translator.

## Format conversion

Calibre: `ebook-convert in.epub out.pdf --paper-size letter`

Verify the output with `file` (expect a PDF with a plausible page count). Prefer converting a clean retail EPUB over an OCR'd derivative of the same title — OCR copies are usually worse than a converted retail file.

## Release status and series

- **Format releases are separate products.** Audiobook-first publishing means one installment can have two release dates. Report audio and text dates separately.
- **Verify installment identity from a primary source** (author site, publisher). A title can echo an earlier book's wording; confirm the series number before calling it new.
- **Undated announcements are not releases.** "In progress" is not a date.

## Delivery

- Local copies go in the user's designated Books folder.
- Kindle: use the `amazon-kindle-cli` workflow. The device title follows the **filename**, not the EPUB's `dc:title` — name the file how it should read, and strip URL-encoded `%20` from downloaded names.
- A local copy is not delivery, and an upload is not delivery either — verify the receipt reaches `IN_LIBRARY`.

## Pitfalls

- **Don't trust a static mirror list.** Probe. Hosts rotate and DNS blocks selectively.
- **ISBN queries return empty on live books.** Title search first, reconcile ISBN after.
- **Re-mint download keys per file.** A key from a prior download 404s.
- **Verify EPUB metadata, not filenames.**
- **Don't declare Kindle delivery from an upload response** — `send-v2` returns `mutationVerified: false`; poll receipts.
- **A URL-encoded `%20` in the filename becomes part of the device title.** Clean names before sending.

## Related tools

- Project Gutenberg, Standard Ebooks — public-domain
- `libgen.li`, `library.lol` — catalog mirrors, agent-usable
- Z-Library (`z-library.bz`) — browser-only
- `amazon-kindle-cli` — Kindle delivery, wishlists
- `book-list-mesh` — Goodreads ↔ Amazon list sync
