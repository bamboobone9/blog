import re
import time
import random
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

# -------- CONFIG --------
INPUT_MD = Path("/Users/bamboo/Documents/兴趣/Blog/HugoHost/bamboobone-blog/content/posts/cultural/book-list-mystery-crime-detective-novel-underrated-recs-1.md")  # <-- change
OUTPUT_MD = Path("/Users/bamboo/Documents/兴趣/Blog/HugoHost/bamboobone-blog/content/posts/cultural/book-list-mystery-crime-detective-novel-underrated-recs-1-linkcard.md")

SLEEP_RANGE = (0.6, 1.3)
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://book.douban.com/",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
}

TITLE_LINE_RE = re.compile(r"^\s*(\d+)\.\s*(.+?)\s*$")  # 4. 书名
# 第二行：作者 / 年份 / 出版社
META_LINE_RE = re.compile(r"^\s*([^/]+?)\s*/\s*(\d{4})\s*/\s*(.+?)\s*$")

def sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip(), b.strip()).ratio()

def douban_suggest(query: str):
    url = f"https://book.douban.com/j/subject_suggest?q={quote(query)}"
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return r.json()  # list of dicts

def pick_best(title: str, author: str, items):
    """
    items fields usually include: title, url, author_name, publisher, year, etc.
    We'll score by title similarity + author containment (soft).
    """
    best = ("", 0.0)
    for it in items:
        t = (it.get("title") or "").strip()
        u = (it.get("url") or "").strip()
        a = (it.get("author_name") or "").strip()

        if not t or not u or "book.douban.com/subject/" not in u:
            continue

        score = sim(t, title)

        # bonus if author matches/contained (Chinese names can vary)
        if author and a and (author in a or a in author):
            score += 0.25

        if score > best[1]:
            best = (u.split("?")[0], score)

    # threshold to avoid garbage matches
    if best[1] < 0.60:
        return ""
    return best[0]

def main():
    text = INPUT_MD.read_text(encoding="utf-8")
    lines = text.splitlines()

    out = []
    failures = []

    i = 0
    while i < len(lines):
        line = lines[i]
        m = TITLE_LINE_RE.match(line)

        if not m:
            out.append(line)
            i += 1
            continue

        num = m.group(1)
        title = m.group(2).strip()

        # 默认把下一行当作 meta（作者/年份/出版社）
        meta_line = lines[i + 1] if i + 1 < len(lines) else ""
        m2 = META_LINE_RE.match(meta_line)

        if not m2:
            # 如果下一行不是 meta，就原样输出
            out.append(line)
            i += 1
            continue

        author = m2.group(1).strip()

        # 原样输出两行
        out.append(line)
        out.append(meta_line)

        # 如果后面已经有 linkcard，就不重复插入
        next_line = lines[i + 2] if i + 2 < len(lines) else ""
        if "{{< linkcard" in next_line:
            i += 2
            continue

        # 搜索：用 "书名 作者"
        q = f"{title} {author}".strip()
        try:
            items = douban_suggest(q)
            url = pick_best(title, author, items)
        except Exception as e:
            url = ""
            failures.append((title, author, f"search error: {repr(e)}"))

        if url:
            out.append(f'{{{{< linkcard "{url}" >}}}}')
        else:
            failures.append((title, author, "no good match"))

        # 保留一个空行（让排版好看）
        out.append("")

        time.sleep(random.uniform(*SLEEP_RANGE))
        i += 2

    OUTPUT_MD.write_text("\n".join(out) + "\n", encoding="utf-8")

    print(f"Wrote: {OUTPUT_MD}")
    if failures:
        print("\nNeeds manual check:")
        for t, a, reason in failures[:40]:
            print(f"- {t} / {a}  ({reason})")
        if len(failures) > 40:
            print(f"... and {len(failures) - 40} more")

if __name__ == "__main__":
    main()