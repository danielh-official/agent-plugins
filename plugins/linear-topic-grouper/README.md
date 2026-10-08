# linear-topic-grouper

One canonical skill that pulls issues from Linear, clusters them into topic
groups, flags duplicates and overlaps, and (only on request) writes the
grouping back as topic labels or parent issues. Packaged for Claude and
Codex/ChatGPT.

## Layout

```text
.claude-plugin/plugin.json
plugin.json
skills/linear-topic-grouper/SKILL.md
skills/linear-topic-grouper/agents/openai.yaml
```

This package lives inside the `agent-plugins` master repository, which
owns both marketplace catalogs. Its marketplace identity is `danielh-official-plugins`.
See the [master README](../../README.md) for installation and full validation.

## Requirements

- **The host agent must have the Linear MCP server (or an equivalent Linear
  app connection) installed and authenticated.** This plugin ships only a
  skill, no Linear tools. Connect Linear in each client separately.
- Write-back (labels or parent issues) needs a Linear connection that can
  create labels and edit issues. The skill never writes without an explicit yes.

## Editing and validation

1. Edit the canonical skill only with explicit approval of wording changes.
2. Bump `version` in both plugin manifests.
3. Run `claude plugin validate .`.
4. From the master root, run every step of `.github/workflows/validate.yml`;
   the root `scripts/validate.py` checks this package.

## Local use

For Claude Code, load this folder with `claude --plugin-dir .`.
For a marketplace installation in Claude Code or Codex, add the master root
as described in its README.

## Replacing the standalone Claude skill

Disable the standalone `linear-topic-grouper` skill under **Customize > Skills**
before enabling the plugin, so two copies don't compete. Keep it disabled
rather than deleted until the plugin works in a fresh conversation.

## Platform limitations

The skill was written for claude.ai. It names `ask_user_input_v0` for the
scoping question and `tool_search` for loading Linear tools; other clients
lack those exact tools and fall back to asking in plain text and to their own
tool loading. The wording is kept as written; changing it needs approval.
