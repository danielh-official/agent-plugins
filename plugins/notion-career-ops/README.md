# notion-career-ops

One canonical skill for the Career Ops job-search tracker in Notion, packaged for
Claude and Codex/ChatGPT.

## Layout

```text
.claude-plugin/plugin.json
plugin.json
skills/notion-career-ops/SKILL.md
skills/notion-career-ops/agents/openai.yaml
scripts/validate.py
scripts/test_validate.py
```

This package lives inside the `agent-plugins` master repository, which
owns both marketplace catalogs. Its marketplace identity is `danielh-official-plugins`.
See the [master README](../../README.md) for installation and full validation.

## Requirements

- **The host agent must have the Notion MCP server (or an equivalent Notion
  app connection) installed and authenticated.** This plugin cannot work
  without it: it ships only a skill, no Notion tools. This applies to every
  client (Claude Code, Codex, Antigravity CLI), so connect Notion in each one
  separately.
- Access to a **Career Ops** page containing **Profile**, **Jobs**, **Events**,
  **Contacts**, and **Notes**

The plugin discovers this structure by exact page and database name. It does
not bundle a Notion connection or store workspace identifiers.

## Editing and validation

1. Edit the canonical skill only with explicit approval of wording changes.
2. Bump `version` in both plugin manifests.
3. Run `python3 scripts/validate.py` (this plugin's own rule: exactly one skill),
   `python3 -m unittest discover -s scripts -p 'test_*.py' -v`, and `claude plugin validate .`.
4. From the master root, run every step of `.github/workflows/validate.yml`;
   the root `scripts/validate.py` checks the shared packaging rules.

GitHub Actions runs the Python validator and regression tests on every push and pull request.
The lightweight validator checks our packaging conventions; it is not a full
YAML parser or a replacement for the clients' manifest validation.
Catalog sync and installed-package updates are separate operations. A push
does not guarantee that an already installed plugin or active session refreshes.

## Local use

For Claude Code, load this folder with `claude --plugin-dir .`.
For a marketplace installation in Claude Code or Codex, add the master root
as described in its README. Do not install another
copy while the standalone skill or an older plugin copy is enabled.

## Hosted installation, after publishing

```sh
claude plugin marketplace add danielh-official/agent-plugins
claude plugin install notion-career-ops@danielh-official-plugins

codex plugin marketplace add danielh-official/agent-plugins
codex plugin add notion-career-ops@danielh-official-plugins
```

Git credentials must grant access to the master repository.
Restart the client session after installing or updating the plugin.

In Claude web or desktop, use **Customize > Plugins > Add > Add marketplace**.
ChatGPT marketplace access depends on the account and surface. Workspace admins
can use **Admin > Plugins > Add > Import marketplace** where available.
Do not assume a personal account supports import or standalone ZIP upload.

## Replacing the standalone Claude skill

Back up the standalone skill, then confirm marketplace access. Disable the
standalone under **Customize > Skills** before installing/enabling the plugin.
Verify the plugin in a fresh conversation with a read-only tracker lookup.
Keep the disabled standalone until verification succeeds. To roll back,
disable the plugin first, then re-enable the standalone.

## Platform limitations

The original skill wording is preserved. Its formula-field limitation, and 2Do assumption still require testing on ChatGPT.
Do not invent replacements or change those instructions without approval.

The plugin bundles no Notion MCP server or app connection. Connect Notion
independently in each client. An authentication policy in a marketplace does
not establish a Notion connection. The skill checks connectivity and named
workspace structure before attempting tracker operations.
