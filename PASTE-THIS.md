# Paste this into your agent

Everything below is one self-contained block. Copy it whole into any agent
(Hermes, Claude Code, Codex, Cursor) and it has what it needs to acquire ebooks and
get them onto a Kindle.

---

```text
You have a book pipeline: acquire ebooks, manage reading lists, and deliver files to Kindle.
Work over HTTP/CLI. Do not drive the browser for product actions — browser/CDP is only for
capturing cookies when a session dies.

## Tools

Two unofficial CLIs (public, TypeScript, MCP is an optional thin adapter — the CLI is primary):
  Amazon/Kindle : github.com/zaydiscold/amazon-kindle-cli-mcp-api
  Goodreads     : github.com/zaydiscold/goodreads-cli-mcp-api

Both auto-load auth in a cold shell. Do not `source` files first and do not start MCP to
make a command "work". Prove state instead:

  amazon-kindle-cli auth verify

Read these gates separately:
  readReady            — can read
  retailWriteReady     — can mutate wishlists (needs recent retail auth)
  kindleAuthenticated  — can send to Kindle
Refresh only the gate that is false.

## Auth (per-operator, from that operator's own browser)

Sign in normally in a dedicated browser profile, then harvest an ORIGIN-SCOPED cookie jar for
https://www.amazon.com/ only, written to ~/.amazon/auth.sh. Never flatten every *amazon* cookie
into one header — duplicate names break the session.

The Amazon cookie is long-lived. Send-to-Kindle and content APIs enforce a freshness window
(openid.pape.max_auth_age, ~3600s). That is a step-up, not a re-login — never conclude "auth is
broken" from an old snapshot. Re-verify, re-harvest, and only then step up.

## Finding books

Check public-domain sources first — they have no bot protection and no ambiguity:
  Project Gutenberg  gutenberg.org/ebooks/search/?query=TITLE+AUTHOR
                     download: gutenberg.org/cache/epub/{id}/pg{id}.txt
  Standard Ebooks    standardebooks.org/ebooks/AUTHOR/BOOK-TITLE/

For catalog mirrors, availability is volatile and DNS-dependent. Probe before trusting any list;
several well-known mirrors time out or fail DNS from some networks. At last verification
libgen.li answered while libgen.is/.rs/.st timed out and annas-archive.org failed DNS.

Mirror search:
  https://libgen.li/index.php?req=QUERY

Hard-won specifics:
  - Search by TITLE, not just ISBN. Catalogue records often carry a different edition's ISBN,
    so an ISBN query returns nothing for a book that is definitely present.
  - Apostrophes and smart quotes break the query. Try both with and without them, plus author
    surname + distinctive title word.
  - Parse result rows for a 32-hex MD5, plus edition.php?id=, file.php?id=, ads.php?md5= links.
  - Downloads are keyed and the key ROTATES: fetch https://libgen.li/ads.php?md5={MD5} and read
    get.php?md5={MD5}&key={KEY} from it. A bare get.php without the key fails.

## Verify every download

  - File MD5 must equal the catalogue MD5. That single check catches truncated files and
    error pages better than size alone.
  - EPUB magic bytes are PK\x03\x04; a real EPUB is usually 300KB–10MB.
  - Confirm identity from the file's OWN metadata (META-INF/container.xml -> .opf, reading
    dc:title / dc:creator / dc:publisher), not from the listing text.
  - If it is not a zip, it is almost certainly an HTML error page — discard it.

## Convert

Calibre: ebook-convert in.epub out.pdf --paper-size letter
Verify with: file out.pdf  (expect "PDF document" with a sensible page count)

Prefer converting a clean retail EPUB over downloading an OCR'd derivative; OCR copies of the
same title are usually worse than a converted retail file.

## Send to Kindle

  amazon-kindle-cli kindle send FILE --via web --execute     # dry-run without --execute
  amazon-kindle-cli kindle recent                            # verify

The title on the device follows the FILENAME, not the EPUB's dc:title. Name the file how you
want it to read, and strip any URL-encoded %20 from downloaded filenames before sending.

A successful upload is NOT delivery. send-v2 returns mutationVerified: false; Amazon converts
asynchronously. Confirm each file reaches IN_LIBRARY (or COMPLETE) in the receipt list, and match
byte sizes against what you sent. Only then report success.

## Amazon lists

  amazon-kindle-cli wishlist list                 # full paginated walk, not page-1 SSR
  amazon-kindle-cli wishlist add --asin ASIN --execute

Wishlist membership is not ownership. Purchased Kindle inventory, personal documents, and recent
send receipts are three separate surfaces — never substitute one for another.

## Goodreads

  goodreads-cli shelves add --book-id ID --name to-read --execute

Verify membership on authenticated shelf HTML, not RSS and not HTTP 200.

## Doctrine

  - HTTP 200 is not success. Verify the end state of every write.
  - Dry-run is the default; --execute is the deliberate act.
  - One edition per work on hauls; skip study guides and duplicate storybook variants.
  - Anything that requires scrolling or clicking Amazon/Goodreads is a bug — fix the HTTP path.

## Housekeeping

Mirror hosts rotate. If a host stops answering, probe alternatives rather than concluding the
book does not exist. Catalogue MD5s, filenames, and product routes drift over time — re-verify
before trusting a hardcoded value from a previous session.
```
