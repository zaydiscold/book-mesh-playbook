# Send-to-Kindle web HTTP (mapped 2026-08-01)

Product path only. Browser/CDP is for cookie mint + one-shot contract sniff.

## End-to-end

1. `GET https://www.amazon.com/sendtokindle` (cookie + browser UA)
2. Extract CSRF from page HTML:
   - **Primary:** `<input name="csrfToken" value="TOKEN">`
   - STK bundle (`KindleDocsWebServiceBuzzAssets-home` JS) uses `DndUtils.getCsrfToken()` → `$('input[name="csrfToken"]')[0].value`
   - Do **not** prefer generic navbar/meta `anti-csrftoken-a2z` — wrong surface
3. `POST /sendtokindle/init`  
   Headers: `Content-Type: application/json`, `anti-csrftoken-a2z: <csrfToken value>`  
   Body shape (from live JS):
   ```json
   {
     "fileSize": 12345,
     "contentType": "application/epub+zip",
     "appVersion": "1.0",
     "appName": "<DRAG_DROP_WEB constant from bundle>",
     "fileExtension": "epub"
   }
   ```
   Response: `{ "uploadUrl": "https://…", "stkToken": "…" }`
4. `PUT` file bytes to signed `uploadUrl` (presigned S3-style)
5. `POST /sendtokindle/send-v2` with JSON including `stkToken`, title, author, archive/deviceList, `inputFileName`, `batchId`, etc. Same CSRF header.
6. Verify: `GET /sendtokindle/recent-docs` — title match on returned docs. HTTP 200 on send alone is not enough; confirm receipt feed.

## Validated batch

Eight DCC EPUBs (`kindle-batch/`) — 8/8 `send-v2` 200 after csrfToken fix; `recent-docs` returned 8 docs.

## Related routes in same bundle

| Path | Role |
|---|---|
| `/sendtokindle/get-device-list` | device picker |
| `/sendtokindle/recent-docs` | receipt feed |
| `/sendtokindle/dnd_metrics` | client metrics (optional) |

## Shared client pitfalls

- Custom CLI User-Agent + valid cookies → Amazon may return **sign-in HTML** instead of STK app. Use browser-compatible desktop Chrome UA on the shared Amazon HTTP header builder (`cli/src/client/httpHeaders.ts`). Header parity, not browser runtime.
- Keep browser capture helpers as RE references; remove from **runtime** CLI/MCP only. User: don't delete helpers — swap non-HTTP call sites.
- STK CSRF surface ≠ wishlist: STK = `<input name="csrfToken">`; wishlist add = form `anti-csrftoken-a2z`. Separate extractors.
- Valid extensions: `doc docx html htm rtf txt jpeg jpg png bmp gif epub pdf` (max ~200MB).
- Proof bar: `send-v2` 200 **and** `recent-docs` title match.

## Code pointers

- `cli/src/client/kindleWebUpload.ts` — CSRF extract + init/put/send
- `cli/src/client/httpHeaders.ts` — shared browser-compatible headers
- `api-map/amazon-web.yaml` — OpenAPI surface
- Cutover rules: `references/http-cutover-rules.md`
