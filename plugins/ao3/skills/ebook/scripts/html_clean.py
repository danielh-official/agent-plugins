"""Tiny HTML tree plus an allowlist sanitizer that emits EPUB-safe XHTML."""

import html
import re
from html.parser import HTMLParser

VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}

# Kept as-is (attributes are filtered separately).
ALLOWED = {
    "p",
    "br",
    "hr",
    "em",
    "i",
    "strong",
    "b",
    "u",
    "s",
    "del",
    "ins",
    "sub",
    "sup",
    "small",
    "blockquote",
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "div",
    "span",
    "a",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "td",
    "th",
    "caption",
    "pre",
    "code",
    "abbr",
    "cite",
    "q",
}
RENAMED = {"strike": "s", "center": "div", "big": "span", "font": "span"}
DROPPED = {
    "script",
    "style",
    "iframe",
    "object",
    "embed",
    "noscript",
    "form",
    "input",
    "button",
    "select",
    "textarea",
    "video",
    "audio",
    "svg",
    "math",
    "head",
    "title",
    "template",
}
ALIGN = {"left", "right", "center", "justify"}
# Characters XML 1.0 forbids.
INVALID_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


class Node:
    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.parent = parent

    @property
    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def iter(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.iter()

    def find_all(self, tag=None, cls=(), **attrs):
        want = set([cls] if isinstance(cls, str) else cls)
        for node in self.iter():
            if tag and node.tag != tag:
                continue
            if want and not want <= node.classes:
                continue
            if any(node.attrs.get(k) != v for k, v in attrs.items()):
                continue
            yield node

    def find(self, tag=None, cls=(), **attrs):
        return next(self.find_all(tag, cls, **attrs), None)

    def text(self):
        parts = []
        for child in self.children:
            parts.append(child.text() if isinstance(child, Node) else child)
        return "".join(parts)


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse(markup):
    builder = _Builder()
    builder.feed(markup)
    builder.close()
    return builder.root


def clean_text(value):
    return INVALID_XML.sub("", value)


def esc(value):
    return html.escape(clean_text(value), quote=False)


def attr(value):
    return html.escape(clean_text(value), quote=True)


def _attrs(tag, node):
    out = []
    if tag == "a":
        href = (node.attrs.get("href") or "").strip()
        if re.match(r"(?i)^(https?:|mailto:)", href):
            out.append(f' href="{attr(href)}"')
    if tag in ("td", "th"):
        for name in ("colspan", "rowspan"):
            value = node.attrs.get(name) or ""
            if value.isdigit():
                out.append(f' {name}="{value}"')
    if tag == "ol":
        start = node.attrs.get("start") or ""
        if start.isdigit():
            out.append(f' start="{start}"')
    align = (node.attrs.get("align") or "").lower()
    if node.tag == "center":
        align = "center"
    if align in ALIGN:
        out.append(f' class="align-{align}"')
    return "".join(out)


def _image(node):
    src = (node.attrs.get("src") or "").strip()
    label = node.attrs.get("alt") or "image"
    if re.match(r"(?i)^https?:", src):
        return f'<a href="{attr(src)}">[{esc(label)}]</a>'
    return f"[{esc(label)}]"


def sanitize(node):
    """Serialize a node's children as allowlisted, well-formed XHTML."""
    parts = []
    for child in node.children:
        if not isinstance(child, Node):
            parts.append(esc(child))
            continue
        tag = RENAMED.get(child.tag, child.tag)
        if tag in DROPPED:
            continue
        if tag == "img":
            parts.append(_image(child))
        elif tag in ("br", "hr"):
            parts.append(f"<{tag}{_attrs(tag, child)}/>")
        elif tag in ALLOWED:
            inner = sanitize(child)
            if tag == "a" and not inner.strip():
                continue
            parts.append(f"<{tag}{_attrs(tag, child)}>{inner}</{tag}>")
        else:
            parts.append(sanitize(child))
    return "".join(parts)


BLOCK = {"p", "br", "div", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}


def _spaced_text(node):
    parts = []
    for child in node.children:
        if not isinstance(child, Node):
            parts.append(child)
        elif child.tag not in DROPPED:
            gap = " " if child.tag in BLOCK or child.tag == "hr" else ""
            parts.append(gap + _spaced_text(child) + gap)
    return "".join(parts)


def word_count(node):
    """Whitespace-separated tokens holding a letter or digit (skips '* * *')."""
    return sum(1 for t in _spaced_text(node).split() if any(c.isalnum() for c in t))
