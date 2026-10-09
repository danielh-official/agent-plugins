# netnewswire

<img width="1593" height="865" alt="Screenshot 2026-10-04 at 4 16 59 PM" src="https://github.com/user-attachments/assets/b568e3aa-7a5d-47f7-b32b-0dab4d1ab33d" />

A plugin for Claude Code and local Codex on macOS with one skill that pulls articles out of [NetNewsWire](https://netnewswire.com) by filter, ranks them by relevance to you, and summarizes them.

Ask things like:

- "Summarize my unread NetNewsWire articles"
- "What's new in my News folder from the last 24 hours?"
- "Catch me up on my starred articles"

Your agent fetches the matching articles, sorts them into Read now, Worth a skim and Skip based on what it knows about you, and gives a short summary of each of the first two groups. It does not mark anything read or change NetNewsWire.

## Requirements

- macOS with NetNewsWire installed
- Claude Code, local Codex, or another surface with a shell on your Mac so the skill can run `osascript`
- Python 3 (ships with the Xcode command line tools)
- The first run may show a macOS prompt asking whether your terminal can control NetNewsWire. Click Allow.
- Your Mac must be awake and unlocked, or AppleScript calls time out.

This skill does not work in a cloud sandbox, because NetNewsWire runs only on your Mac.

It also does not work in ChatGPT desktop chat. The plugin is skill-only (no MCP server or tools), so chat shows it as selected but exposes no callable actions. Use Claude Code or the Codex CLI in a terminal instead; both have a shell. Either one works as a fallback when the other's usage runs out.

## Install

This package lives in the `agent-plugins` master repository.
Its marketplace identity is `danielh-official-plugins`. For local testing, follow
the [master README](../../README.md) to add the master root directly.
For Claude Code development without a marketplace, use `claude --plugin-dir .`.

After publishing the master repository:

```sh
claude plugin marketplace add danielh-official/agent-plugins
claude plugin install netnewswire@danielh-official-plugins

codex plugin marketplace add danielh-official/agent-plugins
codex plugin add netnewswire@danielh-official-plugins
```

Start a new session after installing or updating. This skill cannot access the
Mac app from ChatGPT web or another cloud sandbox.

### Legacy marketplace

This package does not include the old single-plugin marketplace catalog.
If you previously installed `netnewswire-digest@netnewswire-digest-marketplace`,
disable or uninstall it before enabling `netnewswire@danielh-official-plugins`.
Do not keep both copies enabled.

## Editing and validation

The canonical skill remains `skills/digest/SKILL.md`; its wording is
unchanged by the packaging update. Both clients use the same skill and scripts.
Bump the version in both plugin manifests when releasing changes. Run:

```sh
claude plugin validate .
claude plugin validate .claude-plugin/plugin.json
```

GitHub Actions runs the Python packaging checks and regression tests on every push and pull request.
The workflow lives at the master root and also checks both catalogs and packages.
The root `scripts/validate.py` checks this package's metadata conventions, not
the entire YAML schema. Refresh the marketplace and installed plugin explicitly as needed;
catalog sync does not necessarily update an installed cached package.

## Filters

The fetch script takes a JSON filter:

| Option | Meaning |
|---|---|
| `account` | exact account name, such as `iCloud` |
| `folder` | exact folder name |
| `feed` | case-insensitive substring of the feed name |
| `unread` | `true` (default) for unread only, `false` for read and unread |
| `starred` | `true` for starred only |
| `sinceHours` | only articles published or arrived in the last N hours |
| `limit` | cap on articles written, newest first |
| `excludeFolders` | array of folder names to skip |
| `out` | output path (default `/tmp/nnw/articles.json`) |

You can also run it directly:

```
osascript -l JavaScript skills/digest/scripts/nnw_fetch.js '{"unread":true,"folder":"News"}'
python3 skills/digest/scripts/nnw_digest.py /tmp/nnw/articles.json 450
```

## Notes

- Many feeds provide only a title or short teaser. The skill labels those headline-only rather than guessing at content.
- Article text is read from your local NetNewsWire database through AppleScript. Nothing is sent anywhere except to your chosen agent as part of your conversation.
