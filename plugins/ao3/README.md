# ao3

A plugin for reading [Archive of Our Own](https://archiveofourown.org) stories in Apple Books. Its one skill, `ebook`, turns the chapters you pick into an EPUB.

Ask things like:

- "Make an ebook of chapters 1-3 and 7 of https://archiveofourown.org/works/12345"
- "Give me the latest two chapters of this fic as an EPUB"
- "Turn this pasted chapter into an ebook" (then paste the text)

You get one book per story. Picking only some chapters adds them to the title, e.g. "The Lake House (ch 1-3, 7)", so different picks from the same story don't collide in Books.

## Two modes

| | Fetch mode | Paste mode |
| --- | --- | --- |
| Input | A work or chapter URL | Chapter text you paste in |
| Needs | A shell that can reach archiveofourown.org | Python only |
| Works in | Claude Code, Codex, `agy` on your Mac | Those, plus the Claude and ChatGPT iPhone apps |
| Formatting | Kept (italics, bold, centered text) | Usually lost, since chat receives plain text |

## Getting the book into Apple Books

- **Mac:** the skill runs `open -a Books` on the EPUB. Books imports it, and iCloud syncs it to your iPhone and iPad when iCloud is on for Books.
- **iPhone:** the chat hands you the EPUB file. Tap it, then Share, then Books.

## Respecting AO3

AO3 has no public API, and it asks that automated access not strain its servers. Fetch mode:

- makes one request per work (the full-work page), never one per chapter
- fetches works one at a time, at least 5 seconds apart
- retries a rate-limit response at most once, then stops
- sends a User-Agent that names this plugin
- caches pages for a few hours, so changing your chapter pick doesn't refetch

Works restricted to registered users are skipped. The plugin never asks for or stores your AO3 login. The EPUB is for your own reading, and it keeps the author credit and a link back to the work.

## Scripts

All under `skills/ebook/scripts/`, Python 3.9+, standard library only:

| Script | Does |
| --- | --- |
| `ao3.py fetch URL` | Fetch or reuse a cached work, then list its chapters |
| `ao3.py parse PAGE.html --url URL` | Parse a saved work page instead |
| `ao3.py pick WORK.json "1-3, 7" --out BOOK.json` | Choose chapters (`latest 2`, `first 5`, and `all` also work) |
| `paste.py TEXT... --title T --author A --out BOOK.json` | Turn pasted text into chapters |
| `epub.py BOOK.json --out-dir DIR [--no-notes]` | Write the EPUB |
| `selfcheck.py` | Offline tests against the files in `fixtures/` |

## Install

See the [master README](../../README.md). In short:

```sh
claude plugin install ao3@danielh-official-plugins
codex plugin add ao3@danielh-official-plugins
```

Start a new session after installing or updating.
