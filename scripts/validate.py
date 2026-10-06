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
        if not isinstance(path, str) or not path.startswith("./") or ".." in Path(path).parts:
            raise ValueError("local source must stay inside the marketplace root")
        return ("local", path)
    if kind == "github":
        repo = source.get("repo")
        if not isinstance(repo, str) or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
            raise ValueError("github source requires owner/repo")
        url = f"https://github.com/{repo}"
    elif kind == "url":
        url = source.get("url")
        if not isinstance(url, str) or not re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?", url):
            raise ValueError("expected an HTTPS GitHub source without credentials")
        url = url.removesuffix(".git")
    elif kind == "git-subdir":
        url, path = source.get("url"), source.get("path")
        if not isinstance(url, str) or not re.fullmatch(r"https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?", url):
            raise ValueError("expected an HTTPS GitHub source without credentials")
        if not isinstance(path, str) or not path or path.startswith("/") or ".." in Path(path).parts:
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
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise ValueError("plugin names must be lowercase kebab-case")
        if name in result:
            raise ValueError(f"duplicate plugin: {name}")
        result[name] = entry
    return result


def validate(root):
    errors = []
    try:
        claude, codex = (load(root / path) for path in CATALOGS)
        cplugins, xplugins = entries(claude), entries(codex)
    except (OSError, UnicodeError, ValueError) as exc:
        return [str(exc)]
    if claude.get("name") != codex.get("name") or claude.get("name") != "danielh-official-plugins":
        errors.append("Both catalogs must retain marketplace name danielh-official-plugins")
    if not isinstance(claude.get("owner"), dict) or not claude["owner"].get("name"):
        errors.append("Claude catalog requires owner.name")
    if set(cplugins) != set(xplugins):
        errors.append("Catalogs list different plugins")

    local_roots = {}
    for name in sorted(set(cplugins) & set(xplugins)):
        cplugin, xplugin = cplugins[name], xplugins[name]
        try:
            csource, xsource = source_key(cplugin.get("source")), source_key(xplugin.get("source"))
            if csource != xsource:
                errors.append(f"{name}: catalogs point at different sources or revisions")
            if csource[0] == "local":
                plugin_root = (root / csource[1]).resolve()
                if not plugin_root.is_relative_to(root.resolve()):
                    errors.append(f"{name}: local source must stay inside the marketplace root")
                elif csource[1] != f"./plugins/{name}":
                    errors.append(f"{name}: local source must be ./plugins/{name}")
                else:
                    local_roots[name] = plugin_root
        except (OSError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
        for field in ("version", "description"):
            if field in cplugin:
                errors.append(f"{name}: Claude catalog must not duplicate manifest {field}")
        if "description" in xplugin:
            errors.append(f"{name}: OpenAI catalog must not duplicate manifest description")
        if str(cplugin.get("category", "")).lower() != str(xplugin.get("category", "")).lower():
            errors.append(f"{name}: categories disagree")
        policy = xplugin.get("policy")
        if not isinstance(policy, dict):
            errors.append(f"{name}: missing OpenAI policy")
        else:
            if policy.get("installation") not in ("AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"):
                errors.append(f"{name}: invalid installation policy")
            if policy.get("authentication") not in ("ON_INSTALL", "ON_USE"):
                errors.append(f"{name}: invalid authentication policy")

    try:
        bundled = {
            path.name for path in (root / "plugins").iterdir()
            if path.is_dir()
        } if (root / "plugins").is_dir() else set()
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
            xmanifest = load(plugin_root / "plugin.json")
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
            continue

        for field in ("name", "version", "description"):
            if cmanifest.get(field) != xmanifest.get(field):
                errors.append(f"{name}: plugin manifests disagree on {field}")
        if xmanifest.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
            errors.append(f"{name}: portable manifest requires the Agent Plugins 1.0.0 schema")
        if cmanifest.get("name") != name:
            errors.append(f"{name}: catalog and package disagree on name")

        validator = plugin_root / "scripts/validate.py"
        if not validator.is_file():
            errors.append(f"{name}: missing package validator")
            continue

        try:
            result = subprocess.run(
                [sys.executable, str(validator), str(plugin_root)],
                capture_output=True, text=True, check=False,
            )
        except (OSError, UnicodeError) as exc:
            errors.append(f"{name}: cannot run package validator: {exc}")
            continue

        if result.returncode:
            errors.append(f"{name}: package validation failed\n{result.stdout}{result.stderr}")

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
