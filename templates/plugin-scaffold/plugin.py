"""Plugin scaffold — the smallest plugin that actually loads.

One tool, `scaffold_echo`: it echoes its `text` argument back with a
prefix, so you can prove the plugin loaded and its handler runs. No
imports beyond the standard library, no Forge-side modules, no config
keys, no side effects — copy this folder, rename it, and build from it.

The contract, in full:

- `plugin.json` (beside this file) declares the plugin: id, name,
  kind, description, access, and the tools list. The loader builds
  each tool's schema from the manifest — the `parameters` object here
  is what the model sees.
- `HANDLERS` maps each declared tool name to a function taking
  (args, ctx) and returning a string. A declared tool with no handler
  is skipped by the loader; a handler with no declaration is never
  registered.
- `ctx` is a per-plugin view over the live PluginContext: workspace,
  current model, log, cancel event — and `config`, which holds ONLY
  the connectors.json keys this plugin's manifest lists in
  "config_keys" (this scaffold declares none, so ctx.config is {}).
- New plugins start DISABLED: after copying this folder into the
  Forge app's plugins/ directory, enable it in Customize before its
  code will run. The loader never executes a disabled or unknown
  plugin's code.
"""


def scaffold_echo(args, ctx):
    text = str((args or {}).get("text", "")).strip()
    if not text:
        return "scaffold_echo: no text given — pass a 'text' argument."
    return f"scaffold_echo: {text}"


HANDLERS = {"scaffold_echo": scaffold_echo}
