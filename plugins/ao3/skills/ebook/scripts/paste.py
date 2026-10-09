#!/usr/bin/env python3
"""Turn pasted chapter text into a book JSON for epub.py. Nothing is fetched.

Usage: python3 paste.py TEXT_FILE [TEXT_FILE ...] --title T --author A
           [--url URL] [--chapter-title T] [--start N] --out BOOK.json

Each file may hold one chapter or several; a line on its own such as
"Chapter 3" or "Chapter 3: The Lake" starts a new chapter. Files are read in
the order given. A numbered heading sets that chapter's number; otherwise
chapters count up from --start (default 1).
"""

import argparse
import json
import re
import sys
from pathlib import Path

from epub import chapter_label
from html_clean import esc

HEADING = re.compile(
    r"^\s*(?:chapter|ch\.)\s+(\d+|[ivxlcdm]+)\b\s*(?:[:.\-–—]\s*(.*))?$",
    re.IGNORECASE,
)
SCENE_BREAK = re.compile(r"^\s*(?:[*~=\-_#•·+—–]\s*){3,}$")
# Labels AO3 prints around chapter text when a page is copied.
NOISE = {"chapter text", "notes:", "summary:"}


def paragraphs(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    lines = [line.rstrip() for line in text.split("\n")]
    lines = [line for line in lines if line.strip().lower() not in NOISE]
    if any(not line.strip() for line in lines):
        blocks, current = [], []
        for line in lines:
            if line.strip():
                current.append(line.strip())
            elif current:
                blocks.append(current)
                current = []
        if current:
            blocks.append(current)
    else:
        blocks = [[line.strip()] for line in lines if line.strip()]
    out = []
    for block in blocks:
        if len(block) == 1 and SCENE_BREAK.match(block[0]):
            out.append("<hr/>")
        else:
            out.append("<p>" + "<br/>".join(esc(line) for line in block) + "</p>")
    return "\n".join(out)


def split_chapters(text):
    """Return [(heading or None, body)] split on chapter heading lines."""
    pieces, heading, body = [], None, []
    for line in text.replace("\r\n", "\n").split("\n"):
        if HEADING.match(line) and len(line) < 150:
            if heading is not None or "".join(body).strip():
                pieces.append((heading, "\n".join(body)))
            heading, body = line.strip(), []
        else:
            body.append(line)
    pieces.append((heading, "\n".join(body)))
    # Text before the first heading belongs to that first chapter.
    if len(pieces) > 1 and pieces[0][0] is None:
        lead = pieces.pop(0)[1]
        pieces[0] = (pieces[0][0], lead + "\n\n" + pieces[0][1])
    return pieces


def build_book(texts, title, authors, url=None, chapter_title=None, start=None):
    chapters, number, numbered = [], start or 1, bool(start)
    for text in texts:
        for heading, body in split_chapters(text):
            if not body.strip():
                continue
            words = sum(1 for t in body.split() if any(ch.isalnum() for ch in t))
            match = HEADING.match(heading or "")
            if match and match.group(1).isdigit():
                number = int(match.group(1))
                numbered = True
            if heading:
                name = heading
            elif chapter_title and not chapters:
                name = chapter_title
            else:
                name = f"Chapter {number}"
            chapters.append(
                {
                    "number": number,
                    "title": name,
                    "html": paragraphs(body),
                    "words": words,
                }
            )
            number += 1
    if not chapters:
        raise ValueError("no text found in the pasted input")
    book = {
        "source": "paste",
        "title": title,
        "authors": authors,
        "url": url,
        "language": "en",
        "tags": [],
        "chapters": chapters,
    }
    if numbered:
        book["label"] = chapter_label([c["number"] for c in chapters])
    return book


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--author", action="append", default=[], dest="authors")
    parser.add_argument("--url")
    parser.add_argument("--chapter-title")
    parser.add_argument("--start", type=int)
    parser.add_argument("--language", default="en")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    texts = [f.read_text(encoding="utf-8") for f in args.files]
    try:
        book = build_book(
            texts, args.title, args.authors, args.url, args.chapter_title, args.start
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    book["language"] = args.language
    args.out.write_text(json.dumps(book, ensure_ascii=False), encoding="utf-8")
    total = sum(c["words"] for c in book["chapters"])
    for c in book["chapters"]:
        print(f"{c['number']:>4}  {c['words']:>7,}  {c['title']}")
    print(f"{len(book['chapters'])} chapter(s), {total:,} words -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
