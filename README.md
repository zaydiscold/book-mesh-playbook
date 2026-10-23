# Book Mesh Playbook

A portable, credential-free bundle for AI agents that acquire ebooks and move them between
Goodreads, Amazon lists, and a Kindle — without browser automation or a shared login.

**Nothing here contains a credential.** Every secret lives on the operator's own machine and is
minted from *their* browser session. A friend clones this, logs into their own accounts, and
their agent reproduces the same workflow.

## Start here

**[PASTE-THIS.md](./PASTE-THIS.md)** — one self-contained block to paste into any agent. It carries the
whole pipeline: mirrors, search tactics, verification gates, conversion, and Send-to-Kindle.

## What's in the box

```
PASTE-THIS.md            one-paste agent brief
docs/API-CONTRACTS.md    the actual HTTP surface + failure taxonomy
docs/SOURCES.md          every catalog/metadata/delivery source, verified
pipeline/bookmesh.py     pull -> diff -> search -> download -> send
skills/
  free-book-download/    finding + fetching ebooks, mirror reality
  amazon-kindle-cli/     Send-to-Kindle, wishlist, auth recovery
  book-list-mesh/        Goodreads <-> Amazon mesh, HTTP contracts
```

Skills are plain markdown (`SKILL.md` + `references/`). Drop into Hermes, Claude Code, Codex,
Cursor, or anything that reads skill directories.

## Pipeline

```bash
export GOODREADS_USER_ID=<your numeric id>
. ~/.goodreads/auth.sh          # required — goodreads-cli does NOT auto-load auth

python pipeline/bookmesh.py pull       # Goodreads to-read + Amazon wishlist -> state/
python pipeline/bookmesh.py diff       # union + overlap of both lists
python pipeline/bookmesh.py search     # resolve titles on libgen.li
python pipeline/bookmesh.py download   # fetch + MD5-verify -> books/
python pipeline/bookmesh.py send       # dry-run; add --execute to push to Kindle
```

Stages are independent and idempotent — rerun any of them. `send` without `--execute` is a dry run.

Env: `GOODREADS_CLI` and `KINDLE_CLI` point at the two CLI directories; `GOODREADS_COOKIE` is
required for `pull`.

## The two CLIs these skills drive

| Surface | Repo | Auth file | Auto-loads? |
|---|---|---|---|
| Amazon / Kindle | `zaydiscold/amazon-kindle-cli-mcp-api` | `~/.amazon/auth.sh` | **yes** |
| Goodreads | `zaydiscold/goodreads-cli-mcp-api` | `~/.goodreads/auth.sh` | **no — source it** |

That asymmetry is the most common failure. A missing Goodreads cookie returns
`rows: 0, signedOut: false` — an empty result, not an error. It looks like an empty shelf.

MCP is an optional thin adapter; the CLI is the product path and works in a cold shell, in cron,
and from scripts.

## Auth: per-operator, never shared

This is the part that makes the bundle safe to hand around.

- The skills **describe** how auth works. They do not **contain** auth.
- Credentials are session cookies minted from the operator's own signed-in browser and written to
  a local file (`~/.amazon/auth.sh`) that the CLI auto-loads.
- Nothing in this repo can authenticate as anyone. There is no token, key, cookie, account id, or
  user id in it. Personal identifiers were replaced with `<GOODREADS_USER_ID>` /
  `<AMAZON_WISHLIST_ID>` placeholders.

Setup for a new user:

```bash
# 1. Amazon: sign in normally in a dedicated debug browser profile, then
#    harvest an ORIGIN-SCOPED jar for https://www.amazon.com/ only.
# 2. Proof of life (never trust a bare status check):
amazon-kindle-cli auth verify
#    readReady / retailWriteReady / kindleAuthenticated are SEPARATE gates
```

**Do not** flatten every `*amazon*` cookie into one header — multi-origin dumps create duplicate
cookie names and break the session. Origin-scope to `www.amazon.com`.

## Core design rules the skills encode

1. **HTTP/CLI, not browser automation.** Browser/CDP is only for capturing cookies or mapping a
   new contract. An agent that clicks and scrolls Amazon is doing it wrong.
2. **Dry-run by default.** Every write needs `--execute`.
3. **HTTP 200 is not success.** Verify the end state: paginated list membership, Goodreads shelf
   membership, or a Send-to-Kindle receipt. A Kindle `send-v2` upload returns
   `mutationVerified: false` until the receipt reports `IN_LIBRARY`.
4. **Don't conflate surfaces.** Wishlist membership ≠ ownership. Purchased Kindle inventory,
   personal documents, and recent send receipts are three different things.
5. **Reuse the proven parser.** The CLI's shelf parser handles Goodreads markup correctly; a
   hand-rolled regex undercounts badly (69 vs 171 on a real shelf).

## Finding books: mirror reality

Availability is volatile and network-dependent. **Probe before trusting a list.**

Verified at time of writing:

| Source | Status |
|---|---|
| `libgen.li` | ✅ downloadable — primary |
| `z-library.bz` | ✅ search only (real browser defeats DiamWall; 500 results) |
| `z-library.im` | ❌ DiamWall — blocked even in a real browser (IP-level) |
| `libgen.is/.rs/.st` | ❌ TCP timeout |
| `library.lol` | ❌ domain seized |
| `annas-archive.org`, `libgen.gs` | ❌ DNS NXDOMAIN |

Notes that save time:

- Public-domain sources first (Project Gutenberg, Standard Ebooks) — no bot protection.
- Search by **title, not just ISBN**. Catalogue records often carry a different edition's ISBN.
- Download links come from an intermediate page with a **short-lived rotating key**.
- **Verify integrity**: compare the file's MD5 to the catalogue MD5. A mismatch means a rotated key
  or an error page, not a usable book.
- `z-library.bz` is useful for discovery metadata (format, size, language) even when `.im` blocks
  the download.

## Format conversion

Calibre (`ebook-convert in.epub out.pdf --paper-size letter`) covers EPUB→PDF. If a mirror only
offers an OCR'd derivative, prefer converting a clean retail EPUB over using the OCR copy.

## Scope note

These skills are an operator's working notes, not a polished product. They assume a Unix-ish
shell with Windows paths in places, and they will need light editing for another environment.
Treat the HTTP contracts as "verified at a point in time" — Amazon and Goodreads change them.
