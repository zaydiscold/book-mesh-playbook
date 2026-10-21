---
name: free-book-download
description: Use when locating and delivering legally available ebook or audiobook editions. Verify format, edition, and release status before acquisition.
version: 1.3.0
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [books, ebooks, audiobooks, library, gutenberg, standardebooks, kindle]
---

# Legal Book Acquisition & Edition Verification

Locate the exact edition the user wants through authorized sources, verify that it is the requested work and format, then deliver or add it only through an authorized personal-library path.

## When to use
- User wants an ebook, PDF, audiobook, Kindle copy, or library-accessible edition
- User asks whether a newly released installment exists in text or audio
- User needs the right edition, ISBN, or format for a reading device

## Procedure

1. **Normalize the target before searching.** Record title, author, series number if applicable, requested format, and ISBN when supplied. Preserve apostrophes and subtitles in the final metadata comparison, but try a title variant without punctuation if a catalog query returns no result.

2. **Establish current publication status from official sources.** For in-copyright books, check the author's site, publisher/imprint, and the authorized retailer or audiobook publisher. Date-stamp the result. Distinguish:
   - audiobook release;
   - ebook/print release;
   - announced/preorder status;
   - library availability.
   Do not infer that a text edition exists merely because an audiobook has released.

3. **Use authorized acquisition routes.** Prefer the user's owned retailer/library account, the publisher, public-library lending, Project Gutenberg, or Standard Ebooks. Never source, download, distribute, or convert unauthorized copies or fan transcriptions of in-copyright books.

4. **Verify the acquired file before placing it in the library.** Confirm format/magic bytes, inspect EPUB internal OPF metadata (title, creator, publisher, identifier), and compare against the requested work. For a PDF, confirm it opens and has extractable or visually legible content; do not treat a catalog listing or an HTTP success as proof.

5. **Deliver exactly as requested.** Put local copies in the user's designated Books folder. If they request Kindle delivery, use the approved Kindle workflow and verify receipt/library visibility after sending; a local copy alone is not Kindle delivery.

6. **Report in two compact parts.** State (a) availability/release status, including format-specific dates if relevant, then (b) what was acquired or sent, including any remaining gate such as a login or purchase.

## Series and audiobook-first releases

- **Treat release formats as separate products.** Audiobook-first publishing can make the same installment appear to have two releases; give the audio and text dates separately.
- **Verify installment identity from a primary source.** A title may be adjacent to an earlier book's wording or quote; confirm its series number before saying it is a new installment.
- **Do not recommend unofficial transcriptions.** Their quality, completeness, and authorization cannot be assumed; offer the official audio, preorder, library hold, or the announced text date instead.

## File verification

| Check | Method | Valid result |
|---|---|---|
| Format | Inspect magic bytes / file type | PDF begins `%PDF-`; EPUB is a ZIP container |
| EPUB identity | Read `META-INF/container.xml`, then OPF `dc:title`, `dc:creator`, `dc:publisher`, identifier | Matches requested work and edition |
| PDF usability | Open/extract a short sample or inspect pages | Actual readable book, not an HTML error page |
| Delivery | Read back target folder or check authorized library | Exact expected file or library item is present |

## Pitfalls

- **Check official release pages before discussing availability — retailer/catalog metadata can confuse audiobook, ebook, print, preorder, and regional editions.**
- **Search punctuation variants only after preserving the canonical title — apostrophes commonly reduce catalog recall, but the final identity check must use the true title.**
- **Verify EPUB metadata rather than trusting filenames or search snippets — user-uploaded filenames routinely omit edition and translator information.**
- **Do not call a book sent to Kindle until its library/device receipt is verified — copying it to a local folder is a separate action.**
- **Keep format conversion secondary to authorization — converting an owned/authorized EPUB can satisfy a format need, but does not make an unauthorized source acceptable.**

## Related tools

- Project Gutenberg — public-domain texts
- Standard Ebooks — curated public-domain EPUBs
- User's authorized retailer and public-library accounts — current in-copyright titles
- `amazon-kindle-cli` — only when Kindle library delivery is explicitly requested
