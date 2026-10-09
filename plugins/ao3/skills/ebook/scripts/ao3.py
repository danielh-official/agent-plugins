#!/usr/bin/env python3
"""Fetch an AO3 work once, list its chapters, and pick chapters for a book.

  python3 ao3.py fetch WORK_URL            download (or reuse cache), parse, list
  python3 ao3.py parse PAGE.html --url U   parse a saved work page instead
  python3 ao3.py pick WORK.json "1-3, 7" --out BOOK.json

Fetching is polite by construction: one request per work (the full-work
page), at least 5 seconds between requests, an honest User-Agent, a cache
so re-picking chapters never refetches, and at most one retry after a 429.
"""

import argparse
import json
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from epub import chapter_label
from html_clean import parse as parse_html
from html_clean import sanitize, word_count

USER_AGENT = (
    "ao3-ebook/0.0.1 (+https://github.com/danielh-official/agent-plugins; "
    "personal offline reading)"
)
MIN_INTERVAL = 5.0
MAX_RETRY_WAIT = 120
CACHE_TTL = 6 * 3600
WORK_URL = re.compile(
    r"(?:archiveofourown\.org|ao3\.org)/(?:collections/[^/]+/)?works/(\d+)"
)
TAG_FIELDS = (
    ("rating", "Rating"),
    ("warning", "Archive Warnings"),
    ("category", "Categories"),
    ("fandom", "Fandoms"),
    ("relationship", "Relationships"),
    ("character", "Characters"),
    ("freeform", "Additional Tags"),
)


class Locked(Exception):
    pass


def work_id(value):
    value = value.strip()
    if value.isdigit():
        return value
    match = WORK_URL.search(value)
    if not match:
        raise ValueError(f"not an AO3 work URL: {value}")
    return match.group(1)


def cache_dir():
    path = Path(tempfile.gettempdir()) / "ao3-ebook"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _throttle(directory):
    stamp = directory / "last-request"
    if stamp.exists():
        wait = MIN_INTERVAL - (time.time() - stamp.stat().st_mtime)
        if wait > 0:
            time.sleep(wait)
    stamp.touch()


def download(wid, directory):
    url = f"https://archiveofourown.org/works/{wid}?view_full_work=true&view_adult=true"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in (1, 2):
        _throttle(directory)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                final = response.geturl()
                body = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise ValueError(f"work {wid} not found (deleted or never existed)")
            if exc.code in (429, 503) and attempt == 1:
                retry = exc.headers.get("Retry-After", "")
                wait = int(retry) if retry.isdigit() else 60
                if wait > MAX_RETRY_WAIT:
                    raise ValueError(
                        f"AO3 asked to wait {wait}s before retrying; try again later"
                    )
                print(f"AO3 is rate limiting; waiting {wait}s once", file=sys.stderr)
                time.sleep(wait)
                continue
            raise ValueError(f"AO3 returned HTTP {exc.code}; try again later")
        if "/users/login" in final:
            raise Locked(wid)
        return body
    raise ValueError("AO3 is still rate limiting; try again later")


def _tags(meta, cls):
    dd = meta.find("dd", cls) if meta else None
    if not dd:
        return []
    return [a.text().strip() for a in dd.find_all("a", "tag") if a.text().strip()]


def _blockquote(node):
    quote = node.find("blockquote", "userstuff") if node else None
    return sanitize(quote).strip() if quote else ""


def _body(node):
    for landmark in list(node.find_all("h3", "landmark")):
        landmark.parent.children.remove(landmark)
    return sanitize(node).strip(), word_count(node)


def parse_work(markup, url):
    root = parse_html(markup)
    chapters_node = root.find(id="chapters")
    if chapters_node is None:
        text = root.text()
        if "registered users" in text or root.find("form", id="new_user_session"):
            raise Locked(url)
        if "adult content" in text:
            raise ValueError("AO3 showed its adult-content warning instead of the work")
        raise ValueError("could not find the work's text on the page")

    meta = root.find("dl", ("work", "meta"))
    preface = root.find("div", ("preface", "group"))
    title_node = preface.find("h2", "title") if preface else None
    title = title_node.text().strip() if title_node else "Untitled"
    byline = preface.find("h3", "byline") if preface else None
    authors = []
    if byline:
        authors = [a.text().strip() for a in byline.find_all("a", rel="author")]
        authors = authors or [" ".join(byline.text().split())]
    summary = preface.find("div", ("summary", "module")) if preface else None
    notes = preface.find("div", ("notes", "module")) if preface else None
    language = meta.find("dd", "language") if meta else None
    count = meta.find("dd", "chapters") if meta else None

    chapters = []
    blocks = [
        c
        for c in chapters_node.children
        if not isinstance(c, str)
        and "chapter" in c.classes
        and (c.attrs.get("id") or "").startswith("chapter-")
    ]
    for block in blocks:
        number = int(block.attrs["id"].split("-", 1)[1])
        prefaces = list(block.find_all("div", ("chapter", "preface")))
        head = prefaces[0] if prefaces else None
        heading = head.find("h3", "title") if head else None
        name = " ".join(heading.text().split()) if heading else f"Chapter {number}"
        before = ""
        if head:
            before = _blockquote(head.find("div", ("summary", "module")))
            for n in head.find_all("div", ("notes", "module")):
                if "end" not in n.classes:
                    before += _blockquote(n)
        after = ""
        for p in prefaces:
            end = p.find("div", ("end", "notes"))
            if end:
                after = _blockquote(end)
        body = block.find("div", ("userstuff", "module"))
        html, words = _body(body) if body else ("", 0)
        chapters.append(
            {
                "number": number,
                "title": name,
                "html": html,
                "words": words,
                "notes_before_html": before,
                "notes_after_html": after,
            }
        )
    if not chapters:
        # One-shot: the text sits directly in #chapters.
        body = chapters_node.find("div", "userstuff") or chapters_node
        html, words = _body(body)
        chapters.append({"number": 1, "title": title, "html": html, "words": words})

    endnotes = root.find(id="work_endnotes")
    if endnotes:
        last = chapters[-1]
        last["notes_after_html"] = last.get("notes_after_html", "") + _blockquote(
            endnotes
        )

    return {
        "source": "ao3",
        "work_id": work_id(url) if WORK_URL.search(url) else None,
        "url": url,
        "title": title,
        "authors": authors,
        "summary_html": _blockquote(summary),
        "summary_text": " ".join(summary.find("blockquote").text().split())
        if summary and summary.find("blockquote")
        else "",
        "notes_html": _blockquote(notes),
        "language": language.text().strip() if language else "",
        "chapter_count": count.text().strip() if count else str(len(chapters)),
        "tags": [[label, _tags(meta, cls)] for cls, label in TAG_FIELDS],
        "chapters": chapters,
    }


def listing(work, path):
    total = sum(c["words"] for c in work["chapters"])
    rating = dict(work["tags"]).get("Rating") or ["unrated"]
    print(f"{work['title']} by {', '.join(work['authors']) or 'unknown'}")
    print(
        f"{rating[0]} · chapters {work['chapter_count']} · {total:,} words · {work['url']}"
    )
    print("   #    words  title")
    for c in work["chapters"]:
        print(f"{c['number']:>4}  {c['words']:>7,}  {c['title']}")
    print(f"work json: {path}")


def select(numbers, spec):
    """Resolve '1-3, 7', 'all', 'latest 2', 'first 5' against chapter numbers."""
    available = sorted(numbers)
    chosen = []
    for raw in re.split(r"[,;]|\band\b", spec.lower()):
        item = raw.strip().removeprefix("chapters").removeprefix("chapter").strip()
        if not item:
            continue
        if item == "all":
            chosen += available
            continue
        match = re.fullmatch(r"(latest|last|first)\s+(\d+)", item)
        if match:
            n = int(match.group(2))
            if n < 1:
                raise ValueError(f"'{item}' selects nothing")
            chosen += available[-n:] if match.group(1) != "first" else available[:n]
            continue
        match = re.fullmatch(r"(\d+)\s*(?:-|–|to|through)\s*(\d+)", item)
        if match:
            lo, hi = sorted(int(x) for x in match.groups())
            chosen += list(range(lo, hi + 1))
            continue
        if item.isdigit():
            chosen.append(int(item))
            continue
        raise ValueError(f"can't read '{raw.strip()}' as chapters")
    missing = sorted(set(chosen) - set(available))
    if missing:
        raise ValueError(
            f"chapter(s) {', '.join(map(str, missing))} don't exist; "
            f"this work has {available[0]}-{available[-1]}"
        )
    picked = sorted(set(chosen))
    if not picked:
        raise ValueError("no chapters selected")
    return picked


def pick(work, spec):
    numbers = [c["number"] for c in work["chapters"]]
    picked = select(numbers, spec)
    book = dict(work)
    book["chapters"] = [c for c in work["chapters"] if c["number"] in picked]
    if picked != sorted(numbers):
        book["label"] = chapter_label(picked)
    return book


def save(work, directory):
    name = f"work-{work['work_id'] or 'page'}.json"
    path = directory / name
    path.write_text(json.dumps(work, ensure_ascii=False), encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("url")
    f.add_argument("--refresh", action="store_true", help="ignore the cache")
    p = sub.add_parser("parse")
    p.add_argument("page", type=Path)
    p.add_argument("--url", default="")
    k = sub.add_parser("pick")
    k.add_argument("work", type=Path)
    k.add_argument("spec")
    k.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        directory = cache_dir()
        if args.command == "pick":
            work = json.loads(args.work.read_text(encoding="utf-8"))
            book = pick(work, args.spec)
            args.out.write_text(json.dumps(book, ensure_ascii=False), encoding="utf-8")
            total = sum(c["words"] for c in book["chapters"])
            for c in book["chapters"]:
                print(f"{c['number']:>4}  {c['words']:>7,}  {c['title']}")
            print(f"{len(book['chapters'])} chapter(s), {total:,} words -> {args.out}")
            return 0
        if args.command == "parse":
            markup = args.page.read_text(encoding="utf-8")
            work = parse_work(markup, args.url)
        else:
            wid = work_id(args.url)
            url = f"https://archiveofourown.org/works/{wid}"
            cached = directory / f"work-{wid}.html"
            fresh = cached.exists() and time.time() - cached.stat().st_mtime < CACHE_TTL
            if fresh and not args.refresh:
                markup = cached.read_text(encoding="utf-8")
            else:
                markup = download(wid, directory)
                cached.write_text(markup, encoding="utf-8")
            work = parse_work(markup, url)
        listing(work, save(work, directory))
        return 0
    except Locked:
        print(
            "locked: this work is only available to registered AO3 users; skipping it",
            file=sys.stderr,
        )
        return 4
    except urllib.error.URLError as exc:
        print(
            f"network: can't reach AO3 from here ({exc.reason}). "
            "Paste the chapter text instead.",
            file=sys.stderr,
        )
        return 3
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
