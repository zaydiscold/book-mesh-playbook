#!/usr/bin/env python3
"""
Bidirectional list sync: Goodreads to-read  <->  Amazon wishlist.

  goodreads-only  -> add the ASIN to the Amazon wishlist
  amazon-only     -> add the book to the Goodreads to-read shelf

Dry-run by default. Every action is logged to state/sync-log.json so a rerun
resumes instead of repeating work.

  python sync.py                 # plan only
  python sync.py --execute       # perform writes
  python sync.py --limit 20      # cap actions this run
  python sync.py --direction gr2amz|amz2gr
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(ROOT, "state")
LOG = os.path.join(STATE, "sync-log.json")

KINDLE_CLI = os.environ.get("KINDLE_CLI", "")
GR_CLI = os.environ.get("GOODREADS_CLI", "")


def load(p, default):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()


def run(cmd, cwd, timeout=180):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def gr_book_id(title, author):
    """Resolve a title/author to a Goodreads book id.

    /search redirect-loops under anti-bot, but /book/auto_complete still returns clean
    JSON with bookId. Prefer it; fall back to the CLI's search.
    """
    import urllib.parse
    q = f"{title} {author}".strip()
    cookie = os.environ.get("GOODREADS_COOKIE", "")
    url = ("https://www.goodreads.com/book/auto_complete?format=json&q="
           + urllib.parse.quote_plus(q))
    try:
        p = subprocess.run(["curl", "-s", "--max-time", "30",
                            "-A", ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                   "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"),
                            "-H", f"Cookie: {cookie}", url],
                           capture_output=True, text=True, timeout=60)
        raw = p.stdout.strip()
        i = raw.find("[")
        cands = json.loads(raw[i:]) if i >= 0 else []
    except Exception:
        cands = []

    if not cands:
        rc, out, err = run(["node", "dist/index.js", "search", "books", "--query", q, "--json"],
                           GR_CLI, timeout=240)
        j = out.find("{")
        if j >= 0:
            try:
                d = json.loads(out[j:])
                data = d.get("data") or d
                cands = data.get("books") or data.get("results") or []
            except Exception:
                cands = []

    tw = [w for w in norm(title).split() if len(w) > 2]
    aw = [w for w in norm(author).split() if len(w) > 2]
    best = None
    for c in cands:
        ct = norm(c.get("bookTitleBare") or c.get("title") or "")
        if not tw:
            continue
        score = sum(1 for w in tw if w in ct) / len(tw)
        # reject study guides / summaries masquerading as the book
        if re.search(r"\b(summary|study guide|analysis|cliffsnotes|sparknotes)\b", ct):
            continue
        if score >= 0.75:
            if best is None or score > best[0]:
                best = (score, str(c.get("bookId") or c.get("id") or ""))
    return best[1] if best and best[1] else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--direction", choices=["gr2amz", "amz2gr"], default=None)
    ap.add_argument("--delay", type=float, default=6.0)
    a = ap.parse_args()

    if not KINDLE_CLI or not GR_CLI:
        sys.exit("set KINDLE_CLI and GOODREADS_CLI to the two CLI directories")

    merged = load(os.path.join(STATE, "merged.json"), {"items": []})["items"]
    log = load(LOG, {"gr2amz": {}, "amz2gr": {}})

    gr_only = [m for m in merged if m.get("on_goodreads") and not m.get("on_amazon")]
    amz_only = [m for m in merged if m.get("on_amazon") and not m.get("on_goodreads")]

    print(f"goodreads-only: {len(gr_only)}   amazon-only: {len(amz_only)}")
    print(f"already synced: gr2amz={len(log['gr2amz'])} amz2gr={len(log['amz2gr'])}")
    print(f"mode: {'EXECUTE' if a.execute else 'DRY RUN'}\n")

    actions = 0
    # Goodreads -> Amazon wishlist
    if a.direction in (None, "gr2amz"):
        for m in gr_only:
            key = norm(m["title"])
            if key in log["gr2amz"]:
                continue
            if a.limit and actions >= a.limit:
                break
            print(f"[gr2amz] {m['title'][:52]}")
            if not a.execute:
                actions += 1
                continue
            rc, out, err = run(["node", "dist/index.js", "wishlist", "add",
                                "--title", m["title"], "--author", m.get("author") or "",
                                "--execute"], KINDLE_CLI, timeout=300)
            ok = '"ok": true' in out and "added" in out.lower()
            log["gr2amz"][key] = {"ok": ok, "title": m["title"], "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            save(LOG, log)
            print(f"        -> {'OK' if ok else 'FAIL'}")
            actions += 1
            time.sleep(a.delay)

    # Amazon wishlist -> Goodreads to-read
    if a.direction in (None, "amz2gr"):
        for m in amz_only:
            key = norm(m["title"])
            if key in log["amz2gr"]:
                continue
            if a.limit and actions >= a.limit:
                break
            print(f"[amz2gr] {m['title'][:52]}")
            if not a.execute:
                actions += 1
                continue
            bid = gr_book_id(m["title"], m.get("author") or "")
            if not bid:
                log["amz2gr"][key] = {"ok": False, "title": m["title"], "error": "no book id"}
                save(LOG, log)
                print("        -> FAIL (unresolved)")
                actions += 1
                continue
            rc, out, err = run(["node", "dist/index.js", "library", "set-status",
                                "--book-id", bid, "--status", "to-read",
                                "--approved-book-id", bid, "--approved-status", "to-read",
                                "--execute"],
                               GR_CLI, timeout=300)
            ok = rc == 0 and ('"ok": true' in out or '"submitted": true' in out)
            log["amz2gr"][key] = {"ok": ok, "title": m["title"], "bookId": bid,
                                  "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            save(LOG, log)
            print(f"        -> {'OK' if ok else 'FAIL'} (book {bid})")
            actions += 1
            time.sleep(a.delay)

    print(f"\nactions this run: {actions}")
    if not a.execute:
        print("dry run — pass --execute to write")


if __name__ == "__main__":
    main()
