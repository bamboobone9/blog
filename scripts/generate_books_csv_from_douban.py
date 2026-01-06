import os
import re
import csv
import time
import random
from pathlib import Path
from urllib.parse import urlparse

import requests

# -------- CONFIG --------
CONTENT_DIR = Path("/Users/bamboo/Documents/兴趣/Blog/HugoHost/bamboobone-blog/content/posts")  # run from scripts/
OUT_CSV = Path("books.csv")
FAIL_CSV = Path("books_failed.csv")

# Match: {{< linkcard "https://book.douban.com/subject/35031587/" >}}
LINKCARD_RE = re.compile(
    r"""\{\{\<\s*linkcard\s+"(https?://book\.douban\.com/subject/\d+/?[^"]*)"\s*\>\}\}""",
    re.IGNORECASE,
)

# Extract og:image from HTML
OG_IMAGE_RE = re.compile(
    r"""<meta\s+[^>]*property=["']og:image["'][^>]*content=["']([^"']+)["'][^>]*>""",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari",
    "Referer": "https://book.douban.com/",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
}

def file_slug_from_context(md_path: Path, subject_id: str, idx: int) -> str:
    # Use file stem as base, fallback to subject id
    stem = md_path.stem.strip() or f"douban-{subject_id}"
    # If one file has multiple douban links, make slugs unique
    suffix = f"-{idx}" if idx > 1 else ""
    # normalize to url-safe-ish
    safe = re.sub(r"[^a-zA-Z0-9\-]+", "-", stem).strip("-").lower()
    if not safe:
        safe = f"douban-{subject_id}"
    return f"{safe}{suffix}"

def get_subject_id(url: str) -> str:
    m = re.search(r"/subject/(\d+)", url)
    return m.group(1) if m else "unknown"

def fetch_og_image(douban_page_url: str, timeout=25) -> str:
    r = requests.get(douban_page_url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    html = r.text
    m = OG_IMAGE_RE.search(html)
    if not m:
        return ""
    return m.group(1).strip()

def main():
    if not CONTENT_DIR.exists():
        raise SystemExit(f"CONTENT_DIR not found: {CONTENT_DIR.resolve()}")

    md_files = list(CONTENT_DIR.rglob("*.md"))
    found = []  # list of dicts: slug, douban_page_url, douban_image_url
    seen_sids = set()

    for md in md_files:
        try:
            text = md.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # try fallback
            text = md.read_text(encoding="utf-8", errors="ignore")

        matches = LINKCARD_RE.findall(text)
        if not matches:
            continue


        for page_url in matches:
            # normalize trailing slash
            if not page_url.endswith("/"):
                page_url = page_url + "/"

            # de-dupe exact page URL across site
            sid = get_subject_id(page_url)
            if sid in seen_sids:
                continue
            seen_sids.add(sid)

            sid = get_subject_id(page_url)
            slug = f"book-{sid}"

            found.append(
                {
                    "slug": slug,
                    "douban_page_url": page_url,
                    "subject_id": sid,
                }
            )

    print(f"Found {len(found)} unique Douban linkcards.")

    ok_rows = []
    fail_rows = []

    for i, item in enumerate(found, 1):
        page_url = item["douban_page_url"]
        slug = item["slug"]

        print(f"[{i}/{len(found)}] Fetching og:image: {page_url}")
        try:
            img_url = fetch_og_image(page_url)
            if not img_url:
                raise RuntimeError("og:image not found")
            ok_rows.append({"slug": slug, "douban_image_url": img_url})
            print(f"  OK  {slug} -> {img_url}")
        except Exception as e:
            fail_rows.append(
                {
                    "slug": slug,
                    "douban_page_url": page_url,
                    "error": repr(e),
                }
            )
            print(f"  FAIL {slug}: {repr(e)}")

        # polite delay
        time.sleep(random.uniform(0.8, 1.8))

    # Write books.csv for your downloader
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["slug", "douban_image_url"])
        w.writeheader()
        w.writerows(ok_rows)

    # Write failures (so you can re-run / patch)
    with FAIL_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["slug", "douban_page_url", "error"])
        w.writeheader()
        w.writerows(fail_rows)

    print(f"\nWrote: {OUT_CSV} ({len(ok_rows)} rows)")
    print(f"Wrote: {FAIL_CSV} ({len(fail_rows)} rows)")

if __name__ == "__main__":
    main()
