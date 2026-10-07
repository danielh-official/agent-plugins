import json
import tempfile
import unittest
from pathlib import Path

from validate import validate


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = {
            "name": "example-skill",
            "version": "1.0.0",
            "description": "An example skill.",
            "skills": "./skills/",
        }
        self.write(".claude-plugin/plugin.json", self.manifest)
        self.portable = {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            **{
                field: self.manifest[field]
                for field in ("name", "version", "description")
            },
            "extensions": {
                "com.openai": {
                    "interface": {
                        "displayName": "Example",
                        "shortDescription": "Example skill metadata",
                        "defaultPrompt": ["x" * 128] * 3,
                    },
                },
            },
        }
        self.write("plugin.json", self.portable)
        self.skill = self.root / "skills/example-skill"
        (self.skill / "agents").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text(
            "---\nname: example-skill\ndescription: An example skill.\n---\nInstructions.\n",
            encoding="utf-8",
        )
        self.metadata = self.skill / "agents/openai.yaml"
        self.metadata.write_text(
            'interface:\n  display_name: "Example"\n'
            '  short_description: "An example skill for testing."\n'
            '  default_prompt: "Use $example-skill."\n',
            encoding="utf-8",
        )

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_valid_at_prompt_limits(self):
        self.assertEqual(validate(self.root), [])

    def test_manifest_drift(self):
        for field in ("name", "version", "description"):
            with self.subTest(field=field):
                self.write("plugin.json", {**self.portable, field: "different"})
                self.assertTrue(any(field in error for error in validate(self.root)))

    def test_prompt_limits(self):
        for prompts in ([], ["x"] * 4, ["x" * 129], [""], [3], [" "]):
            with self.subTest(prompts=prompts):
                self.portable["extensions"]["com.openai"]["interface"][
                    "defaultPrompt"
                ] = prompts
                self.write("plugin.json", self.portable)
                self.assertTrue(
                    any("defaultPrompt" in error for error in validate(self.root))
                )

    def test_missing_and_empty_metadata(self):
        for value in ('""', "''", '"   "', ""):
            with self.subTest(value=value):
                self.metadata.write_text(
                    f"interface:\n  display_name: {value}\n",
                    encoding="utf-8",
                )
                self.assertTrue(
                    any("display_name" in error for error in validate(self.root))
                )

    def test_malformed_json(self):
        self.write("plugin.json", [])
        self.assertTrue(any("JSON object" in error for error in validate(self.root)))

    def test_legacy_catalog_metadata(self):
        entry = {"name": self.manifest["name"], "source": "."}
        self.write(".claude-plugin/marketplace.json", {"plugins": [entry]})
        self.assertEqual(validate(self.root), [])
        for field in ("version", "description"):
            with self.subTest(field=field):
                self.write(
                    ".claude-plugin/marketplace.json",
                    {
                        "plugins": [{**entry, field: "duplicate"}],
                    },
                )
                self.assertTrue(
                    any("must not duplicate" in error for error in validate(self.root))
                )

    def test_no_bundled_connections(self):
        for field in ("mcpServers", "apps"):
            with self.subTest(field=field):
                self.write("plugin.json", {**self.portable, field: {}})
                self.assertTrue(
                    any("must not bundle" in error for error in validate(self.root))
                )

    def test_skill_name_and_required_assets(self):
        skill_file = self.skill / "SKILL.md"
        skill_file.write_text(
            "---\nname: wrong\ndescription: Example.\n---\n", encoding="utf-8"
        )
        self.assertTrue(
            any("names must agree" in error for error in validate(self.root))
        )
        skill_file.unlink()
        self.assertTrue(any("exactly one" in error for error in validate(self.root)))


if __name__ == "__main__":
    unittest.main()
