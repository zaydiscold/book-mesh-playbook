---
name: book-list-mesh
description: "Use for Goodreads+Amazon list/Kindle HTTP CLI mesh work."
---

# Book list mesh (Goodreads ↔ Amazon/Kindle)

## Cheapest intent router

| Phrase | Route |
|---|---|
| `send/put this EPUB or PDF to Kindle` | `amazon-kindle-cli kindle send FILE --via web --execute` → `kindle recent` |
| `add this title to Amazon` | title/author → ASIN → `wishlist add --asin ASIN --execute` → full `wishlist list` verify |
| `add this title to Goodreads / want-to-read` | title/author → numeric Goodreads ID → `shelves add --book-id ID --name to-read --execute` → shelf verify |
| `add this title to my Kindle library` with no file | Wishlist/to-read, or explicit purchase approval. Never claim wishlist membership is ownership. |
| `show my Kindle books` | Purchased-library inventory. Keep personal docs and recent Send-to-Kindle receipts separate. |

Small-agent rules: use CLI first; do not start browser/CDP or MCP unless the direct command fails; do not ask the user to disambiguate when the noun already identifies the surface; never claim success without a readback.

Class playbook for the **paired unofficial CLIs**. Product path is **API map → standalone CLI** (MCP optional thin adapter). Browser/CDP is for **cookie capture + one-shot contract sniffing only** — never scroll/click product runtime.

## Repos

| Surface | GitHub | Auth |
|---|---|---|
| Goodreads | `zaydiscold/goodreads-cli-mcp-api` | `~/.goodreads/auth.sh` |
| Amazon/Kindle | `zaydiscold/amazon-kindle-cli-mcp-api` | `~/.amazon/auth.sh` auto-loaded (+ optional `AMAZON_WISHLIST_ID`) |

Set `GOODREADS_USER_ID` and `AMAZON_WISHLIST_ID` to your own values.

## Invariants

1. **CLI first** — every MCP tool must exist on CLI and come from the api-map. Amazon MCP is **optional**; do not require it for cold-shell / cron / scripts.
2. **Dry-run default** — writes need `--execute`.
3. **Never print cookies/CSRF/tokens.**
4. **Volume discipline** — one edition per work on hauls; skip study guides and duplicate storybook variants unless asked.
5. **One edition per work** on hauls (skip study guides / duplicate storybook variants unless asked).
6. **GitHub is source of truth** — ship **both** repos (user only sees emails for repos that actually merge).
7. **Anything requiring manual look/scroll on Amazon or Goodreads is a bug** — fix the HTTP CLI path instead.
8. **Auth proof is live dual-surface** — Amazon `auth status` ≠ ready; use `auth verify` and treat `readReady` vs `retailWriteReady` separately.

## Amazon wishlist HTTP (live-mapped 2026-08-01)

**HTTP only on CLI.** No `--via browser` product path. MCP optional.

### Preflight (cold shell — no source, no MCP)

```bash
amazon-kindle-cli auth status
amazon-kindle-cli auth verify --list-id "$AMAZON_WISHLIST_ID"
# readReady / retailWriteReady / kindleAuthenticated / retailSessionMode
```

### List (full walk — no scroll)

```bash
amazon-kindle-cli wishlist list --list-id "$AMAZON_WISHLIST_ID"
# data.via=http, data.pagesFetched, data.items[], data.sessionMode=authenticated|public
```

1. `GET /hz/wishlist/ls/{listId}?sort=date-added&viewType=list`
2. Parse `itemName_*` anchors + `showMoreUrl` / `paginationToken`
3. Loop `GET /hz/wishlist/slv/items?filter=unpurchased&paginationToken=…` until exhausted  
   Live: ~6 pages / 47 items; Discount Dan present when page-1 SSR only had ~10.
4. If cookie request 302s to `/ap/signin` (often `openid.pape.max_auth_age=900`), **retry without cookies** and report `sessionMode=public`. Reads may still work; **writes need fresh retail auth**.

Code: `cli/src/client/wishlistListHttp.ts`, `cli/src/parsers/wishlist.ts`.  
Detail: `references/wishlist-http-list.md`. Dev notes: `amazon-kindle-cli-development` → `references/standalone-auth-session.md`.

### Add

```bash
# Requires retailWriteReady=true from auth verify
amazon-kindle-cli wishlist add --asin B0DSGQ5XPS --execute
```

1. `GET /dp/{ASIN}`
2. CSRF from **`#addToWishListForm` → `name="anti-csrftoken-a2z" value="..."`**  
   Meta-only CSRF often yields **403 “Page Not Found”** (WAF/shape, not real route miss).
3. `POST /hz/wishlist/additemtolist?ie=UTF8`  
   body: `asin`, `vendorId=website.wishlist.detail.add`, `listType=wishlist`, `isAjax=1`, optional `listId`  
   headers: cookie, `anti-csrftoken-a2z`, `X-Requested-With: XMLHttpRequest`, Origin/Referer product page

**Success body:** `huc-atwl` / “View Your List” **or** “This item was already in” + “moved it to the top”.

Code: `cli/src/client/wishlistHttp.ts`. Detail: `references/wishlist-http-add.md`.

## Kindle send HTTP

Default: `kindle send FILE --via web --execute`  
Flow: GET `/sendtokindle` CSRF → POST `/sendtokindle/init` → PUT uploadUrl → POST `/sendtokindle/send-v2` → poll `recent-docs`.  
Do not re-upload known Carl EPUB (`A_Parade_of_Horribles`) unless asked. Email SMTP is the other legal path.

## Known incomplete Amazon/Kindle surfaces (do not fake as shipped)

| Missing | Reality |
|---|---|
| Full Kindle **library** / **personal docs** inventory | `content devices` is a shallow mycd probe (status/bytes). `kindle recent` = last STK receipts only. No structured `booksAll` / `pdocs` parser on master. |
| Wishlist **remove/delete** | HTTP **add** only. List hygiene still needs browser or a not-yet-mapped delete contract. |
| Wishlist **create** | List resolve/list exists; create list not implemented. |
| @kindle.com address harvest | Manual / config file — not parsed from Manage Content settings via CLI. |

Parity today is **wishlist ↔ Goodreads**, not a true three-way with owned Kindle library. Dev backlog: `amazon-kindle-cli-development` → `references/auth-http-contract-gaps.md`.

## Goodreads shelf writes

```bash
source ~/.goodreads/auth.sh
# if CSRF refresh hits anti-bot:
export GOODREADS_SKIP_CSRF_REFRESH=1
# keep browser-minted GOODREADS_CSRF_TOKEN
goodreads-cli shelves add --book-id ID --name to-read --execute
```

- `library set-status` reuses `POST /shelf/add_to_shelf` (not a separate stub).
- **Verify membership on authenticated HTML pages** (`review/list/...&page=N`), not RSS alone and not HTTP 200 alone.
- Photo count ≠ unique books — report unique works verified.

## Auth durability

| Source | How |
|---|---|
| Amazon | Brave CDP `:9333` profile `amazon-kindle-debug-profile` → **origin-scoped** cookies for `https://www.amazon.com/` only → `~/.amazon/auth.sh` (CLI auto-loads). Prefer `brave_amazon_login.py --cookies-only` if already signed in. |
| Goodreads | Same browser after **Continue with Amazon** consent → dump cookie + csrf via `shlex.quote` |
| Cross-machine | Separate files; never merge secrets into git |

**Never** flatten every `*amazon*` domain cookie into one header — multi-origin dumps create **duplicate cookie names** and broken sessions.

## List verification (Amazon)

- Page-1 SSR alone is **not** the full list (~10 `itemName_*` rows).
- Canonical proof: `wishlist list --list-id …` HTTP pagination (`slv/items`).
- Add response `huc-atwl` / already-in is strong; still confirm ASIN in **paginated** `items[]`.
- Do **not** default to browser scroll for verification.
- `sessionMode=public` is still valid full-list **read** proof when recent retail auth expired.

## Photo haul orchestration

Use skill `bookstore-photo-list-parity` for multi-photo pipelines. This skill owns the **HTTP contracts + shipping gates**.

## Product direction (remembered)

Simple app/site: user logs into GR + Amazon, drag bookstore photos / camera roll → dual-list add + bidirectional sync on these engines.

## Related

- `bookstore-photo-list-parity` — haul SOP
- `amazon-kindle-cli-development` — engine/MCP/auth gates + `references/standalone-auth-session.md` + `references/auth-http-contract-gaps.md`
- User-owned (recommend `hermes curator adopt` if stale): `amazon-kindle-cli`, `browser/goodreads-cli` — operator Amazon skill may still say `source` auth; **repo** docs after PR #4 are authoritative
- `windows-browser-automation` — CDP recovery for auth only

## Pitfalls

| Symptom | Fix |
|---|---|
| wishlist add 403 Page Not Found | CSRF from form value, not meta; use `?ie=UTF8` |
| List ~10 items / missing ASIN | Full HTTP list walk (`slv/items`), not page-1 only |
| Agent clicks/scrolls Amazon UI | Stop — CLI HTTP; CDP only for cookie refresh or new route map |
| Agent sources auth or starts Amazon MCP “so CLI works” | Cold-shell auto-load is enough; MCP optional |
| auth status green but mutations fail | `auth verify` → need `retailWriteReady` (recent retail auth) |
| Wishlist 302 to sign-in after ~15m | Expected max_auth_age; public read retry; re-auth for writes |
| Dup cookie names after harvest | Origin-scope to `www.amazon.com` only |
| Goodreads CSRF challenge | `GOODREADS_SKIP_CSRF_REFRESH=1` + browser-minted token |
| Only Goodreads GitHub email | Also merge/push amazon-kindle-cli-mcp-api |
| Official Robinhood MCP | Not wired as a product path — custom robinhood-cli is primary |
