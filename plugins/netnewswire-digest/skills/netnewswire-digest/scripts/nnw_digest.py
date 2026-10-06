#!/usr/bin/env python3
"""Condense the JSON written by nnw_fetch.js into a readable digest, grouped by feed.

Usage: python3 nnw_digest.py [articles.json] [chars_per_article]
"""

import collections
import html
import json
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/nnw/articles.json"
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 450

with open(path) as fh:
    data = json.load(fh)

print(f"total={data['total']} shown={len(data['articles'])} errors={data['errors']}")

groups = collections.OrderedDict()
for art in data["articles"]:
    groups.setdefault((art["account"], art["folder"], art["feed"]), []).append(art)

for (account, folder, feed), arts in groups.items():
    print(f"\n### {account} / {folder} / {feed} ({len(arts)})")
    for art in arts:
        text = re.sub(
            r"<(script|style).*?</\1>", " ", art["html"] or "", flags=re.DOTALL
        )
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", html.unescape(text)).strip()
        print(f"- {art['title'] or '(untitled)'} | {art['published'][:16]}")
        print(f"  {art['url']}")
        print(f"  {text[:limit]}")
