#!/usr/bin/env python3
"""Validate this standalone plugin package using only the standard library."""

import json
import re
import sys
from pathlib import Path


def validate(root):
    errors = []

    def load(relative):
        try:
            value = json.loads((root / relative).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{relative}: {exc}")
            return {}
        if not isinstance(value, dict):
            errors.append(f"{relative}: expected a JSON object")
            return {}
        return value

    claude = load(".claude-plugin/plugin.json")
    portable = load("plugin.json")
    for field in ("name", "version", "description"):
        value = claude.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Claude manifest: missing or invalid {field}")
        if value != portable.get(field):
            errors.append(f"Plugin manifests disagree on {field}")
    name = claude.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        errors.append("Plugin name must be lowercase kebab-case")
    version = claude.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append("Plugin version must use major.minor.patch")
    if claude.get("skills") != "./skills/":
        errors.append("Expected skills path ./skills/")
    if (
        portable.get("$schema")
        != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    ):
        errors.append("OpenAI manifest: expected Agent Plugins 1.0.0 schema")
    if (root / ".claude-plugin/marketplace.json").exists():
        legacy = load(".claude-plugin/marketplace.json")
        entries = legacy.get("plugins")
        if (
            not isinstance(entries, list)
            or len(entries) != 1
            or not isinstance(entries[0], dict)
        ):
            errors.append("Legacy marketplace must contain exactly one plugin entry")
        else:
            if entries[0].get("name") != claude.get("name"):
                errors.append("Legacy marketplace and plugin manifest disagree on name")
            for field in ("version", "description"):
                if field in entries[0]:
                    errors.append(
                        f"Legacy marketplace must not duplicate manifest {field}"
                    )
    for platform, manifest in (("Claude", claude), ("OpenAI", portable)):
        if "mcpServers" in manifest or "apps" in manifest:
            errors.append(
                f"{platform}: this skills-only package must not bundle app or MCP connections"
            )
    extensions = portable.get("extensions")
    openai = extensions.get("com.openai") if isinstance(extensions, dict) else None
    interface = openai.get("interface") if isinstance(openai, dict) else None
    if not isinstance(interface, dict):
        errors.append("OpenAI manifest: missing extensions.com.openai.interface object")
    else:
        for field in ("displayName", "shortDescription"):
            value = interface.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"Codex interface: missing or invalid {field}")
        prompts = interface.get("defaultPrompt")
        if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
            errors.append("Codex defaultPrompt must contain 1 to 3 prompts")
        elif any(
            not isinstance(p, str) or not p.strip() or len(p) > 128 for p in prompts
        ):
            errors.append(
                "Codex defaultPrompt entries must be nonempty strings of at most 128 characters"
            )
    skills = sorted((root / "skills").glob("*/SKILL.md"))
    if len(skills) != 1:
        errors.append("Expected exactly one skills/*/SKILL.md")
    for skill in skills:
        try:
            text = skill.read_text(encoding="utf-8")
            metadata = (skill.parent / "agents/openai.yaml").read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{skill.relative_to(root)}: {exc}")
            continue
        frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.DOTALL)
        if not frontmatter:
            errors.append(f"{skill.relative_to(root)}: missing frontmatter")
            continue
        fields = {}
        for line in frontmatter.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip().strip("'\"")
        if fields.get("name") != skill.parent.name or skill.parent.name != name:
            errors.append("Skill frontmatter, folder, and plugin names must agree")
        description = fields.get("description", "")
        if not description or len(description) > 1024:
            errors.append(
                "Skill description must be nonempty and at most 1024 characters"
            )
        if not re.search(r"^interface:\s*$", metadata, re.MULTILINE):
            errors.append("openai.yaml: missing interface")
        for key in ("display_name", "short_description", "default_prompt"):
            match = re.search(rf"^  {key}:[ \t]*([^\r\n]*)$", metadata, re.MULTILINE)
            if not match or not match.group(1).strip().strip("'\"").strip():
                errors.append(f"openai.yaml: missing or empty {key}")
    return errors


def main():
    root = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) == 2
        else Path(__file__).resolve().parent.parent
    )
    if len(sys.argv) > 2:
        print("Usage: python3 scripts/validate.py [plugin-root]", file=sys.stderr)
        return 2
    errors = validate(root)
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: plugin manifests and skill packaging are in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
