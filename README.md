# agent-plugins

Daniel Haven's plugin marketplace for Claude and OpenAI Codex/ChatGPT.
Marketplace name: **danielh-official-plugins**.

| Plugin | What it does | Runs on |
| --- | --- | --- |
| [notion-career-ops](plugins/notion-career-ops/README.md) | Career Ops job-search tracker in Notion | Claude, Codex, ChatGPT (needs Notion connected) |
| [netnewswire-digest](plugins/netnewswire-digest/README.md) | Ranked, summarized digest of NetNewsWire articles | Claude Code, local Codex on macOS (needs a shell) |
| [quiz-api](https://github.com/danielh-official/quiz-api/tree/main/plugins/quiz-api) | Study and write spaced-repetition quizzes via the Quiz API MCP server | Claude Code, Codex, Gemini CLI (needs a Quiz API account) |

## Install

### Claude Code

```sh
claude plugin marketplace add danielh-official/agent-plugins
claude plugin install notion-career-ops@danielh-official-plugins
claude plugin install netnewswire-digest@danielh-official-plugins
claude plugin install quiz-api@danielh-official-plugins
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
```

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
  plugin.json
  skills/<name>/
  scripts/
  README.md
scripts/validate.py
tests/
```

Both catalogs point at `./plugins/<name>`. One canonical skill per plugin serves
both clients. No bundled MCP servers.

## Release / add a plugin

- Keep the version in both plugin manifests in sync.
- New plugin: add the full package under `plugins/<name>/` (both manifests,
  skill, OpenAI metadata, validator, tests), list it in both catalogs, add its
  suite to the workflow, then validate.
- Skill wording changes need explicit approval.
