#!/usr/bin/env python3
"""
book-mesh pipeline: pull reading lists -> resolve against a catalog mirror -> download -> Kindle.

Stages are independent and idempotent; run them in order or individually.

  pull      Goodreads to-read + Amazon wishlist -> state/*.json
  diff      union/diff of the two lists          -> state/merged.json
  search    resolve each title on libgen.li      -> state/matches.json
  download  fetch + MD5-verify                   -> books/
  send      push to Kindle, verify receipts      -> state/sent.json

Auth (per-operator, never shared):
  Goodreads  export GOODREADS_COOKIE  (or . ~/.goodreads/auth.sh)   <- NOT auto-loaded
  Amazon     amazon-kindle-cli auto-loads ~/.amazon/auth.sh          <- auto-loaded

Usage:
  python bookmesh.py pull
  python bookmesh.py diff
  python bookmesh.py search [--limit N]
  python bookmesh.py download
  python bookmesh.py send [--dry-run]
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, time, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(ROOT, "state")
BOOKS = os.path.join(ROOT, "books")
CACHE = os.path.join(STATE, "cache")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
GOODREADS_USER = os.environ.get("GOODREADS_USER_ID", "")
LIBGEN = "https://libgen.li"


def w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def r(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8", errors="replace") as f:
        return json.load(f)


def curl(url, out=None, cookie=None, timeout=40, referer=None):
    cmd = ["curl", "-s", "-L", "--max-time", str(timeout), "-A", UA]
    if cookie:
        cmd += ["-H", f"Cookie: {cookie}"]
    if referer:
        cmd += ["-e", referer]
    if out:
        cmd += ["-o", out]
    cmd.append(url)
    subprocess.run(cmd, check=False)
    return open(out, encoding="utf-8", errors="replace").read() if out and os.path.exists(out) else ""


def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())


def clean_title(t):
    t = re.sub(r"\s*\([^)]*#\d+[^)]*\)", "", t or "")
    return re.sub(r"\s*\([^)]*\)\s*$", "", t).strip()


# ---------------------------------------------------------------- pull

def stage_pull():
    os.makedirs(STATE, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    user = GOODREADS_USER or os.environ.get("GOODREADS_USER", "")
    if not user:
        sys.exit("set GOODREADS_USER_ID (your numeric Goodreads id)")
    cookie = os.environ.get("GOODREADS_COOKIE", "")
    if not cookie:
        sys.exit("GOODREADS_COOKIE is empty. goodreads-cli does NOT auto-load auth — "
                 "run `. ~/.goodreads/auth.sh` first (or export the cookie).")

    # --- Goodreads to-read, paginated. per_page=100; declared count comes from <title>.
    # Parse with the goodreads-cli's own proven cheerio parser (regex alone undercounts).
    parser_dir = os.environ.get("GOODREADS_CLI", "")
    page, seen, declared, rows = 1, set(), None, []
    while page <= 20:
        fn = os.path.join(CACHE, f"gr-p{page}.html")
        html = curl(f"https://www.goodreads.com/review/list/{user}"
                    f"?shelf=to-read&per_page=100&page={page}", out=fn, cookie=cookie)
        if declared is None:
            m = re.search(r"\((\d[\d,]*)\s+books?\)", html)
            declared = int(m.group(1).replace(",", "")) if m else None
        this_page = []
        if parser_dir and os.path.exists(os.path.join(parser_dir, "dist", "parsers", "shelfHtml.js")):
            js = (
                "import {parseShelfHtml} from './dist/parsers/shelfHtml.js';"
                "import fs from 'fs';"
                f"const r=parseShelfHtml(fs.readFileSync({json.dumps(fn)},'utf8'));"
                "console.log(JSON.stringify({declared:r.declaredBookCount,"
                "rows:r.rows.map(x=>({bookId:x.bookId,title:x.title,author:x.author}))}));"
            )
            p = subprocess.run(["node", "--input-type=module", "-e", js],
                               cwd=parser_dir, capture_output=True, text=True, timeout=180)
            try:
                blob = p.stdout[p.stdout.find("{"):]
                parsed = json.loads(blob)
                declared = declared or parsed.get("declared")
                this_page = parsed.get("rows") or []
            except Exception:
                this_page = []
        if not this_page:  # fallback: coarse regex
            for m in re.finditer(r'href="/book/show/(\d+)[^"]*"[^>]*>([^<]{1,200})</a>', html):
                this_page.append({"bookId": m.group(1), "title": m.group(2).strip(), "author": ""})
        fresh = 0
        for row in this_page:
            bid = str(row.get("bookId") or "")
            if not bid or bid in seen:
                continue
            seen.add(bid); fresh += 1
            rows.append({"bookId": bid, "title": row.get("title", ""),
                         "author": row.get("author", ""), "source": "goodreads_to_read"})
        if fresh == 0 or (declared and len(seen) >= declared) or len(this_page) < 100:
            break
        page += 1
    w(os.path.join(STATE, "goodreads.json"),
      {"shelf": "to-read", "declared": declared, "count": len(rows), "items": rows})
    print(f"  goodreads to-read: {len(rows)} (declared {declared})")

    # --- Amazon wishlist via the CLI (auto-loads its own auth)
    try:
        out = subprocess.run(["node", "dist/index.js", "wishlist", "list", "--json"],
                             cwd=os.environ.get("KINDLE_CLI", "."),
                             capture_output=True, text=True, timeout=300).stdout
        i = out.find("{")
        wl = json.loads(out[i:])["data"]["items"] if i >= 0 else []
    except Exception as e:
        print(f"  amazon wishlist: SKIPPED ({e})")
        wl = []
    amz = [{"asin": x.get("asin"), "title": x.get("title"), "author": x.get("author"),
            "source": "amazon_wishlist"} for x in wl]
    w(os.path.join(STATE, "amazon.json"), {"count": len(amz), "items": amz})
    print(f"  amazon wishlist: {len(amz)}")


# ---------------------------------------------------------------- diff

def stage_diff():
    gr = r(os.path.join(STATE, "goodreads.json"), {"items": []})["items"]
    amz = r(os.path.join(STATE, "amazon.json"), {"items": []})["items"]
    amz_keys = {norm(clean_title(x["title"])) for x in amz}
    merged, seen = [], set()
    for x in amz:
        k = norm(clean_title(x["title"]))
        if k and k not in seen:
            seen.add(k); merged.append({**x, "on_amazon": True, "on_goodreads": False})
    new = []
    for x in gr:
        k = norm(clean_title(x["title"]))
        if not k:
            continue
        if k in seen:
            for m in merged:
                if norm(clean_title(m["title"])) == k:
                    m["on_goodreads"] = True
                    break
            continue
        seen.add(k)
        entry = {**x, "on_amazon": False, "on_goodreads": True}
        merged.append(entry); new.append(entry)
    w(os.path.join(STATE, "merged.json"),
      {"total": len(merged), "both": sum(1 for m in merged if m["on_amazon"] and m["on_goodreads"]),
       "goodreads_only": len(new), "amazon_only": sum(1 for m in merged if m["on_amazon"] and not m["on_goodreads"]),
       "items": merged})
    print(f"  merged: {len(merged)}  (goodreads-only {len(new)}, both {sum(1 for m in merged if m['on_amazon'] and m['on_goodreads'])})")


# ---------------------------------------------------------------- search

def parse_libgen(html):
    m = re.search(r'id="tablelibgen".*?</table>', html, re.S)
    if not m:
        return []
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(0), re.S)[1:]:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(cells) < 6:
            continue
        c = [re.sub(r"<[^>]+>", " ", x).strip() for x in cells]
        md5 = re.findall(r"\b([a-f0-9]{32})\b", tr)
        ext = re.findall(r">(epub|pdf|mobi|azw3)<", tr, re.I)
        out.append({"title": c[0][:200], "author": c[1][:80], "year": c[3][:10],
                    "lang": c[4][:24], "ext": ext[0].lower() if ext else "",
                    "md5": md5[0] if md5 else ""})
    return out


def stage_search(limit=None):
    merged = r(os.path.join(STATE, "merged.json"), {"items": []})["items"]
    os.makedirs(CACHE, exist_ok=True)
    results = []
    for n, it in enumerate(merged, 1):
        if limit and n > limit:
            break
        base = clean_title(it["title"])
        author = it.get("author") or ""
        surname = author.split(",")[0].strip().split()[-1] if author else ""
        q = f"{base} {surname}".strip()
        fn = os.path.join(CACHE, re.sub(r"[^a-z0-9]+", "_", q.lower())[:80] + ".html")
        if os.path.exists(fn) and os.path.getsize(fn) > 5000:
            html = open(fn, encoding="utf-8", errors="replace").read()
        else:
            html = curl(f"{LIBGEN}/index.php?req={urllib.parse.quote_plus(q)}", out=fn)
            time.sleep(0.9)
        tw = [x for x in norm(base).split() if len(x) > 3][:6]
        best, bs = None, -1
        for cand in parse_libgen(html):
            rn = norm(cand["title"])
            hits = sum(1 for x in tw if x in rn)
            if hits < max(2, len(tw) - 1):
                continue
            s = hits * 10
            if "english" in cand["lang"].lower(): s += 6
            if surname and surname.lower() in norm(cand["author"]): s += 5
            if cand["ext"] == "epub": s += 4
            elif cand["ext"] == "pdf": s += 1
            if s > bs:
                bs, best = s, cand
        results.append({**it, "query": q, "found": bool(best), "best": best})
        print(f"  {'OK' if best else '--'} {n:3}. {base[:46]:<46} {(best['ext'] if best else '')}")
    w(os.path.join(STATE, "matches.json"), results)
    print(f"  matched {sum(1 for x in results if x['found'])}/{len(results)}")


# ---------------------------------------------------------------- download

def safe(name, n=90):
    return re.sub(r"\s+", " ", re.sub(r'[\\/:*?"<>|]', " ", name)).strip()[:n]


def stage_download():
    matches = r(os.path.join(STATE, "matches.json"), [])
    os.makedirs(BOOKS, exist_ok=True)
    done, failed = [], []
    for it in matches:
        if not it["found"]:
            continue
        md5, ext = it["best"]["md5"], it["best"]["ext"] or "epub"
        dest = os.path.join(BOOKS, f"{safe(clean_title(it['title']))}.{ext}")
        if os.path.exists(dest) and os.path.getsize(dest) > 20000:
            done.append({"title": it["title"], "file": dest, "md5": md5, "size": os.path.getsize(dest)})
            print(f"  = have  {os.path.basename(dest)[:52]}")
            continue
        ads = f"{LIBGEN}/ads.php?md5={md5}"
        tmp = os.path.join(CACHE, "ads.html")
        html = curl(ads, out=tmp)
        m = re.search(r"(get\.php\?md5=[a-f0-9]{32}&key=[A-Za-z0-9]+)", html)
        if not m:
            failed.append({"title": it["title"], "reason": "no key"})
            print(f"  X nokey {os.path.basename(dest)[:50]}")
            continue
        curl(f"{LIBGEN}/{m.group(1)}", out=dest, referer=ads, timeout=180)
        if not os.path.exists(dest) or os.path.getsize(dest) < 20000:
            failed.append({"title": it["title"], "reason": "small"})
            continue
        got = hashlib.md5(open(dest, "rb").read()).hexdigest()
        if got != md5:
            os.remove(dest)
            failed.append({"title": it["title"], "reason": f"md5 {got[:8]}"})
            print(f"  X md5   {os.path.basename(dest)[:50]}")
            continue
        done.append({"title": it["title"], "file": dest, "md5": md5, "size": os.path.getsize(dest)})
        print(f"  OK {os.path.getsize(dest):>9,}B {os.path.basename(dest)[:48]}")
        time.sleep(1.0)
    w(os.path.join(STATE, "downloaded.json"), {"done": done, "failed": failed})
    print(f"  downloaded {len(done)}, failed {len(failed)}")


# ---------------------------------------------------------------- send

def stage_send(dry_run=True):
    dl = r(os.path.join(STATE, "downloaded.json"), {"done": []})["done"]
    cli = os.environ.get("KINDLE_CLI", ".")
    files = [d["file"] for d in dl if os.path.exists(d["file"])]
    if not files:
        sys.exit("nothing to send — run download first")
    cmd = ["node", "dist/index.js", "kindle", "send", *files]
    if not dry_run:
        cmd.append("--execute")
    subprocess.run(cmd, cwd=cli, check=False)
    print("  (a successful send is NOT delivery — poll `kindle recent` for IN_LIBRARY)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="stage", required=True)
    sub.add_parser("pull")
    sub.add_parser("diff")
    sp = sub.add_parser("search"); sp.add_argument("--limit", type=int)
    sub.add_parser("download")
    sd = sub.add_parser("send"); sd.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    {"pull": stage_pull, "diff": stage_diff, "download": stage_download}.get(a.stage, lambda: None)()
    if a.stage == "search": stage_search(a.limit)
    if a.stage == "send": stage_send(a.dry_run)


if __name__ == "__main__":
    main()
