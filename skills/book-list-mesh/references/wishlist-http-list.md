# Amazon wishlist list — HTTP pagination (2026-08-01)

## Why page-1 is a lie

`GET /hz/wishlist/ls/{listId}` SSR returns ~10 `itemName_*` rows plus a `showMoreUrl` / `paginationToken`. Curl of that page alone will miss most ASINs (including titles the UI already shows after lazy load).

## Contract

1. **First page**
   - `GET https://www.amazon.com/hz/wishlist/ls/{listId}?sort=date-added&viewType=list`
   - Cookie: `AMAZON_COOKIE`
   - Parse:
     - list name (`#profile-list-name` / h1)
     - items: anchors `id="itemName_{itemId}"` → href `/dp/{ASIN}`, title text, optional `item-byline-*`
     - next: `"showMoreUrl":"/hz/wishlist/slv/items?filter=unpurchased&paginationToken=…"`  
       or hidden `name="showMoreUrl" value="…"`

2. **More pages**
   - `GET https://www.amazon.com` + showMoreUrl (absolute)
   - Headers: same cookie, `X-Requested-With: XMLHttpRequest`, Accept html/json
   - Body may be HTML fragment **or** JSON wrapping html — try `JSON.parse` then fall back to HTML
   - Merge items by ASIN/title; stop when no new items or no further showMoreUrl
   - Safety cap: ~40 hops

## CLI

```bash
source ~/.amazon/auth.sh
# prefer env AMAZON_WISHLIST_ID=<AMAZON_WISHLIST_ID>
node cli/dist/index.js wishlist list --list-id <AMAZON_WISHLIST_ID>
# envelope: data.via=http, data.pagesFetched, data.items[]
```

## Live proof (session)

- list id `<AMAZON_WISHLIST_ID>`
- `pagesFetched=6`, `n=47`, Discount Dan `B0DSGQ5XPS` present
- Code: `cli/src/client/wishlistListHttp.ts`, parser `cli/src/parsers/wishlist.ts`
- api-map: `/hz/wishlist/slv/items`

## Do not

- Browser scroll / CDP DOM walks as the default list path
- Claim “missing from list” from a single SSR page
- Print cookies or pagination tokens in user-facing logs
- Delete capture/debug helpers while converting product paths to HTTP — swap runtime only
- Run independent probes serially when auth dump, pagination walk, and JS map can parallelize

## Related

- STK HTTP + csrfToken + browser UA: `references/send-to-kindle-http.md`
- Cutover rules: `references/http-cutover-rules.md`
