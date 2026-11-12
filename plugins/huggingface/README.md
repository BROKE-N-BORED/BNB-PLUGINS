# Hugging Face

**Kind:** connector · **ID:** `huggingface` · **Tools:** 2 (both read-only, no approval needed)

Connector (first pair, Note 6): search Hugging Face and inspect model
repos, including GGUF file sizes — the model's supply line.

## Tools

- `hf_search_models` — search Hugging Face models by text. Returns
  names, downloads, task.
- `hf_model_info` — inspect one HF repo (`owner/name`): license,
  downloads, files with sizes — GGUFs especially.

## Access

Read-only HTTPS calls to `huggingface.co`'s public API. A token in
`connectors.json` (`hf_token`) is optional. JSON bodies are read with
a hard 5 MB cap.

## Dependencies

Standard library only (`urllib`). No Forge-side module needed beyond
the loader. Nothing external to install.

## Source

Verbatim copy of `plugins/huggingface/` from the Code Forge tree
(`~/workspace/code-forge-v2/Linux Forge Agent/`, the shared tree —
identical in the publish staging and the newest build trees, checked
2026-11-12). `plugin.json` and `plugin.py` are byte-identical to the
tree; this README is the only added file.
