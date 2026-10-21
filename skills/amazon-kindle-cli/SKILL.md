---
name: amazon-kindle-cli
description: "Use when sending files to Kindle, reconciling Amazon lists with Goodreads, or routing a photographed book to Amazon/Goodreads via HTTP CLI/MCP."
---

# Amazon / Kindle Book Mesh

## Zero-thought intent router

| User intent | Cheapest correct path |
|---|---|
| "Put this EPUB/PDF in my Kindle app/library" | `amazon-kindle-cli kindle send FILE --via web --execute`, then verify with `kindle recent` |
| "Add this title to my Amazon list" | `books resolve` → ASIN → `wishlist add --asin ASIN --execute`, then verify with full `wishlist list` pagination |
| "Add this title to Goodreads / want-to-read" | resolve numeric Goodreads book ID → `goodreads-cli shelves add --book-id ID --name to-read --execute` |
| "Add this title to my Kindle library" but no legal file exists | Do **not** claim wishlist = library. Offer Amazon wishlist / Goodreads to-read, or request explicit purchase approval. |
| "Show my Kindle library" | distinguish purchased books from personal docs; never substitute `kindle recent` (recent uploads only) |

Rules for small agents:

1. Prefer CLI. MCP is a thin optional adapter. Browser/CDP/WireBrowser is auth recovery or contract research only.
2. The CLI auto-loads Amazon auth in a cold shell; do not source files or start MCP unless a command proves auth is stale.
3. Writes dry-run by default. Add `--execute` only when the user asked for the write.
4. Verify semantically: Send-to-Kindle receipt/status, full paginated wishlist membership, or Goodreads shelf membership. HTTP 200 alone is not success.
5. For a Kindle send, poll `kindle recent` after the asynchronous conversion and match every sent **filename and byte size** in `data.docs[]`; report delivery only when each matching receipt is `status: IN_LIBRARY` with no failure/error code. The send mutation response is only an upload acknowledgment.
6. Writes are explicit: dry-run unless `--execute`.

## Preflight

The standalone CLI auto-loads `~/.amazon/auth.sh`; do not source it or start MCP first.

```bash
amazon-kindle-cli doctor
amazon-kindle-cli auth verify
```

Inspect `readReady`, `retailWriteReady`, and `kindleAuthenticated` **separately**. Require
`kindleAuthenticated=true` before any Kindle send and `retailWriteReady=true` before any
wishlist mutation.

## Auth refresh — deterministic SOP (do not waver)

The Amazon session cookie is **long-lived**. Send-to-Kindle and MYCD only enforce a
*freshness window* (`openid.pape.max_auth_age`, ~3600 s) — a **step-up, not a re-login**.
Never conclude "auth is broken" from a pre-harvest snapshot.

```bash
# 1. Prove the current state first.
amazon-kindle-cli auth verify
#    kindleAuthenticated=true  ->  done, proceed.
```

If not:

```bash
# 2. Re-harvest the existing Brave session BEFORE declaring it dead.
python "%LOCALAPPDATA%/amazon-kindle-debug-profile/brave_amazon_login.py" --cookies-only
amazon-kindle-cli auth verify   # re-check
```

If **still** not authenticated:

```text
3. Drive Brave to https://www.amazon.com/sendtokindle and click the step-up button
   (id="s2k-dnd-sign-in-button"). If the retail session is still fresh this completes
   WITHOUT a password prompt.
4. If a password field actually appears, supply it through the vault (never inline).
5. Re-harvest the FULL jar, then re-run auth verify.
6. Only request an OTP when an OTP field literally appears (enter via
   browser_vault_enter_code, never by asking for it in chat).
```

Assisted sign-in via the vault: operator stores the login once (`hermes vault add`), agent
types the identifier and calls `browser_vault_fill`; the password is resolved server-side and
never enters the transcript. The headless force-add path (`VaultStore.add_item`) is documented
in the repo's `docs/auth.md`.

**Raw HTML ≠ auth wall.** A raw `GET /sendtokindle/recent-docs` returns HTML even when the
session is authenticated — it needs the CSRF token + XHR headers the CLI sends. Read a raw
HTML body as missing headers, not signed-out. Use `auth verify` / `kindle recent` (the CLI
path) to tell headers from a real auth failure.

**Broken + ours = fix in the same turn.** Never ask "want me to fix amazon auth?"

## HTTP product paths

```bash
# Full wishlist via HTTP pagination (no scroll)
amazon-kindle-cli wishlist list

# Add ASIN (dry-run default)
amazon-kindle-cli wishlist add --asin B0XXXXXXXXXX
amazon-kindle-cli wishlist add --asin B0XXXXXXXXXX --execute

# Kindle send (web HTTP default)
amazon-kindle-cli kindle send book.epub --via web
amazon-kindle-cli kindle send book.epub --via web --execute
# Poll until the matching data.docs[] receipt is IN_LIBRARY; match filename + size,
# not only a docId or the total receipt count.
amazon-kindle-cli kindle recent

# Parity (Goodreads id via --user or GOODREADS_USER_ID)
amazon-kindle-cli parity --user <goodreads-user-id> --shelf to-read
```

## Send hygiene — the title follows the filename

The Kindle document title on the device follows the **filename** you send, not the EPUB's
internal `dc:title`. Name the file how you want it to read before sending:

- Decode URL-encoded source names first. Free-book hosts ship links like
  `.../Letters%20to%20a%20Young%20Creator...epub`; a downloader that keeps the literal `%20`
  makes the title render as `Letters%20to%20a%20Young%20Creator` on the device. Send under a
  clean name (spaces, no `%20`).
- One `kindle send` can emit two `recent-docs` entries (both settle `IN_LIBRARY`); verify by
  the newest filename and flag the duplicate library copies to delete.

## Format editing & conversion (before the send)

Editing/converting a file or injecting ASIN/EXTH metadata is a separate toolchain from the send
path — see `references/ebook-toolchain.md` (Calibre installed; `boko`/`kindling`/`epub3-kindle`
for EPUB→AZW3/KFX; `mobi_header` for the EXTH ASIN/cdetype label flag).

## Mapped routes

| Action | Method | Path |
|---|---|---|
| list page | GET | `/hz/wishlist/ls/{id}` |
| list more | GET | `/hz/wishlist/slv/items?paginationToken=…` |
| add item | POST | `/hz/wishlist/additemtolist?ie=UTF8` |
| STK home | GET | `/sendtokindle` |
| STK init | POST | `/sendtokindle/init` |
| STK put | PUT | signed `uploadUrl` |
| STK finalize | POST | `/sendtokindle/send-v2` |
| STK recent | GET | `/sendtokindle/recent-docs` |

## Photo / title intake

Vision/OCR → title+author →:

```bash
amazon-kindle-cli books resolve --text $'Title\nby Author'
amazon-kindle-cli add-plan --title 'Title' --author 'Author'
# then wishlist add --asin … --execute  AND  goodreads-cli shelves add …
```

## Related

| Skill | Use |
|---|---|
| `goodreads-cli` | shelf writes |
| `http-contract-mapping` | capture with CDP, ship and regression-test pure HTTP clients |
| `hermes-agent` | MCP config/reload |

## Docs in repo

- `docs/auth.md` — canonical auth: surfaces, refresh SOP, step-up, vault (single source)
- `docs/canonical-procedures.md` — recipes
- `docs/book-mesh.md` — topology
- `docs/debug-browser-methodology.md` — **auth/capture only**
