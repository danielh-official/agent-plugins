import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validate.py"
SPEC = importlib.util.spec_from_file_location("catalog_validator", SCRIPT)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(
            validator.ROOT / "plugins",
            self.root / "plugins",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        self.claude, self.codex = (
            copy.deepcopy(validator.load(validator.ROOT / path))
            for path in validator.CATALOGS
        )
        self.save()

    def save(self):
        for path, catalog in zip(validator.CATALOGS, (self.claude, self.codex)):
            destination = self.root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(catalog), encoding="utf-8")

    def test_catalogs_valid(self):
        self.assertEqual(validator.validate(self.root), [])

    def test_external_plugin_both_catalogs(self):
        source = {
            "source": "git-subdir",
            "url": "https://github.com/example/repo.git",
            "path": "plugins/external",
        }
        self.claude["plugins"].append(
            {"name": "external", "source": source, "category": "productivity"}
        )
        self.save()
        self.assertTrue(
            any("different plugins" in error for error in validator.validate(self.root))
        )
        self.codex["plugins"].append(
            {
                "name": "external",
                "source": {**source, "path": "./plugins/external"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
                "category": "Productivity",
            }
        )
        self.save()
        self.assertEqual(validator.validate(self.root), [])

    def test_duplicate(self):
        self.claude["plugins"].append(self.claude["plugins"][0])
        self.save()
        self.assertTrue(
            any("duplicate" in error for error in validator.validate(self.root))
        )

    def test_source_drift(self):
        self.codex["plugins"][0]["source"]["path"] = "./plugins/different"
        self.save()
        self.assertTrue(
            any("different sources" in error for error in validator.validate(self.root))
        )

    def test_revision_drift(self):
        self.claude["plugins"][0]["source"] = {
            "source": "github",
            "repo": "example/plugin",
        }
        self.codex["plugins"][0]["source"] = {
            "source": "url",
            "url": "https://github.com/example/plugin.git",
        }
        self.codex["plugins"][0]["source"]["ref"] = "v2"
        self.save()
        self.assertTrue(
            any("revisions" in error for error in validator.validate(self.root))
        )

    def test_name_drift(self):
        self.codex["plugins"][0]["name"] = "different"
        self.save()
        self.assertTrue(
            any("different plugins" in error for error in validator.validate(self.root))
        )

    def test_invalid_authentication(self):
        self.codex["plugins"][0]["policy"]["authentication"] = "ON_FIRST_USE"
        self.save()
        self.assertTrue(
            any("authentication" in error for error in validator.validate(self.root))
        )

    def test_local_containment(self):
        for source in (
            "../plugin",
            "/tmp/plugin",
            {"source": "local", "path": "../plugin"},
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                validator.source_key(source)
        self.assertEqual(
            validator.source_key("./plugins/example"),
            validator.source_key({"source": "local", "path": "./plugins/example"}),
        )

    def test_package_version_change(self):
        for entry in self.claude["plugins"]:
            if not isinstance(entry["source"], str):
                continue  # external plugin, nothing bundled
            root = self.root / "plugins" / entry["name"]
            for destination in (
                root / ".claude-plugin/plugin.json",
                root / "plugin.json",
            ):
                manifest = validator.load(destination)
                manifest["version"] = "2.0.0"
                destination.write_text(json.dumps(manifest), encoding="utf-8")

        self.assertEqual(validator.validate(self.root), [])

    def test_redundant_catalog_metadata(self):
        for catalog, field in (
            (self.claude, "version"),
            (self.claude, "description"),
            (self.codex, "description"),
        ):
            with self.subTest(catalog=catalog["name"], field=field):
                catalog["plugins"][0][field] = "duplicate"
                self.save()
                self.assertTrue(
                    any(
                        "must not duplicate" in error
                        for error in validator.validate(self.root)
                    )
                )
                del catalog["plugins"][0][field]

    def test_missing_package_validator(self):
        (self.root / "plugins/notion-career-ops/scripts/validate.py").unlink()
        self.assertTrue(
            any(
                "missing package validator" in error
                for error in validator.validate(self.root)
            )
        )

    def test_malformed_catalog(self):
        (self.root / validator.CATALOGS[0]).write_text("[]", encoding="utf-8")
        self.assertTrue(
            any("JSON object" in error for error in validator.validate(self.root))
        )

    def test_bundled_version_drift(self):
        path = self.root / "plugins/notion-career-ops/.claude-plugin/plugin.json"
        manifest = validator.load(path)
        manifest["version"] = "2.0.0"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertTrue(
            any(
                "plugin manifests disagree on version" in error
                for error in validator.validate(self.root)
            )
        )

    def test_missing_bundled_package(self):
        path = self.root / "plugins/notion-career-ops/plugin.json"
        path.unlink()
        self.assertTrue(validator.validate(self.root))

    def test_unlisted_package(self):
        (self.root / "plugins/unlisted").mkdir()
        self.assertTrue(
            any(
                "directories must match" in error
                for error in validator.validate(self.root)
            )
        )

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / "escape").symlink_to(outside, target_is_directory=True)
            self.claude["plugins"][0]["source"] = "./escape"
            self.codex["plugins"][0]["source"]["path"] = "./escape"
            self.save()
            self.assertTrue(
                any("stay inside" in error for error in validator.validate(self.root))
            )

    def test_missing_plugin_directory(self):
        shutil.rmtree(self.root / "plugins/notion-career-ops")
        self.assertTrue(
            any(
                "missing bundled plugin directory" in error
                for error in validator.validate(self.root)
            )
        )

    def test_package_validation_failure(self):
        path = (
            self.root
            / "plugins/notion-career-ops/skills/notion-career-ops/agents/openai.yaml"
        )
        path.unlink()
        self.assertTrue(
            any(
                "package validation failed" in error
                for error in validator.validate(self.root)
            )
        )

    def test_package_symlink(self):
        root = self.root / "plugins/notion-career-ops"
        (root / "linked").symlink_to(root / "README.md")
        self.assertTrue(
            any(
                "must not contain symlinks" in error
                for error in validator.validate(self.root)
            )
        )


if __name__ == "__main__":
    unittest.main()
