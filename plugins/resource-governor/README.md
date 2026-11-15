# Resource Governor

**Kind:** plugin · **ID:** `resource-governor` · **Tools:** 1 (`check_resources`, no approval needed)

getcompute as a tool: measures RAM / CPU / Ollama and rules on whether a
model fits before it is loaded. This is the plugin Joshua himself
corrected into being a plugin, not a skill — a skill is read and
followed, this is code the shell runs.

## What it does

`check_resources` (optional `model` tag, e.g.
`maternion/minicpm5-heretic:2b` — omit it to check the selected model)
returns a bench line — free/total RAM, CPU load and thread count,
which models Ollama currently has loaded — plus a fit verdict for the
named model when one is given.

## Access

Reads `/proc` and Ollama's local status API. No writes. No config keys.

## Dependencies

The handler is a 19-line shell over `forge.governor` (the getcompute
logic) — it only runs inside a Forge install, where that module
already exists. Nothing external to install.

## Source

Verbatim copy of `plugins/resource-governor/` from the Code Forge
tree (`~/workspace/code-forge-v2/Linux Forge Agent/`, the shared tree
— identical in the publish staging and the newest build trees, checked
2026-11-15). `plugin.json` and `plugin.py` are byte-identical to the
tree; this README is the only added file.
