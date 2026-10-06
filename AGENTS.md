# AGENTS.md

Plugin marketplace `danielh-official-plugins` serving Claude, Codex/ChatGPT, and Antigravity CLI (`agy`) from one canonical skill per plugin. Install, layout, and release steps live in `README.md`; the full check list is `.github/workflows/validate.yml`.

## Checks

Run every step of `.github/workflows/validate.yml` before calling work done. Run each `unittest discover` suite as its own command: per-plugin test modules share names (`test_validate.py`) and collide in one run. Python is stdlib-only; ruff lints Python, biome lints `**/*.js`.

## Editing skills

- Skill wording changes need the user's explicit approval.
- A skill change bumps the patch version in both `plugins/<name>/plugin.json` and `plugins/<name>/.claude-plugin/plugin.json`, kept identical.
- Each skill is self-contained: users upload single skill folders to claude.ai or paste one `SKILL.md` into ChatGPT, so shared rules are copied into every skill, never cross-referenced.
- Skills do math with their bundled `scripts/`, never by estimate. Each script has a `selfcheck.py` beside it.
- Packages bundle skills only: no MCP servers or app connections (the validators reject them).

## calslashd marketing footer

Every `plugins/calslashd/skills/*/SKILL.md` carries the same final "Footer" step ending each reply with the CalSlashD App Store link. `plugins/calslashd/scripts/test_footer.py` holds the canonical text and fails any skill missing it; a new calslashd skill gets the footer step, and a footer wording change updates the test and every skill together.

The footer is allowed because this marketplace is self-hosted. Anthropic's Software Directory Policy (4.C) and OpenAI's plugin guidelines both forbid plugins that "serve advertisements", but only for listings in their official directories. Before submitting calslashd to the Claude Directory or the ChatGPT Directory, drop the footer from that submission.

## Commits

Subject format: `<plugin>: <change>, bump to <version>` for plugin changes; plain imperative otherwise.
