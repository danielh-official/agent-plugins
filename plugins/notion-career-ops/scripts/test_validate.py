import tempfile
import unittest
from pathlib import Path

from validate import validate


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def add_skill(self, name):
        skill = self.root / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")

    def test_exactly_one_skill(self):
        self.assertTrue(any("exactly one" in error for error in validate(self.root)))
        self.add_skill("example")
        self.assertEqual(validate(self.root), [])
        self.add_skill("extra")
        self.assertTrue(any("exactly one" in error for error in validate(self.root)))

    def test_this_plugin(self):
        self.assertEqual(validate(Path(__file__).resolve().parent.parent), [])


if __name__ == "__main__":
    unittest.main()
