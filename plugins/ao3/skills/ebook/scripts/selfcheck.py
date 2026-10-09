#!/usr/bin/env python3
"""Offline checks for ao3.py, paste.py and epub.py. Run: python3 selfcheck.py"""

import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from ao3 import Locked, parse_work, pick, select, work_id
from epub import build, chapter_label, file_name
from paste import build_book

FIXTURES = Path(__file__).resolve().parent / "fixtures"
URL = "https://archiveofourown.org/works/12345"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def epub_files(path):
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        assert infos[0].filename == "mimetype", "mimetype must come first"
        assert infos[0].compress_type == zipfile.ZIP_STORED
        assert z.read("mimetype") == b"application/epub+zip"
        files = {i.filename: z.read(i.filename).decode("utf-8") for i in infos}
    for name, content in files.items():
        if name.endswith((".xhtml", ".opf", ".ncx", ".xml")):
            ElementTree.fromstring(content.encode("utf-8"))  # well-formed XML
    return files


# URLs: works, chapters, collections, bare ids
assert work_id("https://archiveofourown.org/works/12345/chapters/999") == "12345"
assert work_id("archiveofourown.org/collections/fest/works/42") == "42"
assert work_id(" 777 ") == "777"
try:
    work_id("https://example.com/works/1")
    raise AssertionError("non-AO3 URL accepted")
except ValueError:
    pass

# Parsing a multi-chapter full-work page
work = parse_work(fixture("multi.html"), URL)
assert work["title"] == "The Lake House"
assert work["authors"] == ["Example Author", "Co Writer"]
assert work["chapter_count"] == "3/?"
assert work["language"] == "English"
tags = dict(work["tags"])
assert tags["Rating"] == ["General Audiences"]
assert tags["Additional Tags"] == ["Slow Burn", "Found Family"]
assert [c["number"] for c in work["chapters"]] == [1, 2, 3]
assert [c["title"] for c in work["chapters"]] == [
    "Chapter 1: Arrival",
    "Chapter 2",
    "Chapter 3: Storm <Warning>",
]
one = work["chapters"][0]
assert "Chapter Text" not in one["html"]
assert "<iframe" not in one["html"] and "onclick" not in one["html"]
assert '<p class="align-center">' in one["html"]
assert "<i>laughed</i>" in one["html"] and "<br/>" in one["html"]
assert '<a href="https://example.com/a.png">[map]</a>' in one["html"]
assert "Hello readers." in one["notes_before_html"]
assert "See the end" not in one["notes_before_html"]
assert "Thanks for reading!" in one["notes_after_html"]
assert one["words"] == 13, one["words"]
assert "It rains." in work["chapters"][2]["notes_before_html"]
assert "More to come." in work["chapters"][2]["notes_after_html"]
assert work["summary_text"] == "Two friends & a lake."

# One-shot and locked pages
shot = parse_work(fixture("oneshot.html"), "https://archiveofourown.org/works/9")
assert shot["authors"] == ["Anonymous"]
assert len(shot["chapters"]) == 1 and shot["chapters"][0]["title"] == "Small Hours"
assert "Work Text" not in shot["chapters"][0]["html"]
try:
    parse_work(fixture("login.html"), URL)
    raise AssertionError("locked page parsed")
except Locked:
    pass

# Chapter selection
nums = [1, 2, 3, 4, 5, 6, 7, 8]
assert select(nums, "1-3, 7") == [1, 2, 3, 7]
assert select(nums, "latest 2") == [7, 8]
assert select(nums, "first 2 and chapter 5") == [1, 2, 5]
assert select(nums, "all") == nums
assert select(nums, "3 to 1") == [1, 2, 3]
for bad in ("9", "latest 0", "soon", ""):
    try:
        select(nums, bad)
        raise AssertionError(f"accepted {bad!r}")
    except ValueError:
        pass
assert chapter_label([7, 1, 2, 3]) == "ch 1-3, 7"
partial = pick(work, "1, 3")
assert partial["label"] == "ch 1, 3"
assert [c["number"] for c in partial["chapters"]] == [1, 3]
assert "label" not in pick(work, "all")

# Paste mode
book = build_book([fixture("pasted.txt")], "The Lake House", ["Example Author"])
assert [c["title"] for c in book["chapters"]] == ["Chapter 4: The Pier", "Chapter 5"]
assert [c["number"] for c in book["chapters"]] == [4, 5]
assert book["label"] == "ch 4-5"
first = book["chapters"][0]["html"]
assert "The boards creaked under her feet.<br/>She kept walking." in first
assert "<hr/>" in first
assert "&lt;b&gt;not bold&lt;/b&gt; &amp; that" in book["chapters"][1]["html"]
plain = build_book(["One line.\nAnother line."], "T", ["A"], chapter_title="Prologue")
assert plain["chapters"][0]["title"] == "Prologue"
assert "label" not in plain
assert plain["chapters"][0]["html"] == "<p>One line.</p>\n<p>Another line.</p>"
started = build_book(["Text."], "T", ["A"], start=6)
assert started["chapters"][0]["number"] == 6 and started["label"] == "ch 6"
try:
    build_book(["  \n\n "], "T", ["A"])
    raise AssertionError("empty paste accepted")
except ValueError:
    pass

# EPUB output
with tempfile.TemporaryDirectory() as tmp:
    path = build(partial, tmp, modified="2026-10-09T00:00:00Z")
    assert path.name == "The Lake House (ch 1, 3) - Example Author, Co Writer.epub"
    files = epub_files(path)
    opf = files["OEBPS/content.opf"]
    assert "<dc:title>The Lake House (ch 1, 3)</dc:title>" in opf
    assert "<dc:creator>Co Writer</dc:creator>" in opf
    assert "<dc:language>en</dc:language>" in opf
    assert "<dc:subject>Slow Burn</dc:subject>" in opf
    assert sorted(n for n in files if n.startswith("OEBPS/ch")) == [
        "OEBPS/ch001.xhtml",
        "OEBPS/ch002.xhtml",
    ]
    assert "Chapter 3: Storm &lt;Warning&gt;" in files["OEBPS/ch002.xhtml"]
    assert "Hello readers." in files["OEBPS/ch001.xhtml"]
    assert "Work notes here." in files["OEBPS/title.xhtml"]
    nav = files["OEBPS/nav.xhtml"]
    assert nav.count("<li>") == 3

    bare = build(partial, Path(tmp) / "bare", include_notes=False)
    bare_files = epub_files(bare)
    assert "Hello readers." not in bare_files["OEBPS/ch001.xhtml"]
    assert "Work notes here." not in bare_files["OEBPS/title.xhtml"]

    pasted = build(book, tmp)
    assert "Archive of Our Own" not in epub_files(pasted)["OEBPS/content.opf"]

assert file_name({"title": 'a/b:c?"', "authors": []}) == "abc.epub"

print("selfcheck OK")
