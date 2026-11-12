# Plugin Scaffold

The smallest plugin that actually loads. One tool, `scaffold_echo`,
which echoes its `text` argument back — enough to prove the loader
picked the plugin up and its handler runs.

## Use it

1. Copy this folder into the Forge app's `plugins/` directory and
   rename it to your plugin's slug (lowercase letters, digits,
   hyphens only — e.g. `weather-fetch`).
2. Change the `id`, `name`, and `description` in `plugin.json`, and
   rename the tool + handler to match what your plugin does.
3. Restart Forge (or rescan) — the new plugin appears in Customize
   and **starts DISABLED**. Enable it there; its code never runs
   until you do.
4. Call the tool and check the echo comes back.

## What is load-bearing here

- `plugin.json` is the declaration the loader reads: `id`, `name`,
  `kind` (`plugin` or `connector`), `description`, `access`, and the
  `tools` list. Each tool's `parameters` object is the JSON schema
  the model sees; `requires_approval` decides whether the tool passes
  the owner's approval gate before it runs.
- `plugin.py` must define `HANDLERS = {"tool_name": handler}` at the
  top level, where each handler takes `(args, ctx)` and returns a
  string. The loader skips a declared tool with no callable handler,
  and never registers a handler with no declaration.
- `TOOL_SCHEMAS` is **not** part of the load contract: it is only a
  channel the `create_plugin` authoring tool reads (by AST, without
  executing the code) to build `plugin.json` for agent-created
  plugins. If you write `plugin.json` by hand, declare the parameters
  there and skip `TOOL_SCHEMAS` entirely.
- `ctx.config` holds only the `connectors.json` keys this plugin's
  manifest lists in `config_keys`. This scaffold declares none, so
  `ctx.config` is `{}`. Declare keys only for secrets/config your
  plugin actually needs — secret keys live in the encrypted vault,
  not in `connectors.json`.
- Keep the slug rules: `create_plugin` refuses anything but
  lowercase letters, digits, and hyphens, and refuses a name that
  already exists. Hand-copied folders should follow the same rule —
  the folder name is the fallback id when `plugin.json` omits one.

## Verified

This scaffold was verified against the real Forge loader
(`forge/plugins.py::load_plugins` from the Code Forge tree): it
registers `scaffold_echo` in the tool registry, and calling the
handler with `{"text": "hello"}` returns `scaffold_echo: hello`.
See the root README for the verification run.

## Full contract

See `PLUGIN-SPEC.md` at the repo root — the plugin contract as the
loader actually implements it, with file/line references.
