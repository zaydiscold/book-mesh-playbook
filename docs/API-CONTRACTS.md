# API Contracts

The exact HTTP surface this playbook drives. Everything here was captured from working code and
live traffic — not inferred from docs. Amazon and Goodreads change without notice; treat these as
verified-at-a-point-in-time and re-probe before trusting.

All requests are plain `fetch`/`curl`. No browser automation on any path.

---

## Amazon / Kindle

Base origin: `https://www.amazon.com`
Auth: session cookie jar, origin-scoped to `www.amazon.com` only.

### Send-to-Kindle (4-step dance)

```
1. GET  /sendtokindle
   ← HTML. Extract CSRF from  /<input name="csrfToken" value="…">/
     (prefer this over the generic navbar token — they are different tokens)

2. (assemble upload)

3. POST /sendtokindle/send-v2
   ← { status: true }
   ⚠ status:true means ACCEPTED, not delivered. No delivery guarantee here.

4. GET  /sendtokindle/recent-docs
   ← receipts; poll status IN_PROGRESS → COMPLETE / IN_LIBRARY
```

Also used: `/sendtokindle/init` (upload initialisation), header `anti-csrftoken-a2z` (required on the
upload request).

**Filename behaviour:** Amazon rewrites the receipt filename. `Ender's Game.epub` comes back as
`Ender＇s Game.epub` — a fullwidth apostrophe (U+FF07). Match receipts with apostrophe folding
(U+2019 / U+2018 / U+FF07 → `'`) or delivered books look missing.

**Receipt window:** `/sendtokindle/recent-docs` is a sliding window of roughly the last ~18 docs,
not the full inventory. A confirmed `IN_LIBRARY` book can fall out of the window as newer uploads
land. Falling out ≠ failure.

### Wishlist

```
GET  /hz/wishlist/ls                          → discover list name → listId
GET  /hz/wishlist/ls/{listId}?sort=date-added&viewType=list
POST /hz/wishlist/additemtolist?ie=UTF8&…    → add an ASIN
```

The list page lazy-loads; a page-1 parse undercounts. Walk the pagination before trusting a total.
That is the difference between "54 items" and the real number.

### Content inventory (MYCD)

```
GET  /hz/mycd/digital-console/contentlist/books
   ← HTML; extract `var csrfToken`
POST (same path, paged)
   body: contentType, originTypes, excludeExpiredItemsFor, surfaceType:"Desktop",
         showSharedContent:true, startIndex, batchSize
```

Two content types matter and are **not** interchangeable:

| `contentType` | Returns |
|---|---|
| `Ebook` | purchases, subscriptions, loans, samples |
| `KindlePDoc` | personal documents (your send-to-Kindle uploads) |

This surface needs a **different cookie scope** than send-to-Kindle. `pdocs` frequently fails with
"requires sign-in or Amazon presented a challenge" while `send` works fine. That is a scope split,
not a broken session — don't "fix" it by re-uploading.

### Auth probe

```
GET /gp/css/homepage.html   → signed-in marker present?
```

---

## Goodreads

Base origin: `https://www.goodreads.com`
Auth: `GOODREADS_COOKIE` env var. **The CLI does not auto-load it.**

```bash
. ~/.goodreads/auth.sh     # required — unlike amazon-kindle-cli
```

Missing cookie does not error. It returns `rows: 0, signedOut: false` — an empty result set that
looks exactly like an empty shelf.

### Shelf listing (HTML — full fidelity)

```
GET /review/list/{userId}?shelf={shelf}&per_page=100&page={n}
   ← HTML
```

Parse anchors. Rows are `<tr id="review_…" class="bookalike review">`; the title is the **first
`a[href*='/book/show/']` with non-empty text** — the old `a.bookTitle` class is gone, and matching
on it yields zero rows on current markup.

The authoritative total is in `<title>`:

```
<title>Name's 'to-read' books on Goodreads (171 books)</title>
```

Always reconcile parsed-count against that number before declaring a shelf complete. Paginate at
`per_page=100` until the count matches.

### Shelf listing (RSS — capped)

```
GET /review/list_rss/{userId}?shelf={shelf}
   ← XML, hard cap 100 items
```

Useful for a quick pull and for public shelves. **Silently truncates at 100** — never treat the RSS
count as the shelf size.

### Shelf mutation

```
POST /review/update/{bookId}     (form: shelf, review[book_id], authenticity_token)
GET  /review/edit/{…}
```

Requires a CSRF token from the authenticated page.

### Other surfaces used

```
/notes/{book_slug}/{user_slug}          highlights + notes
/notes/{book_id}/{annotation_pair_id}/note
/review/show/{reviewId}                 review permalink (RSS `guid`)
/recommendations
/quotes, /quotes/list
/message/inbox|sent|saved|trash, /message/{id}, /message/mark_all_as_read
/comment/list/{user_slug}
```

Notes paging uses cursor/fragment pairs; annotation UUIDs regenerate server-side over time, so
treat stored IDs as volatile and reconcile by visible count.

---

## libgen.li (catalogue + download)

The only mirror verified downloadable from this network.

### Search

```
GET /index.php?req={url-encoded query}
   ← HTML
```

Results live in `<table id="tablelibgen">`. Row cells, in order:

```
title | author | publisher | year | language | pages | size | ext | mirrors
```

The 32-hex MD5 and file extension appear as links/markup within the row.

**Query construction matters.** Add the author surname to the title. Include the series suffix in
parentheses only if you are prepared for it to reduce recall — catalogue records often omit it.

### Download (2-step, keyed)

```
1. GET /ads.php?md5={md5}
   ← HTML containing  get.php?md5={md5}&key={key}

2. GET /get.php?md5={md5}&key={key}   (with Referer: the ads.php URL)
   ← the file
```

The key is **short-lived and rotates**. A 404, an HTML error page, or an MD5 mismatch all usually
mean the key went stale between step 1 and step 2 — re-fetch `ads.php` rather than retrying the
same `get.php` URL.

### Verification is mandatory

```
md5(downloaded file) == catalogue md5
```

Any mismatch means you do not have that book. Delete and re-resolve. Do not send an unverified file
to a reader.

---

## z-library.bz (search metadata only)

```
GET /s/?q={url-encoded query}     ← HTML, ~500 results
```

Reachable from a real browser; curl gets a JS challenge shell. **Search works, downloads do not** —
every book link points at `z-library.im`, which returns `Access Denied | DiamWall` even in a real
browser session (IP-level reputation, not fingerprinting).

Useful as a metadata oracle (title, author, year, language, format, size) when libgen misses a
title. Not a download path from this network.

---

## Failure taxonomy — read the failure before changing the approach

Different failures need different fixes. Collapsing them into "blocked" wastes effort.

| Symptom | Real cause | Fix |
|---|---|---|
| `rows: 0, signedOut: false` | missing cookie | source the auth file |
| `000` + could-not-resolve | DNS | different mirror |
| `000` + connect timeout | TCP blocked | not fixable client-side |
| TLS `SEC_E_UNTRUSTED_ROOT` | cert untrusted | browser, or `-k` on a trusted host |
| HTML where a file was expected | stale download key | re-fetch `ads.php` |
| MD5 mismatch | wrong/partial file | discard, re-resolve |
| `status: true` but no receipt | uploaded, not delivered | poll `recent-docs` |
| receipt shows mangled name | filename normalisation | fold apostrophes when matching |
| `pdocs` auth error, `send` fine | separate cookie scope | don't re-upload; use receipts as proof |
