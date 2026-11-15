# Code Forge Plugin Contract

The plugin spec as the loader **actually implements it** — every claim
below is grounded in the Code Forge tree this repo was built from
(`~/workspace/code-forge-v2/Linux Forge Agent/`, the shared tree;
line refs re-checked against that tree 2026-11-15 in the Delta 6
re-sync — several had drifted since the 2026-11-12 check, and the
drifted ones are corrected below). File/line references point at
that tree as of the re-check date — they drift as the tree moves, so
verify a ref before trusting it in a newer tree.

## 1. What a plugin is

A plugin is a **folder** under the Forge app's `plugins/` directory
with two required files (`forge/plugins.py`, module docstring):

- `plugin.json` — the declaration: id, name, kind (`"plugin"` or
  `"connector"`), a one-line description, the access it needs, and
  its tools (name, description, parameters, `requires_approval`).
- `plugin.py` — the code: defines
  `HANDLERS = {tool_name: fn(args, ctx) -> str}`.

A folder missing either file is skipped by the loader
(`forge/plugins.py:252`, `load_plugins`). Extra files in the folder
are ignored by the loader — the MCP plugin keeps its `mcp_client.py`
helper beside its `plugin.py`, and the Browse plugin imports it from
the sibling `mcp/` folder.

**Skill vs plugin:** skills are *read* — instructions the model
follows. Plugins are *run* — code the shell executes that registers
real tools (`forge/plugins.py`, module docstring). A plugin is the
second layer after skills (Note 4): a skill plus code registering new
tools, on the VS Code extension model.

**Plugin vs connector:** both are the same folder shape; `kind` is
`"connector"` when the plugin bridges an outside service (GitHub,
Hugging Face, MCP servers, Browse, rclone cloud storage) and
`"plugin"` when it is a mechanism inside Forge (Resource Governor,
Tester Seat). The loader treats both kinds identically — `kind` is
bookkeeping and UI, not behaviour.

## 2. The manifest (`plugin.json`)

Fields the loader reads (`forge/plugins.py:207-323`, `load_plugins`):

| Field | Required? | What the loader does with it |
|---|---|---|
| `id` | No (defaults to folder name) | The plugin's identity for enable/disable and known-history. |
| `name` | No (defaults to folder name) | Display name; also the source label in the tool registry. |
| `kind` | No (defaults to `"plugin"`) | `"plugin"` or `"connector"`. Display only. |
| `description` | No (defaults to `""`) | One line, shown in Customize. |
| `access` | No | Human-readable declaration of what the plugin touches. The loader does not enforce it — it is the owner's reading material before enabling. Declare it honestly. |
| `tools` | No (defaults to `[]`) | The tool list (below). A non-list value is treated as empty. Non-object entries are dropped. |
| `config_keys` | No (defaults to `[]`) | The `connectors.json` keys this plugin may see (Section 5). A non-list value is treated as empty. |
| `version` | No | Ignored by the loader. Informational only. |

Each entry in `tools`:

| Field | Required? | Behaviour |
|---|---|---|
| `name` | Yes (empty names are skipped) | The tool name the model calls. Must match a key in `HANDLERS`. |
| `description` | No (defaults to `""`) | Becomes the tool schema's description — the model's only guide to when to call it. |
| `parameters` | No (defaults to `{"type": "object", "properties": {}}`) | The JSON-schema parameters object the model sees. |
| `requires_approval` | No (defaults to `true`) | `true` = the tool passes the owner's approval gate (desktop dialog or phone deck) before its handler runs. `false` = read-class tools that run without a gate. **Default is approval on** — read-class is opt-in, per tool. |

A manifest that is unreadable or parses to a non-object **skips the
folder, is logged, and never raises** — one bad plugin cannot break
loading for the rest.

## 3. The code (`plugin.py`)

`plugin.py` must define, at the top level:

```python
HANDLERS = {"tool_name": handler_function, ...}
```

Each handler takes `(args, ctx)` and returns a **string**. `args` is
the model's arguments object for the call; `ctx` is the per-plugin
context view (Section 5).

Loader rules (`forge/plugins.py:207-323`):

- A declared tool with **no callable handler** is skipped — it never
  reaches the registry.
- A handler with **no declaration** is never registered.
- On a **tool-name collision**, the FIRST plugin (sorted folder order)
  keeps the name; the later one is logged and ignored.
- If `plugin.py` **fails to import or execute**, the plugin is logged
  and skipped (handlers stay `{}`) — loading continues for the rest.
- `HANDLERS` must be a dict; a non-dict value is treated as empty.

The tool schema the model sees is built from the **manifest**, not
from the code:

```json
{"type": "function", "function": {"name": ..., "description": ...,
 "parameters": ...}}
```

## 4. Loading: metadata-first, code runs only when enabled and known

`load_plugins` runs **two passes** (`forge/plugins.py:207-323`):

1. **Metadata pass** — every folder's `plugin.json` is read so the
   shell can list all plugins (Customize, known/disabled
   bookkeeping). No code executes in this pass.
2. **Exec pass** — `plugin.py` executes **only** for a plugin whose
   id is not in `disabled` **and** is known. A disabled or brand-new
   plugin's code never runs. Non-executed plugins are still returned
   with their declared tools and `handlers={}`; the tool registry is
   built from executed plugins only.

"Known" is the shell's stored history (`known_plugins` setting).
With no stored history, the shell seeds it from `BUNDLED_PLUGIN_IDS`
(`forge/plugins.py:49`; `forge/main.py:16676-16687`,
`_known_plugins_for_load`) — the seven ids that ship with Forge:

`browse`, `cloudstore`, `github`, `huggingface`, `mcp`,
`resource-governor`, `tester`.

So on a fresh install the bundled seven keep their historic first-run
behaviour, while **any other plugin folder that appears** (an update
zip's payload, a hand copy, anything) **starts DISABLED** instead of
having its code executed on first load. The owner enables it in
Customize → Plugins. That is the security model: new code never runs
before the owner has seen it listed and switched it on.

Enable/disable state lives in the owner's settings
(`disabled_plugins`), not in the plugin folder — copying a folder in
never enables it, and deleting a folder never leaves stale state
behind. The Customize dialog renders one checkbox per plugin
(`forge/main.py:2075-2125`, `2633-2668`).

### The C16 fingerprint gate

`load_plugins` also carries a content-fingerprint gate (C16, audit
S1-25/W2) — the loader's own trust mechanism. It watches plugin
*content*: the code about to run must still be the code the owner
trusted. (It does not watch this document — the spec's own line refs
drifted for the same reason this repo's plugin copies did: nothing
re-checked them. See the header note.)

- `plugin_fingerprint(folder)` (`forge/plugins.py:184-205`): sha256
  over `plugin.json` + `plugin.py`, each file's bytes prefixed by its
  name so the two files cannot trade contents unnoticed. Returns
  `None` when either file is missing or unreadable — unverifiable
  content never counts as matching.
- The fingerprint is recorded at trust time: the first load of an
  enabled plugin records its current content as the baseline in
  place (the enable decision IS the trust decision), or re-enable
  in Customize via `_record_plugin_fingerprint`
  (`forge/main.py:16744`), which also clears any fingerprint-changed
  notice for it. Recording is a no-op during self-maintenance —
  the work copy's content must never become the live baseline.
- At every load, a plugin about to execute is fingerprinted first
  (`forge/plugins.py:275-288`): no recorded fingerprint means
  first sight (the baseline is recorded); a changed fingerprint —
  or unreadable content — means disk replacement under an old trust
  decision: the pid goes on `fingerprint_changes` and the code
  does NOT execute. When `fingerprints` is `None` the gate is off
  and the load is exactly as before.
- The caller is `_load_plugins_with_fingerprints`
  (`forge/main.py:16703-16742`), the single plugin load path
  (startup + rescan): it persists baselines to the
  `plugin_fingerprints` setting, and on a change it returns the
  plugin to DISABLED, records it in
  `fingerprint_changed_plugins`, writes the event log, and
  Customize shows a notice ("Changed on disk since you enabled
  them. Left OFF until you re-enable them here",
  `forge/main.py:2115-2125`). The owner re-enables it after
  reviewing the new code — that re-enable is the new trust
  decision.

## 5. The context view and config

Handlers receive a **per-plugin view** over the live `PluginContext`
(`forge/plugins.py:61-89`, `125-181`):

- Attribute reads delegate to the live context, so shell-side updates
  (workspace, current model, log, cancel event) flow through as they
  happen.
- `config` is **filtered**: at call time it returns exactly the
  `connectors.json` keys named in the plugin's `config_keys` manifest
  list. A plugin that declares no `config_keys` sees an empty config.
- Secret keys a plugin declares (the `SECRET_CONFIG_KEYS` list in
  `forge/vault.py:60`) resolve from the **encrypted vault**, which
  wins over any stale file value. Only declared keys are ever looked
  up: a plugin that does not declare a secret never receives it.
- The vault lookup is fail-soft — a vault problem leaves the file
  values in place.

`PluginContext` fields a handler can read: `workspace`, `base_url`
(Ollama, default `http://127.0.0.1:11434`), `current_model`,
`tester_model`, `tester_max_cycles`, `research_web_engine`,
`forge_browser_engine`, `light_machine`, `governing_roster`,
`config`, `log` (callable or None), `cancel_event` (the live turn's
`threading.Event` — check it in long loops so Stop works).

Connector auth lives in the app config (`connectors.json` in the app
data dir, loaded by `load_connector_config`,
`forge/plugins.py:326-330`) — never in project files or prompts.
Parallel turns dispatch plugin tools under `scoped_ctx`
(`forge/plugins.py:102-112`), so each turn's handlers see that turn's
own context snapshot.

## 6. Authoring: `create_plugin` / `update_plugin`

The agent-side authoring tools live in `forge/create_ext.py`. They
write **only** under the app's own `plugins/` directory (resolved-path
check included) — plugins are global, available in every project, not
inside the current project folder.

**`create_plugin`** (`forge/create_ext.py:369-414`):

- Name must be a slug: lowercase letters, digits, hyphens only
  (`SLUG_RE`, line 45; `validate_slug`, line 159). Path separators
  are refused.
- Refuses a name that already exists (update instead).
- The code must **compile**, must declare top-level
  `HANDLERS = {...}` with **string keys** (read by AST — the code is
  never executed at creation time; `declared_tools`, line 266), and
  any top-level `TOOL_SCHEMAS` declaration must be readable as a
  plain dict literal mapping tool names to dicts (`declared_schemas`,
  line 285). Every refusal is a plain result string, never an
  exception — and nothing is written on refusal.
- Writes `plugin.py` (the code as given) + `plugin.json` in the exact
  shape the loader loads (`_created_plugin_meta`, line 351): `kind`
  `"plugin"`, every tool `requires_approval: true`, parameters from
  `TOOL_SCHEMAS` where given, empty-object parameters otherwise.
- The new plugin starts **DISABLED** — the owner enables it in
  Customize.

**`TOOL_SCHEMAS` is a creation-time channel only.** The loader never
reads it. It exists so an agent-created plugin can declare tool
arguments: `create_plugin` copies the schemas into the generated
`plugin.json`, and from then on the manifest is the truth. Hand-written
plugins declare `parameters` in `plugin.json` directly and skip
`TOOL_SCHEMAS` entirely.

**`update_plugin`** (`forge/create_ext.py:416-505`):

- Refuses when the plugin does **not** exist (creating is
  `create_plugin`'s job).
- Runs the **same validation gate** as create (`_plugin_payload`,
  line 323) **before writing a byte** — a refused update leaves the
  existing plugin byte-identical.
- Edits `plugin.json` rather than regenerating it: fields the update
  does not own (`id`, `name`, `kind`, `access`, `config_keys`,
  hand-set per-tool descriptions and approval flags) survive; only the
  code, the description, and the tool list change. A tool the new
  code adds gets the create shape (approval on).
- One deliberate state change: if the plugin is currently **enabled**,
  a successful update switches it **off** — the owner re-enables it
  in Customize after reviewing the new code.

**Project-local plugins:** skills/plugins saved inside a workspace
(`plugins/` or `.forge/plugins/`) are detected and reported as
project-only, never silently loaded as globals
(`find_project_local`, line 507). The owner can house them into the
app folders from Customize (`house_project_local`, line 526); a name
collision skips that item (the global copy wins, nothing is
overwritten). A `write_file` that lands at a skill/plugin-shaped path
inside the workspace gets a hint appended pointing at the global
tools (`project_local_hint`).

## 7. The bundled seven

The plugins that ship with Forge (all in `plugins/` in this repo,
verbatim from the tree):

| Plugin | Kind | Tools | Needs |
|---|---|---|---|
| `resource-governor` | plugin | `check_resources` | `forge.governor`; Ollama local API |
| `tester` | plugin | `run_tester` | `forge.ollama_client`, `forge.tools`, `forge.handoff`, `forge.seats`, `forge.lightmachine`; tester model in Agent settings |
| `github` | connector | `github_repo_info`, `github_search_repos` | Nothing (stdlib-only); optional `github_token` |
| `huggingface` | connector | `hf_search_models`, `hf_model_info` | Nothing (stdlib-only); optional `hf_token` |
| `mcp` | connector | `mcp_list_tools`, `mcp_call` | `mcp_servers` in `connectors.json`; the servers themselves |
| `browse` | connector | 6 verbs + `verify_in_browser` | Sibling `mcp/` folder (`mcp_client.py`); `forge/browse.py`, `forge/verify.py`, `forge/webengine.py`; OpenCode Browse server + extension, installed by the owner |
| `cloudstore` | connector | `cloud_list`, `cloud_read`, `cloud_download`, `cloud_upload`, `cloud_delete` | `forge/cloudstore.py`; rclone binary, configured by the owner; `.forge/cloudstore.json` allowed prefixes |

Several plugins import `forge.*` modules — they are thin handler
shells over Forge-side logic and only run inside a Forge install.
Only `github`, `huggingface`, and `mcp` are self-contained
(stdlib-only) apart from the loader itself. Each plugin folder's
README states its own dependencies and setup.

### BNB-original: `gist`

One plugin in this repo is not bundled in Forge — it was authored
here to this contract (Delta 6, 2026-11-15, on Joshua's order:
context awareness for AI use). `gist` is self-contained (stdlib
only, no `forge.*` imports): 4 read-only tools (`gist_file`,
`gist_folder`, `gist_repo`, `gist_text`), no approval needed. It
follows the same loader contract as the bundled seven but is
verified by its own 30-test suite, not by a tree diff, and the
re-sync rule does not cover it. First load starts DISABLED like any
new plugin; it has not yet been loaded inside a real Forge install.

## 8. What this spec does not cover

- **aura-plugins** (`BROKE-N-BORED/aura-plugins`) is a **different
  plugin system**: a Claude Code plugin marketplace (`.claude-plugin`
  manifests; `commands/`, `skills/`, `hooks/`, `agents/` dirs). It
  holds no Forge `plugin.json` / `plugin.py` content and nothing from
  it was copied here. Porting anything across would mean rewriting it
  to this contract, not copying it.
- **Skill authoring** (`create_skill` / `update_skill`,
  `forge/create_ext.py:195-264`) is the sibling system — skills live
  in `BNB-SKILLS`, not here.
