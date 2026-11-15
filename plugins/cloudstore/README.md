# Cloud Storage (rclone)

**Kind:** connector · **ID:** `cloudstore` · **Tools:** 5

Cloud storage via rclone (item #70, adopted — not built): list,
read, download, upload, and delete individual files on the owner's
Google Drive, Dropbox, OneDrive, Nextcloud/WebDAV, S3, or any other
rclone remote. Explicit transfers only — no sync, no mirroring.

## Tools

- `cloud_list` — list a remote path (e.g. `gdrive:Forge/docs`).
  Read-only, no approval needed.
- `cloud_read` — read ONE text file into the conversation.
  Size-capped at 64 KB; bigger or binary files are refused with a
  pointer to `cloud_download`. No approval needed.
- `cloud_download` — download ONE file into the project (remote copy
  untouched). Approval required.
- `cloud_upload` — upload ONE project file to a remote (a copy, not
  a move). Approval required.
- `cloud_delete` — delete ONE file from a remote. Never a folder,
  never recursive. Approval required.

Every remote target is **fenced**: the path must be, or sit under, a
prefix the project allows in `.forge/cloudstore.json` (default:
nothing allowed) — an unlisted prefix is refused before rclone is
ever called. Local paths must resolve inside the project workspace.

## Setup (owner's, in a terminal — Forge never touches credentials)

1. Install rclone.
2. Run `rclone config` once — rclone runs the OAuth sign-in and
   keeps the tokens in ITS OWN config file. Forge stores NO cloud
   credentials anywhere; `connectors.json` may name only which
   rclone command to run.
3. Name the project's allowed remote prefixes in
   `.forge/cloudstore.json`, then enable this connector.

## Access

Runs the owner's rclone binary (subprocess, argument lists only) for
explicit file transfers against the remotes the owner configured.
Config keys: `cloudstore`.

## Dependencies

- **Forge-side module:** `forge/cloudstore.py` holds all the logic
  (backend calls, setup words, the fence) — this plugin is the thin
  handler shell over it, so it only runs inside a Forge install.
- **External:** the rclone binary on PATH, configured by the owner.

## Source

Verbatim copy of `plugins/cloudstore/` from the Code Forge tree
(`~/workspace/code-forge-v2/Linux Forge Agent/`, the shared tree —
identical in the publish staging and the newest build trees, checked
2026-11-15). `plugin.json` and `plugin.py` are byte-identical to the
tree; this README is the only added file.
