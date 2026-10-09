#!/usr/bin/env python3
"""Build an EPUB 3 file from a book JSON (written by ao3.py pick or paste.py).

Usage: python3 epub.py BOOK.json --out-dir DIR [--no-notes]
Prints the path of the EPUB it wrote.
"""

import argparse
import json
import re
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from html_clean import attr, esc

CSS = """body { margin: 0 4%; line-height: 1.5; }
p { margin: 0 0 0.8em; }
h1, h2 { line-height: 1.25; }
hr { border: 0; border-top: 1px solid #888; width: 30%; margin: 1.5em auto; }
blockquote { margin: 1em 1.5em; }
.byline { font-style: italic; }
.source { font-size: 0.9em; }
.notes { font-size: 0.9em; margin: 1em 0; padding-left: 0.8em; border-left: 2px solid #999; }
.notes-heading { font-weight: bold; margin-bottom: 0.4em; }
dl.tags dt { font-weight: bold; margin-top: 0.4em; }
dl.tags dd { margin-left: 1em; }
.align-left { text-align: left; }
.align-right { text-align: right; }
.align-center { text-align: center; }
.align-justify { text-align: justify; }
"""

LANGUAGES = {
    "english": "en",
    "español": "es",
    "français": "fr",
    "deutsch": "de",
    "italiano": "it",
    "português brasileiro": "pt-BR",
    "português europeu": "pt-PT",
    "русский": "ru",
    "中文-普通话 國語": "zh",
    "日本語": "ja",
    "한국어": "ko",
    "polski": "pl",
    "nederlands": "nl",
    "svenska": "sv",
    "türkçe": "tr",
}


def language_code(name):
    name = (name or "").strip()
    if re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]+)*", name):
        return name
    return LANGUAGES.get(name.lower(), "und")


def page(title, body, lang):
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" '
        f'lang="{lang}" xml:lang="{lang}">\n'
        f'<head><meta charset="utf-8"/><title>{esc(title)}</title>'
        '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
        f"<body>\n{body}\n</body>\n</html>\n"
    )


def notes_block(heading, markup):
    if not markup or not markup.strip():
        return ""
    return (
        f'<div class="notes"><p class="notes-heading">{esc(heading)}</p>{markup}</div>'
    )


def title_page(book, include_notes):
    parts = [f"<h1>{esc(book['title'])}</h1>"]
    if book.get("authors"):
        parts.append(f'<p class="byline">by {esc(", ".join(book["authors"]))}</p>')
    if book.get("url"):
        url = book["url"]
        parts.append(f'<p class="source"><a href="{attr(url)}">{esc(url)}</a></p>')
    tags = [(label, values) for label, values in book.get("tags", []) if values]
    if tags:
        parts.append('<dl class="tags">')
        for label, values in tags:
            parts.append(f"<dt>{esc(label)}</dt><dd>{esc(', '.join(values))}</dd>")
        parts.append("</dl>")
    if book.get("summary_html"):
        parts.append(f"<h2>Summary</h2>{book['summary_html']}")
    if include_notes and book.get("notes_html"):
        parts.append(f"<h2>Notes</h2>{book['notes_html']}")
    return "\n".join(parts)


def chapter_page(chapter, include_notes):
    parts = [f"<h2>{esc(chapter['title'])}</h2>"]
    if include_notes:
        parts.append(notes_block("Notes", chapter.get("notes_before_html")))
    parts.append(chapter["html"])
    if include_notes:
        parts.append(notes_block("End notes", chapter.get("notes_after_html")))
    return "\n".join(p for p in parts if p)


def chapter_label(numbers):
    """[1, 2, 3, 7] -> 'ch 1-3, 7'."""
    numbers = sorted(set(numbers))
    runs, start = [], None
    for i, n in enumerate(numbers):
        if start is None:
            start = n
        if i + 1 == len(numbers) or numbers[i + 1] != n + 1:
            runs.append(str(start) if start == n else f"{start}-{n}")
            start = None
    return "ch " + ", ".join(runs)


def display_title(book):
    label = book.get("label")
    return f"{book['title']} ({label})" if label else book["title"]


def file_name(book):
    name = display_title(book)
    if book.get("authors"):
        name = f"{name} - {', '.join(book['authors'])}"
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", name).strip(" .")
    return (name[:150].rstrip(" .") or "book") + ".epub"


def book_id(book):
    key = json.dumps(
        [
            book.get("url") or book["title"],
            book.get("authors"),
            [c["number"] for c in book["chapters"]],
        ]
    )
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, key)}"


def build(book, out_dir, include_notes=True, modified=None):
    if not book.get("chapters"):
        raise ValueError("book has no chapters")
    lang = language_code(book.get("language"))
    title = display_title(book)
    ident = book_id(book)
    modified = modified or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    pages = [("title.xhtml", title, title_page(book, include_notes))]
    for i, chapter in enumerate(book["chapters"], 1):
        pages.append(
            (f"ch{i:03d}.xhtml", chapter["title"], chapter_page(chapter, include_notes))
        )

    meta = [
        f'<dc:identifier id="bookid">{esc(ident)}</dc:identifier>',
        f"<dc:title>{esc(title)}</dc:title>",
        f"<dc:language>{lang}</dc:language>",
    ]
    meta += [f"<dc:creator>{esc(a)}</dc:creator>" for a in book.get("authors", [])]
    if book.get("url"):
        meta.append(f"<dc:source>{esc(book['url'])}</dc:source>")
    if book.get("summary_text"):
        meta.append(f"<dc:description>{esc(book['summary_text'])}</dc:description>")
    for label, values in book.get("tags", []):
        if label in ("Fandom", "Fandoms", "Relationships", "Additional Tags"):
            meta += [f"<dc:subject>{esc(v)}</dc:subject>" for v in values]
    if book.get("source") == "ao3":
        meta.append("<dc:publisher>Archive of Our Own</dc:publisher>")
    meta.append(f'<meta property="dcterms:modified">{modified}</meta>')

    manifest = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '<item id="css" href="style.css" media-type="text/css"/>',
    ]
    spine = []
    for name, _, _ in pages:
        item = name.removesuffix(".xhtml")
        manifest.append(
            f'<item id="{item}" href="{name}" media-type="application/xhtml+xml"/>'
        )
        spine.append(f'<itemref idref="{item}"/>')

    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        f'unique-identifier="bookid" xml:lang="{lang}">\n'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        + "\n".join(meta)
        + "\n</metadata>\n<manifest>\n"
        + "\n".join(manifest)
        + '\n</manifest>\n<spine toc="ncx">\n'
        + "\n".join(spine)
        + "\n</spine>\n</package>\n"
    )

    nav_items = "\n".join(
        f'<li><a href="{name}">{esc(label)}</a></li>' for name, label, _ in pages
    )
    nav = page(
        title,
        f'<nav epub:type="toc" id="toc"><h1>Contents</h1><ol>\n{nav_items}\n</ol></nav>',
        lang,
    )
    points = "\n".join(
        f'<navPoint id="np{i}" playOrder="{i}"><navLabel><text>{esc(label)}</text>'
        f'</navLabel><content src="{name}"/></navPoint>'
        for i, (name, label, _) in enumerate(pages, 1)
    )
    ncx = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
        f'<head><meta name="dtb:uid" content="{esc(ident)}"/></head>\n'
        f"<docTitle><text>{esc(title)}</text></docTitle>\n"
        f"<navMap>\n{points}\n</navMap>\n</ncx>\n"
    )
    container = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" '
        'media-type="application/oebps-package+xml"/></rootfiles>\n</container>\n'
    )

    out_dir = Path(out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / file_name(book)
    with zipfile.ZipFile(path, "w") as epub:
        # Readers require an uncompressed mimetype as the very first entry.
        epub.writestr(
            zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED
        )
        files = [
            ("META-INF/container.xml", container),
            ("OEBPS/content.opf", opf),
            ("OEBPS/nav.xhtml", nav),
            ("OEBPS/toc.ncx", ncx),
            ("OEBPS/style.css", CSS),
        ]
        files += [(f"OEBPS/{n}", page(t, body, lang)) for n, t, body in pages]
        for name, content in files:
            epub.writestr(name, content, zipfile.ZIP_DEFLATED)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("book", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    parser.add_argument(
        "--no-notes", action="store_true", help="leave out author notes"
    )
    args = parser.parse_args()
    book = json.loads(args.book.read_text(encoding="utf-8"))
    try:
        path = build(book, args.out_dir, include_notes=not args.no_notes)
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
