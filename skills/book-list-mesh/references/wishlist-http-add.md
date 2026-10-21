# Wishlist HTTP add — live map (2026-08-01)

## Endpoint

`POST https://www.amazon.com/hz/wishlist/additemtolist?ie=UTF8`

## Headers

- `Cookie: $AMAZON_COOKIE`
- `anti-csrftoken-a2z: <from product page form>`
- `Content-Type: application/x-www-form-urlencoded;charset=UTF-8`
- `X-Requested-With: XMLHttpRequest`
- `Origin: https://www.amazon.com`
- `Referer: https://www.amazon.com/dp/{ASIN}`

## Body

```
asin={ASIN}
vendorId=website.wishlist.detail.add
listType=wishlist
isAjax=1
listId={optional AMAZON_WISHLIST_ID e.g. <AMAZON_WISHLIST_ID>}
```

## CSRF source (critical)

Prefer hidden input inside `#addToWishListForm`:

```regex
name="anti-csrftoken-a2z"\s*value="([^"]+)"
```

Meta-only / wrong token → HTTP **403** with “Page Not Found” HTML (not a real 404 route miss).

## Success body markers

- `id="huc-atwl-inner"` / “View Your List”
- **or** “This item was already in” + “We've moved it to the top of the list.”

## Verification

1. Parse add response for markers above
2. `wishlist list --list-id …` full HTTP pagination (`slv/items`) — not page-1 SSR alone
3. Confirm ASIN in `data.items[]`

## Live proof

- Discount Dan ASIN `B0DSGQ5XPS` on Shopping List `<AMAZON_WISHLIST_ID>`
- Code: `cli/src/client/wishlistHttp.ts` (merged master)

## Capture method

CDP `Network.enable` on product page → one click to snag XHR **for mapping only**. Product path stays pure HTTP. No browser product path on CLI/MCP.
