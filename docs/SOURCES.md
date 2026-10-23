# Sources

Every catalog, metadata, and delivery surface this project uses — what works, what doesn't,
and what it actually does. Verified from this machine on 2026-10-22/23.

## Mirrors

| Source | Status | Notes |
|---|---|---|
| **libgen.li** | ✅ **only downloadable** | `ads.php?md5=<md5>` → extract `get.php?...&key=...` → fetch. ~42 KB/s per connection. **50 files / 300s per IP.** |
| **z-library.bz** | ⚠️ search only | `/s/?q=QUERY` works in a real browser (~500 results). Every book link redirects to `.im`. |
| **z-library.im** | ❌ blocked | DiamWall "Access Denied" even in a fresh browser profile — IP reputation. |
| **library.lol** | ❌ dead | Serves a "Domain Seizure Notice", not a block. |
| **libgen.is / .rs / .st** | ❌ TCP timeout | DNS resolves; no TCP handshake. Network-level. |
| **annas-archive.org** | ❌ DNS NXDOMAIN | Does not resolve. |
| **libgen.gs** | ❌ DNS NXDOMAIN | Does not resolve. |
| **libgen.bz / libgen.vg** | ⚠️ linked by the tracker | Present as external search routes; not verified downloadable here. |

Mirror status is geography- and time-dependent. Re-test before concluding a source is dead —
and never conclude it's alive because a URL 200s.

## Metadata

| Source | Use |
|---|---|
| **Open Library** | Title, author, cover art, editions. No key required. |
| **Goodreads** (`/book/auto_complete?format=json&q=`) | Title → `bookId` resolution. `/search` redirect-loops under anti-bot; autocomplete does not. |
| **Amazon `/dp/{ASIN}`** | ASIN validation before a wishlist write. |

## Lists

| Surface | Detail |
|---|---|
| **Goodreads to-read** | `GET /review/list/{user}?shelf=to-read&per_page=100&page=N`. RSS caps at 100 — paginate HTML for the real count. |
| **Amazon wishlist** | `GET /hz/wishlist/ls/{id}?sort=date-added&viewType=list`. Lazy-loads; walk pagination. |
| **Goodreads write** | `POST /shelf/add_to_shelf` — requires `--approved-book-id` / `--approved-status`. |
| **Amazon write** | `POST /hz/wishlist/additemtolist` — throttles hard; ~5 burst then sustained 403. |

## Delivery

| Surface | Detail |
|---|---|
| **Send to Kindle** | `/sendtokindle` → CSRF → `/sendtokindle/send-v2`. EPUB/PDF only — **`.mobi` is rejected**. |
| **Receipts** | `/sendtokindle/recent-docs` returns **exactly 18**, regardless of limit. Nothing enumerates the full library. |

## Audiobooks

| Source | Status |
|---|---|
| **LibriVox** | ✅ Public domain. JSON API with direct MP3s. `librivox.org/api/feed/audiobooks/?title=X&format=json&extended=1`. Tested: 4 MB MP3 downloaded and valid. |
| **Internet Archive** | ✅ Hosts the LibriVox audio; ZIP of a whole book via `archive.org/compress/<id>/...`. |
| **Loyal Books** | ✅ Reachable. |
| **Hoopla / Libby** | ✅ Legitimate free route for in-copyright audiobooks with a library card. |
| **Audiobookbay** | ✅ Reachable. |

**Audible is not accessible via Amazon retail cookies.** It uses a separate SSO
(`audible_experiment_sso_web_us`) and then hits the bot wall.

## Not a source

- **Amazon retail cookies do not carry to Audible.**
- **Amazon's web UI is bot-walled from this machine** — `/dp/*`, `/s?k=*`, and `/hz/mycd/*` all
  return "Click the button below to continue shopping". HTTP with the CLI's cookies is more
  reliable than the browser here, which is the opposite of the usual assumption.
