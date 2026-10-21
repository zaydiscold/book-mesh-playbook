# HTTP cutover rules (Amazon/Goodreads mesh)

User-enforced product rules from 2026-08-01 mesh work.

## Stack shape

**api-map → CLI → MCP**, all HTTP/scriptable.

Browser/CDP only for:

1. Minting cookies into `~/.amazon/auth.sh` / `~/.goodreads/auth.sh`
2. One-shot contract sniff (capture helpers, HAR, JS bundle map)

Never for: wishlist scroll, send-to-kindle UI clicks, product list verification.

## Keep helpers, swap runtime

When converting a command from browser to HTTP:

- **Delete** runtime call sites that launch/drive a browser
- **Keep** helper modules used for capture, login, and route discovery
- Do not “clean up” helpers mid-cutover because they look unused from product paths

## Header / CSRF surfaces (do not mix)

| Surface | CSRF source | UA |
|---|---|---|
| Wishlist add | product page form `anti-csrftoken-a2z` | browser Chrome UA |
| Wishlist list | cookie session only | browser Chrome UA |
| Send-to-Kindle | `<input name="csrfToken">` → header `anti-csrftoken-a2z` | browser Chrome UA |

Custom CLI UA with valid cookies → Amazon sign-in HTML trap.

## Proof bars

- Wishlist membership: full `slv/items` pagination, not page-1 SSR
- Kindle send: `send-v2` 200 **and** `recent-docs` title match
- Never claim success from HTTP status alone when body can be sign-in HTML

## Shipping

- CLI and MCP capability parity test required
- GitHub is source of truth; push amazon-kindle-cli-mcp-api, not only goodreads
- Parallelize independent diagnostics
