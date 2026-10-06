# agent-plugins

Daniel Haven's plugin marketplace for Claude, OpenAI Codex/ChatGPT, and Google Antigravity CLI (`agy`).
Marketplace name: **danielh-official-plugins**.

| Plugin | What it does | Runs on |
| --- | --- | --- |
| [notion-career-ops](plugins/notion-career-ops/README.md) | Career Ops job-search tracker in Notion | Claude, Codex, ChatGPT, Antigravity CLI (needs Notion connected) |
| [netnewswire-digest](plugins/netnewswire-digest/README.md) | Ranked, summarized digest of NetNewsWire articles | Claude Code, local Codex, Antigravity CLI on macOS (needs a shell) |
| [calslashd](plugins/calslashd/README.md) | Calorie-budget stats from Apple Health using the CalSlashD app's formulas | Claude, Codex, ChatGPT, Antigravity CLI on iOS (needs Apple Health access) |
| [quiz-api](https://github.com/danielh-official/quiz-api/tree/main/plugins/quiz-api) | Study and write spaced-repetition quizzes via the Quiz API MCP server | Claude Code, Codex, Antigravity CLI (needs your own fork of quiz-api, deployed, with `QUIZ_API_URL` set) |

## Install

### Claude Code

```sh
claude plugin marketplace add danielh-official/agent-plugins
claude plugin install notion-career-ops@danielh-official-plugins
claude plugin install netnewswire-digest@danielh-official-plugins
claude plugin install quiz-api@danielh-official-plugins
claude plugin install calslashd@danielh-official-plugins
```

Or inside a session: `/plugin marketplace add danielh-official/agent-plugins`,
then `/plugin install <name>@danielh-official-plugins`.

### Claude web / desktop

**Customize > Plugins > Add > Add marketplace**, enter
`danielh-official/agent-plugins`, then install the plugins you want.

### Codex CLI

```sh
codex plugin marketplace add danielh-official/agent-plugins
codex plugin add notion-career-ops@danielh-official-plugins
codex plugin add netnewswire-digest@danielh-official-plugins
codex plugin add quiz-api@danielh-official-plugins
codex plugin add calslashd@danielh-official-plugins
```

### Antigravity CLI (`agy`)

`agy` has a marketplace, but its docs don't cover third-party ones and it can't
add this one yet. Clone and install each plugin directory by path:

```sh
git clone https://github.com/danielh-official/agent-plugins.git
agy plugin install ./agent-plugins/plugins/notion-career-ops
agy plugin install ./agent-plugins/plugins/netnewswire-digest
agy plugin install ./agent-plugins/plugins/calslashd
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
python3 -m unittest discover -s plugins/notion-career-ops/scripts -p 'test_*.py' -v
python3 -m unittest discover -s plugins/netnewswire-digest/scripts -p 'test_*.py' -v
python3 -m unittest discover -s plugins/calslashd/scripts -p 'test_*.py' -v
python3 plugins/calslashd/skills/calslashd/scripts/selfcheck.py
claude plugin validate .
```

CI runs the same on every push and pull request. Run suites separately; package
test module names collide.

## Layout

```text
.claude-plugin/marketplace.json     Claude catalog
.agents/plugins/marketplace.json    Codex/OpenAI catalog
plugins/<name>/
  .claude-plugin/plugin.json
  plugin.json                       Codex/OpenAI + Antigravity manifest
  skills/<name>/
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
  skill, OpenAI metadata, validator, tests), list it in both catalogs, add its
  suite to the workflow, then validate.
- Skill wording changes need explicit approval.
