#!/usr/bin/env python3
"""
从公开互联网资料（维基、书目库、网页检索、出版社书页）整理简介与目录。

用法:
    python scripts/gen_book_guide.py --title 天路历程 --author 约翰·班扬
    python scripts/gen_book_guide.py --title 认识神 --author 巴刻 --en-title "Knowing God"
    python scripts/gen_book_guide.py --from-repo --write
    python scripts/gen_book_guide.py --title 渴慕神 --author 陶恕 --no-ai
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from list_books import discover_books, repo_root  # noqa: E402

# ========================== 配置 ==========================

API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
API_BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
API_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# 只用于提高英文维基命中率，不作为正文来源
KNOWN_EN_TITLES = {
    "基督教要义": "Institutes of the Christian Religion",
    "天路历程": "The Pilgrim's Progress",
    "宗教情操真伪辨": "A Treatise Concerning Religious Affections",
    "认识神": "Knowing God",
    "至高喜乐的传承": "The Legacy of Sovereign Joy",
    "渴慕神": "The Pursuit of God",
    "信靠神：哪怕风雨如磐": "Trusting God",
    "恩典作王": "The Discipline of Grace",
    "魔鬼家书": "The Screwtape Letters",
    "勿忘死：通往永生盼望的惊人道路": "Remember Death",
    "大阅读家": "Lit!: A Christian Guide to Reading Books",
    "婚姻治愈指南": "What Did You Expect?",
    "父母之道": "Parenting: 14 Gospel Principles That Can Radically Change Your Family",
    "青春的契机": "Age of Opportunity: A Biblical Guide to Parenting Teens",
    "父母的责任": "The Duties of Parents",
    "圣灵论": "Pneumatologia",
    "保守你心": "Keeping the Heart",
    "得胜的祷告：什么拦阻了它？": "Prevailing Prayer: What Hinders It?",
    "因信称义": "The Doctrine of Justification by Faith",
    "对罪的治死": "Of the Mortification of Sin in Believers",
    "治死信徒身上的罪": "Of the Mortification of Sin in Believers",
    "胜过罪与试探": "Overcoming Sin and Temptation",
    "别有洞天：基督徒与现代思潮之比较": "The Universe Next Door",
    "救赎：它的意义及重要性": "The Atonement: Its Meaning and Significance",
    "圣洁：它的本质、阻拦、困难、及根源": "Holiness: Its Nature, Hindrances, Difficulties, and Roots",
    "返璞归真": "Mere Christianity",
    "忏悔录": "Confessions",
    "上帝之城": "The City of God",
    "爱与爱的果实": "Charity and Its Fruits",
    "压伤的芦苇": "The Bruised Reed",
    "福音的荣耀盛宴": "The Glorious Feast of the Gospel",
    "属灵生命的动力": "Dynamics of Spiritual Life",
    "柔和谦卑：基督对罪人和困苦人的心": "Gentle and Lowly",
    "属灵的真义": "True Spirituality",
    "人之废": "The Abolition of Man",
    "荣耀之重": "The Weight of Glory",
    "稀世珍宝：基督徒知足的秘诀": "The Rare Jewel of Christian Contentment",
    "殉道史": "Foxe's Book of Martyrs",
    "普世宣教手册": "Operation World",
    "我真的是基督徒吗？": "Am I Really a Christian?",
}

KNOWN_AUTHORS_EN = {
    "巴刻": "J. I. Packer",
    "加尔文": "John Calvin",
    "约翰·班扬": "John Bunyan",
    "爱德华兹": "Jonathan Edwards",
    "约翰·派伯": "John Piper",
    "陶恕": "A. W. Tozer",
    "毕哲思": "Jerry Bridges",
    "C.S.路易斯": "C. S. Lewis",
    "马修·麦克劳": "Matthew McCullough",
    "托尼·莱因克": "Tony Reinke",
    "保罗·区普": "Paul David Tripp",
    "莱尔": "J. C. Ryle",
    "约翰·欧文": "John Owen",
    "约翰·弗拉维尔": "John Flavel",
    "慕迪": "D. L. Moody",
    "雅各・瑟尼": "James W. Sire",
    "雅各·瑟尼": "James W. Sire",
    "莱昂·莫里斯": "Leon Morris",
    "C. S.路易斯": "C. S. Lewis",
    "奥古斯丁": "Augustine of Hippo",
    "约拿单·爱德华兹": "Jonathan Edwards",
    "薛伯斯": "Richard Sibbes",
    "理查德·洛普雷斯": "Richard F. Lovelace",
    "戴恩·奥特伦": "Dane Ortlund",
    "薛华": "Francis Schaeffer",
    "巴罗夫": "Jeremiah Burroughs",
    "耶利米·巴罗夫": "Jeremiah Burroughs",
    "约翰·福克斯": "John Foxe",
    "迈克·麦金利": "Mike McKinley",
}

USER_AGENT = "christian-books-guide/1.0 (+https://github.com/yanyue404/christian-books)"
SKIP_HINTS = ("电影", "电视剧", "動畫", "动画", "film", "TV series", "album", "消歧")
COMMENTARY = ("注释", "解经", "释经", "讲章")
SKIP_TITLES = {"希伯来书注释", "摩根解经丛卷·希伯来书", "圣灵论（繁体）"}

PREFERRED_SITES = (
    "ivpress.com",
    "crossway.org",
    "ccel.org",
    "desiringgod.org",
    "ustiendao.com",
    "afcbook.org",
    "gutenberg.org",
    "archive.org",
    "wikisource.org",
    "ligonier.org",
    "thegospelcoalition.org",
    "christianbook.com",
    "wikipedia.org",
    "wellsofgrace.com",
    "gaigezong.com",
    "ccbiblestudy.org",
)

SYSTEM_PROMPT = """
你是基督教书籍导读编辑。只根据用户提供的互联网资料包写中文导读。

规则：
1. 只能用资料包里的事实。没有的年份、译本、章题写「资料未提供」，禁止编造。
2. 情节介绍不是原书目录。只有资料明确列出原书章节、书信编号或卷册时，才能写成目录。
3. 原著不分章（如《天路历程》连续叙事、《魔鬼家书》书信无原题）必须说明，不得伪造章名。
4. 简介 150–280 字，说明作者、成书背景、主题。语气克制。
5. 「依据」列出资料包中实际用到的链接（维基、Google Books、Open Library、Internet Archive、出版社书页等均可）。
6. 按下面结构输出 Markdown，不要代码围栏：

# 《中文书名》

- **作者**：中文名 (英文名, 生年–卒年)
- **原书**：*English Title*（年份）
- **文件**：仅当资料里有仓库文件名时才写

## 简介

## 目录

（先说明目录依据；没有原书目录就如实说明。）

## 依据
"""

# ========================== 网络 ==========================


def http_json(url: str, params: dict | None = None, body: bytes | None = None, headers: dict | None = None) -> dict:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})},
        method="POST" if body else "GET",
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code != 429 or attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise last_error  # type: ignore[misc]


def http_text(url: str, params: dict | None = None) -> str:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/json"})
    with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace")


def html_to_text(html: str, limit: int = 4500) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</(p|div|h[1-6]|li|tr)>", "\n", html)
    text = unescape(re.sub(r"(?is)<[^>]+>", " ", html))
    text = re.sub(r"[ \t]+\n", "\n", re.sub(r"[ \t]{2,}", " ", text))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:limit] + ("\n\n[……后文已截断]" if len(text) > limit else "")


def try_source(label: str, fn) -> str:
    try:
        return fn()
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        print(f"{label} 跳过：{exc}", file=sys.stderr)
        return f"### {label}\n未能读取（{exc}）\n"


def wiki_search(lang: str, query: str, must: tuple[str, ...] = ()) -> str | None:
    data = http_json(
        f"https://{lang}.wikipedia.org/w/api.php",
        {"action": "query", "list": "search", "srsearch": query, "srlimit": "8", "format": "json"},
    )
    hits = [str(h.get("title") or "") for h in data.get("query", {}).get("search", [])]
    hits = [t for t in hits if t and not any(s.lower() in t.lower() for s in SKIP_HINTS)]
    if not hits:
        return None
    folded = query.strip().lower()
    for title in hits:
        if title.lower() == folded:
            return title
    keys = [k.lower() for k in must if k]
    if keys:
        for title in hits:
            blob = title.lower()
            if any(k in blob for k in keys):
                return title
    return hits[0]


def wiki_extract(lang: str, title: str) -> tuple[str, str, str] | None:
    """返回 (条目标题, url, 纯文本)，取不到则 None。"""
    data = http_json(
        f"https://{lang}.wikipedia.org/w/api.php",
        {
            "action": "query",
            "prop": "extracts|info",
            "explaintext": "1",
            "exintro": "0",
            "inprop": "url",
            "titles": title,
            "redirects": "1",
            "format": "json",
        },
    )
    page = next(iter(data.get("query", {}).get("pages", {}).values()), None)
    if not page or page.get("missing") is not None:
        return None
    text = str(page.get("extract") or "").strip()
    if not text:
        return None
    if len(text) > 6000:
        text = text[:6000] + "\n\n[……后文已截断]"
    return str(page.get("title") or title), str(page.get("fullurl") or ""), text


def page_mentions(page: tuple[str, str, str], *needles: str) -> bool:
    name, _, text = page
    hay = f"{name}\n{text[:1200]}".lower()
    return any(n and n.lower() in hay for n in needles)


def fetch_page(
    lang: str,
    *queries: str,
    must: tuple[str, ...] = (),
    title_must: tuple[str, ...] = (),
) -> tuple[str, str, str] | None:
    for query in queries:
        query = (query or "").strip()
        if not query:
            continue
        try:
            page = wiki_extract(lang, query)
            if not page:
                found = wiki_search(lang, query, must=title_must or must)
                page = wiki_extract(lang, found) if found else None
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"维基请求失败（{lang} {query}）：{exc}", file=sys.stderr)
            time.sleep(1)
            continue
        time.sleep(0.4)
        if not page:
            continue
        if title_must and not any(k and k.lower() in page[0].lower() for k in title_must):
            continue
        if must and not page_mentions(page, *must):
            continue
        return page
    return None


def collect_wikipedia(title: str, author: str, en_title: str, author_en: str) -> str:
    parts: list[str] = []
    book_en = fetch_page("en", en_title or title, title_must=(title, en_title))
    author_zh = fetch_page("zh", author, must=(author, author_en))
    author_en_page = fetch_page("en", author_en, must=(author, author_en))
    for label, page in (
        ("维基：书（英文）", book_en),
        ("维基：作者（中文）", author_zh),
        ("维基：作者（英文）", author_en_page),
    ):
        if not page:
            parts.append(f"### {label}\n未找到")
            continue
        name, url, text = page
        parts.append(f"### {label}\n标题：{name}\nURL：{url}\n\n{text}")
    return "\n\n".join(parts)


def collect_google_books(title: str, author: str, en_title: str, author_en: str) -> str:
    query = f'intitle:"{en_title or title}" inauthor:"{author_en or author}"'
    data = http_json(
        "https://www.googleapis.com/books/v1/volumes",
        {"q": query, "maxResults": "3"},
    )
    items = data.get("items") or []
    if not items:
        return "### Google Books\n未找到"
    blocks = ["### Google Books"]
    for item in items[:2]:
        info = item.get("volumeInfo") or {}
        toc = info.get("tableOfContents") or ""
        blocks.append(
            "\n".join(
                [
                    f"标题：{info.get('title') or '无'}",
                    f"作者：{', '.join(info.get('authors') or []) or '无'}",
                    f"出版：{info.get('publishedDate') or '无'} / {info.get('publisher') or '无'}",
                    f"URL：{info.get('infoLink') or info.get('canonicalVolumeLink') or '无'}",
                    f"简介：{(info.get('description') or '无')[:1800]}",
                    f"目录：{toc or '无'}",
                ]
            )
        )
    return "\n\n".join(blocks)


def collect_openlibrary(title: str, author_en: str, en_title: str) -> str:
    data = http_json(
        "https://openlibrary.org/search.json",
        {"title": en_title or title, "author": author_en, "limit": "3"},
    )
    docs = data.get("docs") or []
    if not docs:
        return "### Open Library\n未找到"
    doc = docs[0]
    key = doc.get("key") or ""
    url = f"https://openlibrary.org{key}" if key else "https://openlibrary.org"
    extra = ""
    if key:
        work = http_json(f"https://openlibrary.org{key}.json")
        desc = work.get("description")
        if isinstance(desc, dict):
            desc = desc.get("value")
        extra = str(desc or "")[:1800]
    return (
        "### Open Library\n"
        f"标题：{doc.get('title')}\n"
        f"作者：{', '.join(doc.get('author_name') or [])}\n"
        f"首版：{doc.get('first_publish_year') or '无'}\n"
        f"URL：{url}\n"
        f"简介：{extra or '无'}"
    )


def collect_archive(en_title: str, author_en: str) -> str:
    if not en_title:
        return "### Internet Archive\n未检索（无英文书名）"
    data = http_json(
        "https://archive.org/advancedsearch.php",
        {
            "q": f'title:("{en_title}") AND creator:({author_en})',
            "output": "json",
            "rows": "5",
        },
    )
    docs = (data.get("response") or {}).get("docs") or []
    needle = en_title.lower()
    exact = [d for d in docs if str(d.get("title") or "").strip().lower() == needle]
    matched = exact or [d for d in docs if str(d.get("title") or "").strip().lower().startswith(needle)]
    if not matched:
        return "### Internet Archive\n未找到同名条目"
    doc = matched[0]
    ident = doc.get("identifier") or ""
    desc = doc.get("description")
    if isinstance(desc, list):
        desc = " ".join(str(x) for x in desc)
    return (
        "### Internet Archive\n"
        f"标题：{doc.get('title')}\n"
        f"作者：{doc.get('creator')}\n"
        f"年份：{doc.get('year') or '无'}\n"
        f"URL：https://archive.org/details/{ident}\n"
        f"简介：{str(desc or '无')[:1800]}"
    )


def _unwrap_ddg(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    uddg = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg")
    return uddg[0] if uddg else href


def web_search(query: str, limit: int = 8) -> list[tuple[str, str]]:
    html = http_text("https://lite.duckduckgo.com/lite/", {"q": query})
    hits: list[tuple[str, str]] = []
    seen: set[str] = set()
    for href, title in re.findall(
        r'<a[^>]+href="([^"]+)"[^>]*class=[\'"]result-link[\'"][^>]*>(.*?)</a>',
        html,
        flags=re.I | re.S,
    ):
        href = _unwrap_ddg(unescape(href))
        if "duckduckgo.com" in href or href in seen:
            continue
        title = unescape(re.sub(r"<[^>]+>", "", title)).strip()
        if not title:
            continue
        seen.add(href)
        hits.append((href, title))
        if len(hits) >= limit:
            break
    return hits


def collect_web_pages(title: str, author: str, en_title: str, author_en: str) -> str:
    queries = [f"{title} {author} 目录"]
    if en_title:
        queries.append(f"{en_title} {author_en} table of contents")
    hits: list[tuple[str, str]] = []
    for query in queries:
        hits.extend(web_search(query))
        time.sleep(0.3)

    unique: list[tuple[str, str]] = []
    seen: set[str] = set()
    for url, name in hits:
        if url in seen:
            continue
        seen.add(url)
        unique.append((url, name))

    lines = ["### 网页检索"]
    if unique:
        lines.append("检索到的页面：")
        lines.extend(f"- {name} | {url}" for url, name in unique[:8])
    else:
        lines.append("未检索到页面")

    preferred = [
        (url, name)
        for url, name in unique
        if any(site in url for site in PREFERRED_SITES) and not url.lower().endswith(".pdf")
    ]
    to_fetch = preferred[:3] or [(u, n) for u, n in unique if not u.lower().endswith(".pdf")][:1]
    for url, name in to_fetch:
        try:
            text = html_to_text(http_text(url))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            lines.append(f"\n抓取失败：{name} | {url}（{exc}）")
            continue
        lines.append(f"\n#### 页面正文：{name}\nURL：{url}\n\n{text}")
        time.sleep(0.4)
    return "\n".join(lines)


def collect_sources(title: str, author: str, en_title: str, filename: str) -> str:
    en_title = en_title or KNOWN_EN_TITLES.get(title, "")
    author_en = KNOWN_AUTHORS_EN.get(author, author)
    blocks = [
        f"中文书名：{title}",
        f"作者：{author}",
        f"英文原名：{en_title or '无'}",
        f"仓库文件名：{filename or '无'}",
        "资料来源不限维基，以下为实际拉取到的公开网页 / 书目库。",
    ]
    blocks.append(try_source("网页检索", lambda: collect_web_pages(title, author, en_title, author_en)))
    blocks.append(try_source("Internet Archive", lambda: collect_archive(en_title, author_en)))
    blocks.append(try_source("Google Books", lambda: collect_google_books(title, author, en_title, author_en)))
    blocks.append(try_source("Open Library", lambda: collect_openlibrary(title, author_en, en_title)))
    blocks.append(try_source("维基百科", lambda: collect_wikipedia(title, author, en_title, author_en)))
    return "\n\n".join(blocks)


def fallback_guide(title: str, author: str, en_title: str, filename: str, sources: str) -> str:
    file_line = f"\n- **文件**：[{filename}](../{urllib.parse.quote(filename)})" if filename else ""
    return (
        f"# 《{title}》\n\n"
        f"- **作者**：{author}\n"
        f"- **原书**：*{en_title or KNOWN_EN_TITLES.get(title) or '待核'}*"
        f"{file_line}\n\n"
        "## 简介\n\n互联网资料如下，未经 AI 整理。设好 OPENAI_API_KEY 后重跑即可。\n\n"
        f"{sources}\n"
    )


# ========================== AI ==========================


def call_llm(sources: str) -> str:
    if not API_KEY:
        raise RuntimeError("未设置 OPENAI_API_KEY")
    payload = json.dumps(
        {
            "model": API_MODEL,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT.strip()},
                {"role": "user", "content": "请根据下列互联网资料撰写导读。\n\n" + sources},
            ],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    data = http_json(
        f"{API_BASE}/chat/completions",
        body=payload,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
    if not content:
        raise RuntimeError(f"模型无返回：{data}")
    return content.strip() + "\n"


def guide_name(title: str) -> str:
    short = title.split("：", 1)[0]
    return re.sub(r'[\\/:*?"<>|]', "", short).strip() + ".md"


def generate(title: str, author: str, en_title: str = "", filename: str = "", use_ai: bool = True) -> str:
    sources = collect_sources(title, author, en_title, filename)
    if use_ai and API_KEY:
        try:
            return call_llm(sources)
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            print(f"AI 失败，回退资料草稿：{exc}", file=sys.stderr)
    return fallback_guide(title, author, en_title, filename, sources)


# ========================== 命令行 ==========================


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="用公开互联网资料生成书籍简介与目录。")
    parser.add_argument("--title", help="中文书名，不要带书名号")
    parser.add_argument("--author", help="作者")
    parser.add_argument("--en-title", default="", help="英文原名")
    parser.add_argument("--from-repo", action="store_true", help="扫描仓库电子书")
    parser.add_argument("--write", action="store_true", help="写入 guides/<书名>.md")
    parser.add_argument("--force", action="store_true", help="覆盖已有导读")
    parser.add_argument("--no-ai", action="store_true", help="只拉资料，不调用模型")
    args = parser.parse_args()

    root = repo_root()
    if args.from_repo:
        jobs = [
            (b.title, b.author, "", b.filename)
            for b in discover_books(root)
            if b.title not in SKIP_TITLES and not any(m in b.title for m in COMMENTARY)
        ]
    elif args.title and args.author:
        jobs = [(args.title, args.author, args.en_title, "")]
    else:
        print("请提供 --title 与 --author，或使用 --from-repo。", file=sys.stderr)
        return 1

    if not jobs:
        print("没有可处理的书。", file=sys.stderr)
        return 1

    for title, author, en_title, filename in jobs:
        print(f"# {title} — {author}", file=sys.stderr)
        markdown = generate(title, author, en_title=en_title, filename=filename, use_ai=not args.no_ai)
        if not args.write:
            print(markdown)
            continue
        dest = root / "guides" / guide_name(title)
        if dest.exists() and not args.force:
            print(f"已存在，跳过 {dest}（覆盖请加 --force）", file=sys.stderr)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(markdown if markdown.endswith("\n") else markdown + "\n", encoding="utf-8")
        print(f"已写入 {dest}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
