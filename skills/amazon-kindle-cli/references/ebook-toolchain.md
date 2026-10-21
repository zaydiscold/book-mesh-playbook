# Ebook Format Toolchain (edit / convert / inject)

Use when preparing, editing, or converting ebook files — the work that happens *before* the
send-to-Kindle HTTP path. Distinct from `amazon-kindle-cli` send/wishlist.

## Open-source tools (no Amazon dependency)

- **Calibre 9.x** — installed at `C:\Program Files\Calibre2\` (winget `calibre.calibre`).
  `ebook-convert`, `ebook-edit`, `ebook-meta`, `ebook-polish`. General workhorse.
- **Sigil** — dedicated GUI EPUB editor (XHTML/OPF precision).
- **ebooklib** (Python) — programmatic EPUB read/write; used for metadata/identifier/ISBN/ASIN injection.
- **boko** (Rust, `cargo install boko`) — EPUB → **KFX**/AZW3/MOBI. The only KFX writer that does
  not shell out to Amazon's Kindle Previewer (KFX = preferred Kindle format: hyphenation/kerning/ligatures).
- **kindling** (Rust, `cargo install kindling-mobi`) — drop-in kindlegen replacement, single binary,
  ~7000x faster than kindlegen.
- **epub3-kindle** (Rust) — EPUB → AZW3/MOBI (KF8-only), kindlegen-compatible flags.
- **mobi_header** (Python, `pip install mobi-header`) — read/edit MOBI/AZW3 **EXTH** metadata.
- **KindleUnpack** — unpack AZW3/MOBI to source (reverse engineering).
- **epubcheck** — EPUB 2/3 spec validation.
- **KindleGen / Kindle Previewer** — DEPRECATED by Amazon (2020); avoid.

## The "book vs personal doc" flag lives in EXTH, not EPUB metadata

EXTH 113 (ASIN) and EXTH 501 (cdetype=EBOK) are MOBI/AZW3 **header** fields — EPUB metadata has
no equivalent. To set them:

1. Convert EPUB → AZW3 (`boko`/`kindling`/Calibre `ebook-convert`).
2. Patch EXTH with `mobi_header` (EXTH 113 = ASIN, EXTH 501 = EBOK).

Boundary: this flips the display label ("Book" vs "Personal Document") only. It does **not**
unlock Kindle→Goodreads highlight sync — that is keyed to Amazon's purchased-ASIN database, not
to any field in the file. Treat the injection as cosmetic/format-label work, not a sync path.

## Conversion chain

`ebooklib` (metadata/ISBN/ASIN → EPUB) → `boko`/Calibre (→ AZW3/KFX) → `mobi_header`
(EXTH/ASIN patch) → `amazon-kindle-cli kindle send FILE --via web --execute`.
