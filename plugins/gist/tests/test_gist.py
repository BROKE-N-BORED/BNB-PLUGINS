"""Suite for the gist plugin - stdlib unittest, no network.

Run from the plugin folder:
    python3 -m unittest discover -s tests -v

Every test builds its own fixtures in a temp dir; nothing here
depends on the workspace, the Forge tree, or the network. The git
fixture is built with `git init` + real commits.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PLUGIN_DIR)

import plugin  # noqa: E402


class FakeCtx:
    """Minimal stand-in for the loader's per-plugin context view."""

    def __init__(self, workspace=None):
        self.workspace = workspace
        self.config = {}


def write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, text=True)


class ManifestTests(unittest.TestCase):
    """The loader contract: declared tools == HANDLERS."""

    def test_manifest_parses_and_matches_handlers(self):
        with open(os.path.join(PLUGIN_DIR, "plugin.json")) as fh:
            manifest = json.load(fh)
        declared = {t["name"] for t in manifest["tools"]}
        self.assertEqual(declared, set(plugin.HANDLERS))
        for name, handler in plugin.HANDLERS.items():
            self.assertTrue(callable(handler), name)

    def test_all_tools_read_class_no_approval(self):
        with open(os.path.join(PLUGIN_DIR, "plugin.json")) as fh:
            manifest = json.load(fh)
        for tool in manifest["tools"]:
            self.assertIs(tool["requires_approval"], False, tool["name"])

    def test_no_config_keys(self):
        with open(os.path.join(PLUGIN_DIR, "plugin.json")) as fh:
            manifest = json.load(fh)
        self.assertEqual(manifest.get("config_keys", []), [])


class GistFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ctx = FakeCtx(workspace=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_file_gist(self):
        path = os.path.join(self.tmp.name, "notes.md")
        write(path, "# Project Notes\n\nSome intro text.\n\n"
                    "## Setup\n\nDo the thing.\n\n"
                    "## Risks\n\nTODO: check the battery.\n"
                    "FIXME: the latch sticks.\n")
        out = plugin.gist_file({"path": path}, self.ctx)
        self.assertIn("Title: Project Notes", out)
        self.assertIn("Lines: 12", out)
        self.assertIn("line 5: Setup", out)
        self.assertIn("line 9: Risks", out)
        self.assertIn("line 11 [TODO]", out)
        self.assertIn("line 12 [FIXME]", out)
        self.assertIn("modified", out)
        self.assertLessEqual(len(out.splitlines()), plugin.MAX_LINES)

    def test_file_gist_relative_to_workspace(self):
        write(os.path.join(self.tmp.name, "a.txt"), "hello\n")
        out = plugin.gist_file({"path": "a.txt"}, self.ctx)
        self.assertIn("File: a.txt", out)
        self.assertIn("First line: hello", out)

    def test_file_gist_python_sections(self):
        path = os.path.join(self.tmp.name, "mod.py")
        write(path, '"""A module."""\n\n\ndef first():\n    pass\n\n\n'
                    'class Widget:\n    pass\n')
        out = plugin.gist_file({"path": path}, self.ctx)
        self.assertIn("line 4: def first()", out)
        self.assertIn("line 8: class Widget", out)

    def test_missing_path(self):
        out = plugin.gist_file(
            {"path": os.path.join(self.tmp.name, "nope.md")}, self.ctx)
        self.assertIn("No such file", out)

    def test_empty_file(self):
        path = os.path.join(self.tmp.name, "empty.txt")
        write(path, "")
        out = plugin.gist_file({"path": path}, self.ctx)
        self.assertIn("The file is empty", out)

    def test_directory_given(self):
        out = plugin.gist_file({"path": self.tmp.name}, self.ctx)
        self.assertIn("That's a folder", out)
        self.assertIn("gist_folder", out)

    def test_binary_file(self):
        path = os.path.join(self.tmp.name, "blob.bin")
        with open(path, "wb") as fh:
            fh.write(b"\x00\x01\x02binary\x00data")
        out = plugin.gist_file({"path": path}, self.ctx)
        self.assertIn("binary", out)
        self.assertIn("couldn't determine", out)

    def test_no_markers_says_so(self):
        path = os.path.join(self.tmp.name, "plain.txt")
        write(path, "just some words\non two lines\n")
        out = plugin.gist_file({"path": path}, self.ctx)
        self.assertIn("no TODO/FIXME/OPEN markers found", out)
        self.assertIn("couldn't determine", out)  # no headings

    def test_many_markers_capped_with_count(self):
        path = os.path.join(self.tmp.name, "many.md")
        lines = ["# Big\n"] + [f"TODO: item {i}\n" for i in range(100)]
        write(path, "".join(lines))
        out = plugin.gist_file({"path": path}, self.ctx)
        out_lines = out.splitlines()
        self.assertLessEqual(len(out_lines), plugin.MAX_LINES)
        self.assertIn("... and 90 more marker(s)", out)

    def test_fast(self):
        path = os.path.join(self.tmp.name, "fast.md")
        write(path, "# Fast\n\n" + "text line\n" * 500)
        start = time.monotonic()
        plugin.gist_file({"path": path}, self.ctx)
        self.assertLess(time.monotonic() - start, 1.0)


class AssembleTests(unittest.TestCase):
    """The 40-line cap itself, tested directly on _assemble."""

    def test_under_cap_untouched(self):
        sections = [("a", ["one", "two"]), ("b", ["three"])]
        self.assertEqual(plugin._assemble(sections),
                         "one\ntwo\nthree")

    def test_over_cap_truncates_and_names_the_cut(self):
        sections = [("first", [f"f{i}" for i in range(20)]),
                    ("second", [f"s{i}" for i in range(20)]),
                    ("third", [f"t{i}" for i in range(20)])]
        out = plugin._assemble(sections)
        out_lines = out.splitlines()
        self.assertEqual(len(out_lines), plugin.MAX_LINES)
        self.assertIn("cut 21 more line(s)", out_lines[-1])
        self.assertIn("second", out_lines[-1])
        self.assertIn("third", out_lines[-1])
        self.assertNotIn("first", out_lines[-1])


class GistFolderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ctx = FakeCtx(workspace=self.tmp.name)
        self.root = os.path.join(self.tmp.name, "proj")
        os.mkdir(self.root)
        write(os.path.join(self.root, "README.md"),
              "# Demo Project\n\nIt demos things.\n")
        write(os.path.join(self.root, "main.py"), "print(1)\n")
        write(os.path.join(self.root, "util.py"), "x = 1\n")
        write(os.path.join(self.root, "notes.txt"), "hi\n")
        os.mkdir(os.path.join(self.root, "docs"))
        write(os.path.join(self.root, "docs", "guide.md"), "# Guide\n")
        # One genuinely stale file: untouched 100 days ago.
        stale = os.path.join(self.root, "old.log")
        write(stale, "old\n")
        old = time.time() - 100 * 86400
        os.utime(stale, (old, old))

    def tearDown(self):
        self.tmp.cleanup()

    def test_folder_gist(self):
        out = plugin.gist_folder({"path": self.root}, self.ctx)
        self.assertIn("Files: 6", out)
        self.assertIn(".py: 2", out)
        self.assertIn(".md: 2", out)
        self.assertIn("Title: Demo Project", out)
        self.assertIn("Stale (untouched 90+ days): 1 file(s)", out)
        self.assertIn("old.log", out)
        self.assertIn("Newest:", out)
        self.assertIn("Oldest:", out)
        self.assertLessEqual(len(out.splitlines()), plugin.MAX_LINES)

    def test_missing_folder(self):
        out = plugin.gist_folder(
            {"path": os.path.join(self.tmp.name, "nope")}, self.ctx)
        self.assertIn("No such folder", out)

    def test_file_given(self):
        out = plugin.gist_folder(
            {"path": os.path.join(self.root, "main.py")}, self.ctx)
        self.assertIn("That's a file", out)
        self.assertIn("gist_file", out)

    def test_no_readme_and_nothing_stale(self):
        bare = os.path.join(self.tmp.name, "bare")
        os.mkdir(bare)
        write(os.path.join(bare, "a.txt"), "x\n")
        out = plugin.gist_folder({"path": bare}, self.ctx)
        self.assertIn("README: none found", out)
        self.assertIn("Stale: nothing", out)

    def test_skipped_dirs_named(self):
        os.mkdir(os.path.join(self.root, "__pycache__"))
        write(os.path.join(self.root, "__pycache__", "m.pyc"), "x")
        out = plugin.gist_folder({"path": self.root}, self.ctx)
        self.assertIn("Skipped (not counted): __pycache__", out)
        self.assertIn("Files: 6", out)  # the .pyc was not counted


class GistRepoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ctx = FakeCtx(workspace=self.tmp.name)
        self.repo = os.path.join(self.tmp.name, "repo")
        os.mkdir(self.repo)
        git("init", "-b", "main", cwd=self.repo)
        git("config", "user.email", "test@example.com", cwd=self.repo)
        git("config", "user.name", "Test", cwd=self.repo)
        write(os.path.join(self.repo, "README.md"),
              "# Fixture Repo\n\nA test repo.\n")
        write(os.path.join(self.repo, "a.txt"), "one\n")
        git("add", ".", cwd=self.repo)
        git("commit", "-m", "first commit", cwd=self.repo)
        write(os.path.join(self.repo, "b.txt"), "two\n")
        git("add", ".", cwd=self.repo)
        git("commit", "-m", "second commit", cwd=self.repo)
        # One uncommitted change + one untracked file.
        write(os.path.join(self.repo, "a.txt"), "one changed\n")
        write(os.path.join(self.repo, "untracked.txt"), "new\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_repo_gist(self):
        out = plugin.gist_repo({"path": self.repo}, self.ctx)
        self.assertIn("Branch: main", out)
        self.assertIn("second commit", out)
        self.assertIn("first commit", out)
        self.assertIn("Uncommitted: 2 change(s)", out)
        self.assertIn("1 unstaged", out)
        self.assertIn("1 untracked", out)
        self.assertIn("Title: Fixture Repo", out)
        self.assertLessEqual(len(out.splitlines()), plugin.MAX_LINES)

    def test_repo_gist_default_path_is_workspace(self):
        ctx = FakeCtx(workspace=self.repo)
        out = plugin.gist_repo({}, ctx)
        self.assertIn("Branch: main", out)

    def test_not_a_repo(self):
        plain = os.path.join(self.tmp.name, "plain")
        os.mkdir(plain)
        out = plugin.gist_repo({"path": plain}, self.ctx)
        self.assertIn("Not a git repo", out)

    def test_empty_repo_no_history(self):
        empty = os.path.join(self.tmp.name, "empty")
        os.mkdir(empty)
        git("init", "-b", "main", cwd=empty)
        out = plugin.gist_repo({"path": empty}, self.ctx)
        self.assertIn("No commits yet", out)


class GistTextTests(unittest.TestCase):
    def setUp(self):
        self.ctx = FakeCtx()

    def test_text_gist(self):
        text = ("# Meeting notes\n\nWe talked about the launch.\n\n"
                "## Decisions\n\nDECISION: ship on Friday.\n"
                "TODO: tell the team.\nDONE: book the room.\n")
        out = plugin.gist_text({"text": text}, self.ctx)
        self.assertIn("9 line(s)", out)
        self.assertIn("line 1: Meeting notes", out)
        self.assertIn("line 7 [DECISION]", out)
        self.assertIn("line 8 [TODO]", out)
        self.assertIn("line 9 [DONE]", out)
        self.assertNotIn("Could not determine", out)

    def test_text_no_markers_no_headings(self):
        out = plugin.gist_text(
            {"text": "just a few words\nand another line\n"}, self.ctx)
        self.assertIn("Could not determine", out)
        self.assertIn("sections (no headings in the text)", out)
        self.assertIn("marked items", out)
        self.assertIn("does not summarize or interpret", out)

    def test_text_empty(self):
        out = plugin.gist_text({"text": "   \n"}, self.ctx)
        self.assertIn("The text is empty", out)

    def test_text_missing_arg(self):
        out = plugin.gist_text({}, self.ctx)
        self.assertIn("No text given", out)

    def test_many_markers_capped_with_count(self):
        text = "\n".join(f"TODO: item {i}" for i in range(100))
        out = plugin.gist_text({"text": text}, self.ctx)
        out_lines = out.splitlines()
        self.assertLessEqual(len(out_lines), plugin.MAX_LINES)
        self.assertIn("... and 90 more marker(s)", out)


class NoArgTests(unittest.TestCase):
    def test_missing_path_arg(self):
        self.assertIn("No path given",
                      plugin.gist_file({}, FakeCtx()))
        self.assertIn("No path given",
                      plugin.gist_folder({}, FakeCtx()))


if __name__ == "__main__":
    unittest.main()
