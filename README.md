# Book Mesh Playbook

A portable, credential-free bundle for AI agents that acquire ebooks and move them between
Goodreads, Amazon lists, and a Kindle — without browser automation or a shared login.

**Nothing here contains a credential.** Every secret lives on the operator's own machine and is
minted from *their* browser session. A friend clones this, logs into their own accounts, and
their agent reproduces the same workflow.

## What's in the box

```
skills/
  free-book-download/    # finding + fetching public-domain and free ebooks
  amazon-kindle-cli/     # Send-to-Kindle, wishlist, auth recovery SOP
  book-list-mesh/        # Goodreads <-> Amazon mesh, HTTP contracts, shipping gates
```

Each is a `SKILL.md` plus `references/`. Drop them into any agent that supports skill/prompt
directories (Hermes, Claude Code, Codex, Cursor, etc.) — they're plain markdown.

## The two CLIs these skills drive

| Surface | Repo | Auth file |
|---|---|---|
| Amazon / Kindle | `zaydiscold/amazon-kindle-cli-mcp-api` | `~/.amazon/auth.sh` |
| Goodreads | `zaydiscold/goodreads-cli-mcp-api` | `~/.goodreads/auth.sh` |

Both are **public**. MCP is an optional thin adapter — the CLI is the product path and works in
a cold shell, in cron, and from scripts.

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

## Finding books: mirror reality

`free-book-download` documents what actually works, verified rather than assumed:

- Public-domain sources first (Project Gutenberg, Standard Ebooks) — no bot protection.
- Mirror availability is volatile and DNS-dependent; **probe before trusting a list**. At the last
  verification only `libgen.li` answered while several well-known mirrors timed out or failed DNS.
- Search by **title as well as ISBN**. Catalogue records often carry a different edition's ISBN,
  so an ISBN search can return nothing for a book that is definitely present.
- Download links may require a short-lived key from an intermediate page; the key rotates.
- **Verify integrity by comparing the file's MD5 to the catalogue MD5**, then confirm identity from
  the file's own internal metadata rather than the listing.

## Format conversion

Calibre (`ebook-convert in.epub out.pdf --paper-size letter`) covers EPUB→PDF. If a mirror only
offers an OCR'd derivative, prefer converting a clean retail EPUB over using the OCR copy.

## Scope note

These skills are an operator's working notes, not a polished product. They assume a Unix-ish
shell with Windows paths in places, and they will need light editing for another environment.
Treat the HTTP contracts as "verified at a point in time" — Amazon and Goodreads change them.
