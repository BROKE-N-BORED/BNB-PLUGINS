# MCP Servers

**Kind:** connector · **ID:** `mcp` · **Tools:** 2

Bridge to locally-run MCP (Model Context Protocol) servers declared
in `connectors.json` — their tools become the agent's tools.

## Tools

- `mcp_list_tools` — list the tools a configured local MCP server
  exposes. Read-only, no approval needed.
- `mcp_call` — call one tool on a configured local MCP server.
  Approval-gated, like any write-class tool.

## Setup

Declare servers in the app data dir's `connectors.json`:

```json
{"mcp_servers": {"files": {"command": "python3", "args": ["/path/server.py"]}}}
```

Adding an MCP server means trusting a program to run on this PC —
the first use of each server configuration is approved by the owner
at the gate, and any change to its command or arguments is approved
again.

## Access

Local processes only. Listing tools is read-only; calling a tool
requires approval.

## Files

- `plugin.py` — the two handlers.
- `mcp_client.py` — the shared MCP client machinery (JSON-RPC over
  stdio, server lifecycle). The Browse connector imports this same
  file from the sibling `mcp/` folder, so **keep this folder beside
  `browse/`** — Browse breaks without it.

## Dependencies

Standard library only. No Forge-side module needed beyond the loader.
The MCP servers themselves are the owner's programs, run locally.

## Source

Verbatim copy of `plugins/mcp/` from the Code Forge tree
(`~/workspace/code-forge-v2/Linux Forge Agent/`, the shared tree —
identical in the publish staging and the newest build trees, checked
2026-11-15). `plugin.json`, `plugin.py`, and `mcp_client.py` are
byte-identical to the tree; this README is the only added file.
