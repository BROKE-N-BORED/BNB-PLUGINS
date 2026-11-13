# BNB-PLUGINS

Code Forge plugins — the second layer after skills. A skill is read
and followed; a plugin is code the shell runs that registers real
tools. Every plugin here is either a verbatim copy of a real plugin
from the Forge tree or a verified scaffold. Nothing is invented.

## What's in here

### The bundled seven (`plugins/`)

The plugins that ship with Code Forge, copied verbatim from the tree
(`~/workspace/code-forge-v2/Linux Forge Agent/plugins/` — the shared
tree; identical in the publish staging and the newest build trees,
checked 2026-11-12). `plugin.json` and `plugin.py` are byte-identical
to the tree in every folder; each folder's README is the only added
file, and it states what the plugin does, its tools, its access, its
dependencies, and its setup.

| Plugin | Kind | Tools | In short |
|---|---|---|---|
| `resource-governor` | plugin | `check_resources` | getcompute as a tool — RAM/CPU/Ollama fit check before loading a model |
| `tester` | plugin | `run_tester` | Hands work to a second AI that runs and stress-tests it before shipping |
| `github` | connector | `github_repo_info`, `github_search_repos` | Read-only GitHub lookups |
| `huggingface` | connector | `hf_search_models`, `hf_model_info` | Hugging Face model search + repo inspection, GGUF sizes included |
| `mcp` | connector | `mcp_list_tools`, `mcp_call` | Bridges locally-run MCP servers into Forge as tools |
| `browse` | connector | 7 verbs + `verify_in_browser` | OpenCode Browse over the owner's signed-in Chromium, fenced by the project allowlist |
| `cloudstore` | connector | `cloud_list`, `cloud_read`, `cloud_download`, `cloud_upload`, `cloud_delete` | Explicit file transfers via the owner's rclone — no sync, no credentials in Forge |

### The contract (`PLUGIN-SPEC.md`)

The plugin contract as the loader actually implements it: the manifest
fields, the `HANDLERS` shape, metadata-first loading, the
disabled-until-enabled security model, the per-plugin config view,
and the `create_plugin` / `update_plugin` authoring tools — with
file/line references into the Forge tree.

### The scaffold (`templates/plugin-scaffold/`)

The smallest plugin that actually loads: one tool, `scaffold_echo`,
stdlib-only, no side effects. Copy the folder, rename it, build from
it. Verified against the real Forge loader (see below).

## Install a plugin

Copy the plugin's folder into the Forge app's `plugins/` directory
(the app's own folder, beside the shell — **not** inside a project
folder; plugins are global). Restart Forge or rescan. The plugin
appears in Customize → Plugins and **starts DISABLED** — enable it
there. Its code never runs until you do.

Notes:

- `browse` needs its sibling `mcp/` folder beside it (it imports
  `mcp_client` from there). Copy both or neither.
- Several plugins import `forge.*` modules (`resource-governor`,
  `tester`, `browse`, `cloudstore`) — they only run inside a Forge
  install, where those modules already exist. `github`,
  `huggingface`, and `mcp` are self-contained.
- Connectors that need setup (Browse, rclone, MCP servers, tokens)
  say so in their own README — setup is always the owner's, on their
  PC. Forge never installs external tools or stores cloud
  credentials.

## Author a plugin

Read `PLUGIN-SPEC.md` section 6, or start from
`templates/plugin-scaffold/`. The short version:

- Folder named with a slug (lowercase letters, digits, hyphens).
- `plugin.json` declares id, name, kind, description, access, and
  the tools (name, description, JSON-schema parameters,
  `requires_approval` — default is approval **on**).
- `plugin.py` defines `HANDLERS = {"tool_name": handler}` where each
  handler takes `(args, ctx)` and returns a string.
- Inside Forge, the agent can also build one with the `create_plugin`
  tool (same validation gate: code must compile, `HANDLERS` must be
  declared with string keys, `TOOL_SCHEMAS` must be readable) — the
  new plugin starts disabled either way.

## Verified

- All 7 plugin folders diffed byte-identical against the tree
  (`plugin.json`, `plugin.py`, `mcp/mcp_client.py`).
- All 7 copied plugins + the scaffold loaded through the **real**
  Forge loader (`forge/plugins.py::load_plugins`) from the copied
  location: 21 tools registered (browse 7, cloudstore 5, github 2,
  huggingface 2, mcp 2, resource-governor 1, tester 1, scaffold 1).
- `check_resources` called through the registry returns the bench
  line; `scaffold_echo` called with `{"text": "hello"}` returns
  `scaffold_echo: hello`.
- The tree's own `PluginTests` + `PluginLoadingAuditTests` pass
  against the tree (7/7, `python3 -m unittest
  tests.test_core.PluginTests tests.test_core.PluginLoadingAuditTests`).

## Not here

- **aura-plugins** (`BROKE-N-BORED/aura-plugins`) is a Claude Code
  plugin marketplace (`.claude-plugin` manifests; `commands/`,
  `skills/`, `hooks/`, `agents/`). It holds no Forge plugin content
  and nothing from it was copied — different system, different
  contract. Porting anything across would mean rewriting it to the
  Forge contract, not copying it.
- Skills live in `BNB-SKILLS`, not here. Roles live in `BNB-ROLES`.

## License

MIT — see the LICENSE file.
