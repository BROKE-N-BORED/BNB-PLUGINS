# Tester Seat

**Kind:** plugin · **ID:** `tester` · **Tools:** 1 (`run_tester`, approval required)

Note 9: hands work to a second AI that runs and stress-tests it in the
workspace before the result is shipped. The driver builds; the tester
verifies — use after building, before reporting done.

## What it does

`run_tester` takes a concrete test task (e.g. "Run python3 -m unittest
in tests/ and report any failure verbatim"). The tester model runs a
second local model session with file/command tools inside the active
workspace, contained, and returns a PASS/FAIL report with evidence.

The `model` argument is **ignored by design**: the tester model is
chosen in Agent settings only — the driver does not pick who tests it
(the governing-seat rule). The tester's cycle cap comes from the
owner's `tester_max_cycles` setting, and Light Machine mode
(`light_machine`) makes its generations run with keep-alive 0 and
single residency.

## Access

Runs a second local model session with file/command tools inside the
active workspace. Approval-gated — the owner approves each delegation
at the gate before it runs.

## Dependencies

Imports `forge.ollama_client`, `forge.tools`, `forge.handoff`,
`forge.seats`, and `forge.lightmachine` — it only runs inside a Forge
install, where those modules already exist. Needs a local Ollama with
a tester model configured. Nothing external to install.

## Source

Verbatim copy of `plugins/tester/` from the Code Forge tree
(`~/workspace/code-forge-v2/Linux Forge Agent/`, the shared tree —
identical in the publish staging and the newest build trees, checked
2026-11-15). `plugin.json` and `plugin.py` are byte-identical to the
tree; this README is the only added file.
