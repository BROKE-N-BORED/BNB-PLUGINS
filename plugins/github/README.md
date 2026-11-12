# GitHub

**Kind:** connector · **ID:** `github` · **Tools:** 2 (both read-only, no approval needed)

Connector (first pair, Note 6): look up GitHub repos and search code —
the far end of clone-and-promote.

## Tools

- `github_repo_info` — look up a public repo (`owner/name`):
  description, stars, language, license, last push.
- `github_search_repos` — search public repositories by text.

## Access

Read-only HTTPS calls to `api.github.com`. A token in
`connectors.json` (`github_token`) only raises rate limits — never
required for public data. JSON bodies are read with a hard 5 MB cap;
the `repo` parameter must be exactly `owner/name` (no path-walking
segments).

## Dependencies

Standard library only (`urllib`). No Forge-side module needed beyond
the loader. Nothing external to install.

## Source

Verbatim copy of `plugins/github/` from the Code Forge tree
(`~/workspace/code-forge-v2/Linux Forge Agent/`, the shared tree —
identical in the publish staging and the newest build trees, checked
2026-11-12). `plugin.json` and `plugin.py` are byte-identical to the
tree; this README is the only added file.
