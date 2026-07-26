#!/usr/bin/env python3
"""
扫描本仓库中的基督教电子书，并按 README 命名规范输出清单。

命名规范：《书名》- 作者.pdf / .epub

# 用法:
    
# 1. 纯文本列表（默认）
python scripts/list_books.py

# 2. Markdown 表格（可用于更新 README）
python scripts/list_books.py --format markdown

# 3. JSON（便于其他工具读取）
python scripts/list_books.py --format json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

BOOK_EXTENSIONS = {".pdf", ".epub"}
# 《书名》- 作者.ext
BOOK_NAME_PATTERN = re.compile(r"^《(?P<title>.+?)》- (?P<author>.+)\.(?P<ext>pdf|epub)$", re.IGNORECASE)


@dataclass(frozen=True)
class Book:
    """仓库中的一本电子书。"""

    title: str
    author: str
    format: str
    filename: str

    @property
    def markdown_link(self) -> str:
        return f"[{self.filename}]({self.filename})"


def repo_root() -> Path:
    """返回仓库根目录（scripts/ 的上一级）。"""
    return Path(__file__).resolve().parent.parent


def parse_book(path: Path) -> Book | None:
    match = BOOK_NAME_PATTERN.match(path.name)
    if not match:
        return None
    return Book(
        title=match.group("title"),
        author=match.group("author"),
        format=match.group("ext").upper(),
        filename=path.name,
    )


def discover_books(root: Path) -> list[Book]:
    books: list[Book] = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in BOOK_EXTENSIONS:
            continue
        book = parse_book(path)
        if book:
            books.append(book)
    return books


def format_text(books: list[Book]) -> str:
    if not books:
        return "未找到符合命名规范的电子书。"
    lines = [f"共收录 {len(books)} 本电子书：", ""]
    for index, book in enumerate(books, start=1):
        lines.append(f"{index:>2}. [{book.format}] {book.title} — {book.author}")
    return "\n".join(lines)


def format_markdown(books: list[Book]) -> str:
    if not books:
        return "| # | 书名 | 作者 | 格式 | 文件 |\n|---|------|------|------|------|"
    rows = [
        "| # | 书名 | 作者 | 格式 | 文件 |",
        "|---|------|------|------|------|",
    ]
    for index, book in enumerate(books, start=1):
        rows.append(
            f"| {index} | {book.title} | {book.author} | {book.format} | {book.markdown_link} |"
        )
    return "\n".join(rows)


def format_json(books: list[Book]) -> str:
    payload = {
        "count": len(books),
        "books": [asdict(book) for book in books],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="列出 christian-books 仓库中的电子书清单。",
    )
    parser.add_argument(
        "--format",
        choices=("text", "markdown", "json"),
        default="text",
        help="输出格式（默认: text）",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="指定扫描目录，默认为仓库根目录",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve() if args.root else repo_root()

    if not root.is_dir():
        print(f"错误：目录不存在 — {root}", file=sys.stderr)
        return 1

    books = discover_books(root)
    formatters = {
        "text": format_text,
        "markdown": format_markdown,
        "json": format_json,
    }
    print(formatters[args.format](books))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
