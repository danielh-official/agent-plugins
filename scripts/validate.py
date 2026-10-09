#!/usr/bin/env python3
"""Validate catalogs and bundled plugin packages offline."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOGS = (".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json")


def load(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def source_key(source):
    if isinstance(source, str):
        source = {"source": "local", "path": source}
    if not isinstance(source, dict):
        raise ValueError("source must be a path or object")
    kind = source.get("source")
    if kind == "local":
        path = source.get("path")
        if (
            not isinstance(path, str)
            or not path.startswith("./")
            or ".." in Path(path).parts
        ):
            raise ValueError("local source must stay inside the marketplace root")
        return ("local", path)
    if kind == "github":
        repo = source.get("repo")
        if not isinstance(repo, str) or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
            raise ValueError("github source requires owner/repo")
        url = f"https://github.com/{repo}"
    elif kind == "url":
        url = source.get("url")
        if not isinstance(url, str) or not re.fullmatch(
            r"https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?", url
        ):
            raise ValueError("expected an HTTPS GitHub source without credentials")
        url = url.removesuffix(".git")
    elif kind == "git-subdir":
        url, path = source.get("url"), source.get("path")
        if not isinstance(url, str) or not re.fullmatch(
            r"https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?", url
        ):
            raise ValueError("expected an HTTPS GitHub source without credentials")
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or ".." in Path(path).parts
        ):
            raise ValueError("git-subdir source requires a relative path")
        url = f"{url.removesuffix('.git')}/{path.removeprefix('./')}"
    else:
        raise ValueError(f"unsupported source type: {kind}")
    return ("git", url, source.get("ref"), source.get("sha"))


def entries(catalog):
    plugins = catalog.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        raise ValueError("plugins must be a nonempty list")
    result = {}
    for entry in plugins:
        if not isinstance(entry, dict):
            raise ValueError("plugin entries must be objects")
        name = entry.get("name")
        if not isinstance(name, str) or not re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*", name
        ):
            raise ValueError("plugin names must be lowercase kebab-case")
        if name in result:
            raise ValueError(f"duplicate plugin: {name}")
        result[name] = entry
    return result


def validate_package(root):
    """Check the packaging rules every bundled plugin shares."""
    errors = []

    def read(relative):
        try:
            value = json.loads((root / relative).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{relative}: {exc}")
            return {}
        if not isinstance(value, dict):
            errors.append(f"{relative}: expected a JSON object")
            return {}
        return value

    claude = read(".claude-plugin/plugin.json")
    portable = read("plugin.json")
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
        legacy = read(".claude-plugin/marketplace.json")
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
    if not skills:
        errors.append("Expected at least one skills/<skill>/SKILL.md")
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
        if fields.get("name") != skill.parent.name:
            errors.append("Skill frontmatter and folder names must agree")
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


def validate(root):
    errors = []
    try:
        claude, codex = (load(root / path) for path in CATALOGS)
        cplugins, xplugins = entries(claude), entries(codex)
    except (OSError, UnicodeError, ValueError) as exc:
        return [str(exc)]
    if (
        claude.get("name") != codex.get("name")
        or claude.get("name") != "danielh-official-plugins"
    ):
        errors.append(
            "Both catalogs must retain marketplace name danielh-official-plugins"
        )
    if not isinstance(claude.get("owner"), dict) or not claude["owner"].get("name"):
        errors.append("Claude catalog requires owner.name")
    if set(cplugins) != set(xplugins):
        errors.append("Catalogs list different plugins")

    local_roots = {}
    for name in sorted(set(cplugins) & set(xplugins)):
        cplugin, xplugin = cplugins[name], xplugins[name]
        try:
            csource, xsource = (
                source_key(cplugin.get("source")),
                source_key(xplugin.get("source")),
            )
            if csource != xsource:
                errors.append(
                    f"{name}: catalogs point at different sources or revisions"
                )
            if csource[0] == "local":
                plugin_root = (root / csource[1]).resolve()
                if not plugin_root.is_relative_to(root.resolve()):
                    errors.append(
                        f"{name}: local source must stay inside the marketplace root"
                    )
                elif csource[1] != f"./plugins/{name}":
                    errors.append(f"{name}: local source must be ./plugins/{name}")
                else:
                    local_roots[name] = plugin_root
        except (OSError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
        for field in ("version", "description"):
            if field in cplugin:
                errors.append(
                    f"{name}: Claude catalog must not duplicate manifest {field}"
                )
        if "description" in xplugin:
            errors.append(
                f"{name}: OpenAI catalog must not duplicate manifest description"
            )
        if (
            str(cplugin.get("category", "")).lower()
            != str(xplugin.get("category", "")).lower()
        ):
            errors.append(f"{name}: categories disagree")
        policy = xplugin.get("policy")
        if not isinstance(policy, dict):
            errors.append(f"{name}: missing OpenAI policy")
        else:
            if policy.get("installation") not in (
                "AVAILABLE",
                "INSTALLED_BY_DEFAULT",
                "NOT_AVAILABLE",
            ):
                errors.append(f"{name}: invalid installation policy")
            if policy.get("authentication") not in ("ON_INSTALL", "ON_USE"):
                errors.append(f"{name}: invalid authentication policy")

    try:
        bundled = (
            {path.name for path in (root / "plugins").iterdir() if path.is_dir()}
            if (root / "plugins").is_dir()
            else set()
        )
    except OSError as exc:
        errors.append(f"Cannot list bundled plugins: {exc}")
        bundled = set()

    if bundled != set(local_roots):
        errors.append("Bundled plugin directories must match the catalog entries")

    for name, plugin_root in local_roots.items():
        try:
            if not plugin_root.is_dir():
                errors.append(f"{name}: missing bundled plugin directory")
                continue
            if any(path.is_symlink() for path in plugin_root.rglob("*")):
                errors.append(f"{name}: bundled package must not contain symlinks")
                continue
            cmanifest = load(plugin_root / ".claude-plugin/plugin.json")
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
            continue

        errors.extend(f"{name}: {error}" for error in validate_package(plugin_root))
        if cmanifest.get("name") != name:
            errors.append(f"{name}: catalog and package disagree on name")

        # Checks specific to one plugin live in its own scripts/validate.py.
        validator = plugin_root / "scripts/validate.py"
        if not validator.is_file():
            continue

        try:
            result = subprocess.run(
                [sys.executable, str(validator), str(plugin_root)],
                capture_output=True,
                text=True,
                check=False,
            )
        except (OSError, UnicodeError) as exc:
            errors.append(f"{name}: cannot run plugin validator: {exc}")
            continue

        if result.returncode:
            errors.append(
                f"{name}: plugin-specific validation failed\n{result.stdout}{result.stderr}"
            )

    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: catalogs, package manifests, and skills agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
