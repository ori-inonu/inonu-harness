"""Structural checks for the Claude Code plugin package. No Claude CLI is needed."""

import json
import re
import tempfile
import tomllib
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from urllib.parse import urlsplit

from inonu_harness import __version__
from inonu_harness.host_profiles import _source_skill, main as profiles_main, render_runner_command


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / ".claude-plugin"
SKILL = REPO_ROOT / "skills" / "inonu-harness" / "SKILL.md"
PLACEHOLDER = "${CLAUDE_PLUGIN_ROOT}"
RUNNER_TOKEN = 'python "${CLAUDE_PLUGIN_ROOT}/scripts/inonu.py"'
MANIFEST_KEYS = {"name", "version", "description", "author", "homepage", "repository", "keywords"}  # R1: no license, no components
AGENT_KEYS = {"name", "description", "model"}
SKILL_KEYS = {"name", "description"}
RESERVED_PREFIXES = ("claude-", "anthropic-", "anthropics-", "cc-plugin-")
RESERVED_NAMES = {"claude", "anthropic", "anthropics", "claude-code", "claude-mods"}
MARKETPLACE_RESERVED_WORDS = {"npm", "pip", "uv", "cargo", "github", "gh"}
KEBAB_CASE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    keys = [key for key, _ in pairs]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise ValueError(f"duplicate JSON keys: {duplicates}")
    return dict(pairs)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)


def pairs_official_with_vendor(name: str) -> bool:
    """Documented error: a name that places `official` beside `claude` or `anthropic`."""
    words = set(re.split(r"[^a-z0-9]+", name.lower()))
    return "official" in words and bool(words & {"claude", "anthropic", "anthropics"})


def is_reserved(name: str, marketplace: bool = False) -> bool:
    """Rules from research-verify.md: reserved prefixes and exact names; marketplace-only words."""
    if name in RESERVED_NAMES or name.startswith(RESERVED_PREFIXES) or pairs_official_with_vendor(name):
        return True
    return marketplace and name in MARKETPLACE_RESERVED_WORDS


def frontmatter(text: str) -> dict[str, str]:
    """Standard-library reader for flat `key: value` frontmatter; anything else is an error."""
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("missing frontmatter")
    values: dict[str, str] = {}
    for line in lines[1:lines.index("---", 1)]:
        key, separator, value = line.partition(":")
        if not separator or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key) or not value.strip():
            raise ValueError(f"unsupported frontmatter line: {line!r}")
        if key in values:
            raise ValueError(f"duplicate frontmatter key: {key}")
        values[key] = value.strip()
    return values


def body_after_frontmatter(text: str) -> str:
    lines = text.splitlines()
    return "\n".join(lines[lines.index("---", 1) + 1:])


class PluginStructureTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_json(PLUGIN_DIR / "plugin.json")
        self.marketplace = load_json(PLUGIN_DIR / "marketplace.json")
        self.skill = (REPO_ROOT / "skills" / "inonu-harness" / "SKILL.md").read_text(encoding="utf-8")
        self.agent = (REPO_ROOT / "agents" / "inonu-worker.md").read_text(encoding="utf-8")

    def test_duplicate_keys_are_rejected_and_manifests_parse(self):
        with self.assertRaises(ValueError):
            json.loads('{"name": "a", "name": "b"}', object_pairs_hook=reject_duplicate_keys)
        self.assertEqual("inonu-harness", self.manifest["name"])
        self.assertEqual("inonu-harness", self.marketplace["name"])

    def test_plugin_and_marketplace_names_are_kebab_case_and_not_reserved(self):
        self.assertIsNotNone(KEBAB_CASE.fullmatch(self.manifest["name"]))
        self.assertFalse(is_reserved(self.manifest["name"]))
        self.assertIsNotNone(KEBAB_CASE.fullmatch(self.marketplace["name"]))
        self.assertFalse(is_reserved(self.marketplace["name"], marketplace=True))

    def test_reserved_rules_reject_documented_examples(self):
        for name in ("claude-helper", "anthropic-tools", "anthropics-x", "cc-plugin-x", "official-claude-tools", *RESERVED_NAMES):
            self.assertTrue(is_reserved(name), name)
        for word in MARKETPLACE_RESERVED_WORDS:
            self.assertTrue(is_reserved(word, marketplace=True), word)

    def test_only_documented_manifest_keys_appear(self):
        self.assertLessEqual(set(self.manifest), MANIFEST_KEYS)
        self.assertNotIn("license", self.manifest)
        self.assertEqual({"name": "Inonu Harness"}, self.manifest["author"])
        self.assertTrue(self.manifest["description"])
        self.assertTrue(all(isinstance(word, str) and word for word in self.manifest["keywords"]))

    def test_version_matches_package_and_pyproject(self):
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(__version__, self.manifest["version"])
        self.assertEqual(__version__, pyproject["project"]["version"])

    def test_homepage_and_repository_are_https_urls(self):
        for key in ("homepage", "repository"):
            parts = urlsplit(self.manifest[key])
            self.assertEqual("https", parts.scheme, key)
            self.assertTrue(parts.netloc, key)

    def test_marketplace_has_a_top_level_description(self):
        self.assertIsInstance(self.marketplace.get("description"), str)
        self.assertTrue(self.marketplace["description"].strip())

    def test_skill_documentation_links_resolve_inside_the_plugin_root(self):
        skill = SKILL.read_text(encoding="utf-8")
        targets = re.findall(r"\]\((\.\./\.\./docs/[^)#]+)", skill)
        self.assertIn("../../docs/plugin.md", targets, "the skill must point to the plugin reference")
        for target in targets:
            self.assertTrue((SKILL.parent / target).resolve().is_file(), target)
            self.assertTrue((SKILL.parent / target).resolve().is_relative_to(REPO_ROOT), target)

    def test_marketplace_entry_points_at_repository_root(self):
        self.assertEqual({"name": "Inonu Harness"}, self.marketplace["owner"])
        self.assertEqual(1, len(self.marketplace["plugins"]))
        entry = self.marketplace["plugins"][0]
        self.assertEqual(self.manifest["name"], entry["name"])
        self.assertEqual("./", entry["source"])
        self.assertNotIn("version", entry)
        self.assertTrue(entry["description"])
        source = Path(entry["source"])
        self.assertNotIn("..", source.parts)
        self.assertEqual(REPO_ROOT.resolve(), (REPO_ROOT / source).resolve())

    def test_components_outside_the_plugin_are_absent(self):
        for name in (".mcp.json", "hooks", "commands", "bin"):
            self.assertFalse((REPO_ROOT / name).exists(), name)

    def test_plugin_root_carries_runner_and_package(self):
        self.assertTrue((REPO_ROOT / "scripts" / "inonu.py").is_file())
        self.assertTrue((REPO_ROOT / "inonu_harness" / "__init__.py").is_file())

    def test_skill_frontmatter_uses_allowed_fields_only(self):
        values = frontmatter(self.skill)
        self.assertLessEqual(set(values), SKILL_KEYS)
        self.assertEqual("inonu-harness", values["name"])
        self.assertTrue(values["description"])

    def test_worker_agent_frontmatter_uses_allowed_fields_and_haiku(self):
        values = frontmatter(self.agent)
        self.assertEqual(AGENT_KEYS, set(values))
        self.assertEqual("inonu-worker", values["name"])
        self.assertEqual("haiku", values["model"])

    def test_worker_agent_body_names_no_runner_path(self):
        body = body_after_frontmatter(self.agent)
        self.assertNotIn("inonu.py", body)
        self.assertNotIn(PLACEHOLDER, body)

    def test_skill_body_uses_placeholder_and_no_bare_runner(self):
        self.assertIn(RUNNER_TOKEN, self.skill)
        self.assertNotIn("python scripts/inonu.py", self.skill)
        self.assertEqual(self.skill.count("scripts/inonu.py"), self.skill.count(RUNNER_TOKEN))

    def test_frontmatter_reader_rejects_duplicate_and_malformed_lines(self):
        with self.assertRaises(ValueError):
            frontmatter("---\nname: a\nname: b\n---\n")
        with self.assertRaises(ValueError):
            frontmatter("---\nnot a pair\n---\n")

    def test_rendered_skill_has_runner_command_and_no_placeholder_for_both_hosts(self):
        runner = (REPO_ROOT / "scripts" / "inonu.py").resolve()
        for host in ("codex", "claude"):
            rendered = _source_skill(REPO_ROOT, host).decode("utf-8")
            self.assertNotIn(PLACEHOLDER, rendered, host)
            self.assertIn(render_runner_command(runner, host, "check"), rendered, host)

    def test_installed_skills_have_no_placeholder_for_both_hosts(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with redirect_stdout(StringIO()):
                self.assertEqual(0, profiles_main(["--home", str(home), "--apply"]))
            for parent in (".agents", ".claude"):
                installed = (home / parent / "skills" / "inonu-harness" / "SKILL.md").read_text(encoding="utf-8")
                self.assertNotIn(PLACEHOLDER, installed, parent)
                self.assertNotIn("python scripts/inonu.py", installed, parent)


if __name__ == "__main__":
    unittest.main()
