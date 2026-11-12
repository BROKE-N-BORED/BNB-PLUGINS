# Browse (OpenCode)

**Kind:** connector · **ID:** `browse` · **Tools:** 7

OpenCode Browse (item #55, adopted — not built): six fenced verbs
plus the item #65 verify loop (`verify_in_browser`) over the owner's
signed-in Chromium via its local MCP server.

## Tools

- `browse_open` — open a page in the agent's Browse tab. **Fenced:**
  the URL's host must be on the active project's Browse site
  allowlist (`.forge/browse.json`) — an unlisted host is refused
  before the browser is touched. Approval required.
- `browse_read` — read the current page as a TEXT snapshot. Text is
  the default and the rule; no approval needed.
- `browse_click` — click an element by CSS selector. Approval required.
- `browse_type` — type text into a field (selector + text). Approval
  required.
- `browse_screenshot` — screenshot the current page, on demand only
  (when text cannot show what is needed). No approval needed.
- `browse_hand_back` — hand the tab back to the owner (login, 2FA,
  payment, captcha). Waits at the approval gate; the owner's approval
  IS their Continue. After the browser reports a wall, Browse stays
  HELD — every verb refuses — until this call is approved.
- `verify_in_browser` — verify your own work: open a page, read it
  back as text, save a screenshot under the project's
  `.forge/artifacts/`. Project pages are served from a throwaway
  loopback preview that exists only for the call; http(s) URLs must
  be on the site allowlist like `browse_open`. No approval needed.

## Setup (owner's, on their PC — Forge never installs Browse)

1. Install Browse with its own installer.
2. Add the preset block from the README ("Browse connector") /
   `forge.browse.preset_config()` to `connectors.json`.
3. Enable this connector in Customize → Connectors.
4. List the project's sites in `.forge/browse.json`.

## Access

Drives the owner's real Chromium via the external OpenCode Browse MCP
server + extension the owner installs. Navigation is fenced by the
project's site allowlist; acting verbs and hand-back require approval.
Config keys: `mcp_servers`, `browse`.

## Dependencies

- **Sibling `mcp/` plugin folder (required):** `plugin.py` inserts
  the `mcp` folder into `sys.path` to import `mcp_client`. Keep both
  folders side by side in `plugins/`.
- **Forge-side modules:** `forge/browse.py` (fences, allowlist,
  hold, tool map), `forge/verify.py`, `forge/webengine.py` — it only
  runs inside a Forge install, where those already exist.
- **External:** the OpenCode Browse MCP server + Chromium extension,
  installed by the owner.

## Source

Verbatim copy of `plugins/browse/` from the Code Forge tree
(`~/workspace/code-forge-v2/Linux Forge Agent/`, the shared tree —
identical in the publish staging and the newest build trees, checked
2026-11-12). `plugin.json` and `plugin.py` are byte-identical to the
tree; this README is the only added file.
