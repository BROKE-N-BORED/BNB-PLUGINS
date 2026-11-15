# Gist

**Kind:** plugin · **ID:** `gist` · **Tools:** 4 (all read-only, no approval needed)

Context awareness for AI use. An AI calls it before acting on
something it hasn't seen yet, and gets a short, honest,
deterministic gist - what it is, how big, what's in it, what's
stale. No model calls, no network, stdlib only. The value is a $0
context snapshot, not a summary the model could write itself.

## Tools

- `gist_file` - gist of a file: what it is (title / first heading),
  lines + size, key sections (headings), TODO/FIXME/OPEN markers
  with line numbers, last modified. Missing path or empty file: says
  so plainly, never invents.
- `gist_folder` - gist of a folder: file/dir counts by type, README
  gist if one exists, newest + oldest files, what looks stale
  (untouched in 90+ days - the threshold is stated in the output).
- `gist_repo` - gist of a git repo: current branch, head commit
  (short SHA + date + one-line message), uncommitted change count,
  last 5 commits one line each, README gist. Not a git repo: says so
  plainly.
- `gist_text` - gist of pasted text: first lines, headings, and
  deterministically extractable lines (TODO/DONE/OPEN/DECISION/FLAG
  markers) - and says plainly what it could NOT determine. Never
  invents a summary the text doesn't support.

## Honesty rules

- A gist is SHORT: output is capped at 40 lines. When the cap cuts
  something, the last line names how many lines were cut and which
  sections they came from.
- A gist never invents content. When it cannot determine something,
  it says "couldn't determine".
- A gist never claims a file's purpose beyond what its name and
  headings say.
- Binary files are reported as binary (size + modified date only) -
  no headings or markers are guessed from them.
- `gist_folder` skips `.git`, `__pycache__`, `node_modules`, `.venv`
  and similar generated dirs (not counted); the output names them
  when any were skipped. The walk stops after 5,000 entries, and
  says so if it does.
- `gist_file` reads at most the first 1 MB / 5,000 lines of a file,
  and says so when the file runs past that.

## Access

Read-only local reads: files and folders under the given path, and
git commands (`rev-parse`, `log`, `status`) run inside the given
repo. No network, no model calls, no writes, no config keys. Relative
paths resolve against the Forge workspace; absolute paths are used
as given.

## Dependencies

Standard library only (`os`, `re`, `subprocess`, `datetime`). No
Forge-side module needed beyond the loader. Nothing external to
install. `gist_repo` needs the `git` binary on PATH; without it, it
says so plainly instead of failing.

## New plugin - starts disabled

Per the loader's security model (PLUGIN-SPEC.md §4), a plugin that
is not one of the bundled seven starts DISABLED on first load - its
code never runs until the owner enables it in Customize → Plugins.

## Tests

`tests/test_gist.py` - stdlib `unittest`, no network. Run it from
this folder:

```
python3 -m unittest discover -s tests -v
```

It proves each verb on fixtures (a sample file, a sample folder, a
git repo built with `git init` + commits, sample text) including the
honest-failure cases: missing path, empty file, binary file,
not-a-repo, text with no markers. The loader ignores the `tests/`
folder (PLUGIN-SPEC.md §1 - extra files in a plugin folder are
ignored).

## Source

Built for BNB-PLUGINS 2026-11-15 (Delta 6) - a new plugin written
for this repo, not a verbatim copy from the Code Forge tree.
Ordered by Joshua 2026-11-15 ~12:18, right after he corrected the
S77 trim cycle to its gist: "Create a plugin tool omnipresent or
whatever it would be called for GIST for context awareness... I
think that would be extremely helpful to have something like that
for ai to use."

**Name note:** Joshua floated "omnipresent" as a possible name. It
was built as `gist` - the name says what it does. If he wants the
other name, the folder, `plugin.json` id/name, and this README are
the only three things to rename (the tool names stay the same).
