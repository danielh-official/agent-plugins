# agent-plugins

Daniel Haven's plugin marketplace for Claude, OpenAI Codex/ChatGPT, and Google Antigravity CLI (`agy`).
Marketplace name: **danielh-official-plugins**.

| Plugin | What it does | Runs on |
| --- | --- | --- |
| [career-ops](plugins/career-ops/README.md) | Career Ops job-search tracker in Notion | Claude, Codex, ChatGPT, Antigravity CLI (needs Notion connected) |
| [netnewswire](plugins/netnewswire/README.md) | Ranked, summarized digest of NetNewsWire articles | Claude Code, local Codex, Antigravity CLI on macOS (needs a shell) |
| [calslashd](plugins/calslashd/README.md) | Calorie-budget stats from Apple Health using the CalSlashD app's formulas | Claude, Codex, ChatGPT, Antigravity CLI on iOS (needs Apple Health access) |
| [linear](plugins/linear/README.md) | Groups Linear issues by topic, flags duplicates, optionally writes labels or parent issues back | Claude, Codex, ChatGPT, Antigravity CLI (needs Linear connected) |
| [ao3](plugins/ao3/README.md) | EPUBs for Apple Books from chosen AO3 chapters, fetched or pasted | Fetch: Claude Code, Codex, Antigravity CLI on a Mac. Paste: also the Claude and ChatGPT iPhone apps |
| [quiz-api](https://github.com/danielh-official/quiz-api/tree/main/plugins/quiz-api) | Study and write spaced-repetition quizzes via the Quiz API MCP server | Claude Code, Codex, Antigravity CLI (needs your own fork of quiz-api, deployed, with `QUIZ_API_URL` set) |

A plugin is named after the app it is built for (`linear:topic-grouper`), or after its job when the app
is only where its data lives (`career-ops:insights`, which stores data in Notion). Skills are named after what they do.
If you installed `notion-career-ops`, `netnewswire-digest` or `linear-topic-grouper` under their old
names, uninstall them and install `career-ops`, `netnewswire` or `linear` instead.

## Install

### Claude Code

```sh
claude plugin marketplace add danielh-official/agent-plugins
claude plugin install career-ops@danielh-official-plugins
claude plugin install netnewswire@danielh-official-plugins
claude plugin install quiz-api@danielh-official-plugins
claude plugin install calslashd@danielh-official-plugins
claude plugin install linear@danielh-official-plugins
claude plugin install ao3@danielh-official-plugins
```

Or inside a session: `/plugin marketplace add danielh-official/agent-plugins`,
then `/plugin install <name>@danielh-official-plugins`.

### Claude web / desktop

**Customize > Plugins > Add > Add marketplace**, enter
`danielh-official/agent-plugins`, then install the plugins you want.

### Codex CLI

```sh
codex plugin marketplace add danielh-official/agent-plugins
codex plugin add career-ops@danielh-official-plugins
codex plugin add netnewswire@danielh-official-plugins
codex plugin add quiz-api@danielh-official-plugins
codex plugin add calslashd@danielh-official-plugins
codex plugin add linear@danielh-official-plugins
codex plugin add ao3@danielh-official-plugins
```

### Antigravity CLI (`agy`)

`agy` has a marketplace, but its docs don't cover third-party ones and it can't
add this one yet. Clone and install each plugin directory by path:

```sh
git clone https://github.com/danielh-official/agent-plugins.git
agy plugin install ./agent-plugins/plugins/career-ops
agy plugin install ./agent-plugins/plugins/netnewswire
agy plugin install ./agent-plugins/plugins/calslashd
agy plugin install ./agent-plugins/plugins/linear
agy plugin install ./agent-plugins/plugins/ao3
```

`quiz-api` lives in its own repo; clone it and install `plugins/quiz-api` by
path the same way. Check a package with `agy plugin validate <path>`.

### ChatGPT

Supported workspaces: **Admin > Plugins > Add > Import marketplace** with
`https://github.com/danielh-official/agent-plugins`. Availability varies
by account; admins set authentication policy.

### After installing

- Start a fresh session. Installed plugins don't hot-reload.
- Update later: `claude plugin marketplace update danielh-official-plugins`, then
  reinstall/update the plugin.
- Notion: connect Notion in each app yourself. Installing doesn't grant access.
- Linear: same as Notion; connect Linear in each app yourself.
- NetNewsWire: macOS only. First run may prompt to let your terminal control
  NetNewsWire. Click Allow.
- Don't enable two copies of the same skill (older standalone skill, legacy
  plugin copy). Disable the old one first.

## Local development

Clone and add the checkout as a marketplace (use an absolute path):

```sh
git clone https://github.com/danielh-official/agent-plugins.git
claude plugin marketplace add /absolute/path/to/agent-plugins
codex plugin marketplace add /absolute/path/to/agent-plugins
```

Validate from the repo root:

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s plugins/calslashd/scripts -p 'test_*.py' -v
python3 plugins/calslashd/skills/insights/scripts/selfcheck.py
python3 plugins/ao3/skills/ebook/scripts/selfcheck.py
claude plugin validate .
```

CI runs the same on every push and pull request. Run suites separately; package
test module names collide.

`scripts/validate.py` checks the catalogs and the packaging rules every plugin
shares. A plugin's own `scripts/validate.py` is optional and holds only the
rules specific to that plugin; the root runs it when present.

## Layout

```text
.claude-plugin/marketplace.json     Claude catalog
.agents/plugins/marketplace.json    Codex/OpenAI catalog
plugins/<name>/
  .claude-plugin/plugin.json
  plugin.json                       Codex/OpenAI + Antigravity manifest
  skills/<skill>/
  scripts/
  README.md
scripts/validate.py
tests/
```

Both catalogs point at `./plugins/<name>`, or at a remote `git-subdir` source
(`quiz-api`). One canonical skill per plugin serves all four clients. No bundled MCP servers.

## Release / add a plugin

- Keep the version in both manifests (`.claude-plugin/plugin.json`,
  `plugin.json`) in sync.
- New plugin: add the full package under `plugins/<name>/` (both manifests,
  skill, OpenAI metadata), list it in both catalogs, then validate. Add a
  `scripts/validate.py` and tests only for plugin-specific rules, and add that
  suite to the workflow.
- Skill wording changes need explicit approval.
