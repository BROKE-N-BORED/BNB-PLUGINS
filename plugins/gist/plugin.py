"""Gist - short, honest, deterministic context snapshots for AI use.

An AI calls it before acting on something it hasn't seen yet, and gets
the gist: what it is, how big, what's in it, what's stale. No model
calls, no network, stdlib only - a $0 context snapshot, not a summary
the model could write itself.

Honesty rules (structural, tested):
- A gist is SHORT: output is capped at MAX_LINES lines. When the cap
  cuts something, the last line names what was cut.
- A gist never invents content. When it cannot determine something,
  it says so plainly ("couldn't determine").
- A gist never claims a file's purpose beyond what its name and
  headings say.
- Missing paths, empty files, and non-repos are reported plainly,
  never as an error and never with invented filler.
"""

import datetime
import os
import re
import subprocess

MAX_LINES = 40
MAX_READ_BYTES = 1024 * 1024
MAX_LINES_READ = 5000
MAX_WALK_ENTRIES = 5000
STALE_DAYS = 90
GIT_TIMEOUT = 10

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv",
             ".tox", ".mypy_cache", ".eggs"}
README_NAMES = ("README.md", "README.txt", "README.rst", "README")
FILE_MARKERS = ("TODO", "FIXME", "OPEN")
TEXT_MARKERS = ("TODO", "DONE", "OPEN", "DECISION", "FLAG")


def _workspace(ctx):
    """The workspace path from the context view, or None."""
    return getattr(ctx, "workspace", None) if ctx is not None else None


def _resolve(path, ctx):
    """Expand ~ and resolve a relative path against the workspace."""
    path = os.path.expanduser(str(path))
    if not os.path.isabs(path):
        ws = _workspace(ctx)
        if ws:
            path = os.path.join(ws, path)
    return os.path.abspath(path)


def _fmt_size(n):
    if n < 1024:
        return f"{n} bytes"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _fmt_date(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def _assemble(sections, max_lines=MAX_LINES):
    """Join (name, lines) sections into one capped output.

    When the lines run past max_lines, the tail is cut and the last
    line names how many lines were cut and which sections they came
    from - the reader always knows what is missing.
    """
    flat = []
    for name, lines in sections:
        for line in lines:
            flat.append((name, line))
    if len(flat) <= max_lines:
        return "\n".join(line for _, line in flat)
    kept = flat[:max_lines - 1]
    dropped = flat[max_lines - 1:]
    names = []
    for name, _ in dropped:
        if name not in names:
            names.append(name)
    out = [line for _, line in kept]
    out.append(f"... cut {len(dropped)} more line(s) "
               f"(from: {', '.join(names)})")
    return "\n".join(out)


def _read_text_lines(path):
    """Read a file as text lines, capped.

    Returns (lines, notes, is_binary). notes lists what the cap left
    out, in plain words. A file with NUL bytes in its first 8 KiB
    counts as binary and returns no lines.
    """
    notes = []
    with open(path, "rb") as fh:
        head = fh.read(8192)
        if b"\x00" in head:
            return [], notes, True
        fh.seek(0)
        raw = fh.read(MAX_READ_BYTES + 1)
    size = os.path.getsize(path)
    if len(raw) > MAX_READ_BYTES:
        raw = raw[:MAX_READ_BYTES]
        notes.append(f"Read only the first {_fmt_size(MAX_READ_BYTES)} "
                     f"of {_fmt_size(size)} - headings and markers "
                     f"come from that part.")
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    if len(lines) > MAX_LINES_READ:
        lines = lines[:MAX_LINES_READ]
        notes.append(f"Read only the first {MAX_LINES_READ} lines - "
                     f"more lines follow.")
    return lines, notes, False


def _headings(lines, path):
    """(line number, heading text) for markdown headings, plus
    top-level def/class lines in a .py file. Deterministic only."""
    found = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            text = stripped.lstrip("#").strip()
            if text:
                found.append((i, text))
    if path.endswith(".py"):
        for i, line in enumerate(lines, 1):
            if line.startswith(("def ", "class ")):
                found.append((i, line.strip().rstrip(":")))
        found.sort(key=lambda item: item[0])
    return found


def _markers(lines, kinds):
    """(line number, marker, line text) for whole-word markers."""
    pattern = re.compile(r"\b(" + "|".join(kinds) + r")\b")
    found = []
    for i, line in enumerate(lines, 1):
        match = pattern.search(line)
        if match:
            found.append((i, match.group(1), line.strip()[:100]))
    return found


def _first_nonempty(lines, count=3, skip_headings=True):
    """The first `count` non-empty lines, optionally skipping headings."""
    out = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if skip_headings and stripped.startswith("#"):
            continue
        out.append(stripped[:120])
        if len(out) >= count:
            break
    return out


def _readme_gist(folder):
    """(title, lines) for a README in `folder`, or None."""
    for name in README_NAMES:
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            lines, _, is_binary = _read_text_lines(path)
            if is_binary:
                return name, ["README is binary - couldn't read it."]
            heads = _headings(lines, path)
            title = heads[0][1] if heads else None
            first = _first_nonempty(lines)
            out = []
            if title:
                out.append(f"Title: {title}")
            out.extend(first)
            if not out:
                out.append("README is empty.")
            return name, out
    return None


def _git(path, *args):
    """Run a read-only git command in `path`.

    Returns (ok, stdout). ok is False when git is missing, the
    command times out, or git exits non-zero.
    """
    try:
        result = subprocess.run(
            ["git", "-C", path, *args],
            capture_output=True, text=True, timeout=GIT_TIMEOUT)
    except FileNotFoundError:
        return False, "git is not installed"
    except subprocess.TimeoutExpired:
        return False, f"git timed out after {GIT_TIMEOUT}s"
    if result.returncode != 0:
        return False, (result.stderr or "").strip()
    return True, result.stdout


# ---------------------------------------------------------------- verbs


def gist_file(args, ctx):
    path = str((args or {}).get("path", "") or "").strip()
    if not path:
        return "No path given - pass a 'path' argument."
    full = _resolve(path, ctx)
    if not os.path.exists(full):
        return f"No such file: {path}."
    if os.path.isdir(full):
        return (f"That's a folder, not a file: {path}. "
                f"Use gist_folder for folders.")
    name = os.path.basename(full)
    size = os.path.getsize(full)
    modified = _fmt_date(os.path.getmtime(full))
    if size == 0:
        return f"The file is empty: {name} (0 bytes, modified {modified})."
    lines, notes, is_binary = _read_text_lines(full)

    file_lines = [f"File: {name}",
                  f"Path: {full}",
                  f"Size: {_fmt_size(size)} · modified {modified}"]
    if is_binary:
        file_lines.append("Text content: couldn't determine - the file "
                          "is binary, so no headings or markers were read.")
        sections = [("file", file_lines)]
        return _assemble(sections)

    file_lines.append(f"Lines: {len(lines)}")
    heads = _headings(lines, full)
    first = _first_nonempty(lines, count=1, skip_headings=False)
    if heads:
        file_lines.append(f"Title: {heads[0][1]}")
    elif first:
        file_lines.append(f"First line: {first[0]}")
    else:
        file_lines.append("Title: couldn't determine - no heading or "
                          "text line found.")
    sections = [("file", file_lines)]

    if heads:
        shown = heads[:10]
        section_lines = ["Sections:"] + [
            f"  line {n}: {text}" for n, text in shown]
        if len(heads) > 10:
            section_lines.append(f"  ... and {len(heads) - 10} more "
                                 f"heading(s)")
    else:
        section_lines = ["Sections: none found - couldn't determine "
                         "sections (no headings)."]
    sections.append(("sections", section_lines))

    found = _markers(lines, FILE_MARKERS)
    if found:
        shown = found[:10]
        marker_lines = ["Markers (TODO/FIXME/OPEN):"] + [
            f"  line {n} [{kind}] {text}" for n, kind, text in shown]
        if len(found) > 10:
            marker_lines.append(f"  ... and {len(found) - 10} more "
                                f"marker(s)")
    else:
        marker_lines = ["Markers: no TODO/FIXME/OPEN markers found."]
    sections.append(("markers", marker_lines))

    if notes:
        sections.append(("notes", ["Notes:"] + [f"  {n}" for n in notes]))
    return _assemble(sections)


def gist_folder(args, ctx):
    path = str((args or {}).get("path", "") or "").strip()
    if not path:
        return "No path given - pass a 'path' argument."
    full = _resolve(path, ctx)
    if not os.path.exists(full):
        return f"No such folder: {path}."
    if not os.path.isdir(full):
        return (f"That's a file, not a folder: {path}. "
                f"Use gist_file for files.")
    name = os.path.basename(full) or full

    files = []  # (path, size, mtime, ext)
    dir_count = 0
    skipped = set()
    entries = 0
    capped = False
    for root, dirs, names in os.walk(full):
        kept = []
        for d in dirs:
            if d in SKIP_DIRS:
                skipped.add(d)
            else:
                kept.append(d)
        dirs[:] = kept
        dir_count += len(dirs)
        for fname in names:
            entries += 1
            if entries > MAX_WALK_ENTRIES:
                capped = True
                break
            fpath = os.path.join(root, fname)
            try:
                st = os.stat(fpath)
            except OSError:
                continue
            _, ext = os.path.splitext(fname)
            files.append((fpath, st.st_size, st.st_mtime,
                          ext.lower() or "(no extension)"))
        if capped:
            break

    total_size = sum(size for _, size, _, _ in files)
    folder_lines = [f"Folder: {name}",
                    f"Path: {full}",
                    f"Files: {len(files)} · folders: {dir_count} · "
                    f"total size: {_fmt_size(total_size)}"]
    sections = [("folder", folder_lines)]

    counts = {}
    for _, _, _, ext in files:
        counts[ext] = counts.get(ext, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    type_lines = ["By type:"] + [
        f"  {ext}: {n}" for ext, n in ranked[:8]]
    if len(ranked) > 8:
        type_lines.append(f"  ... and {len(ranked) - 8} more type(s)")
    if not ranked:
        type_lines = ["By type: no files found."]
    sections.append(("types", type_lines))

    readme = _readme_gist(full)
    if readme:
        rname, rlines = readme
        sections.append(("readme", [f"README ({rname}):"] +
                         [f"  {line}" for line in rlines]))
    else:
        sections.append(("readme", ["README: none found."]))

    if files:
        newest = sorted(files, key=lambda f: f[2], reverse=True)[:3]
        oldest = sorted(files, key=lambda f: f[2])[:3]
        sections.append(("newest", ["Newest:"] + [
            f"  {os.path.relpath(p, full)} ({_fmt_date(m)})"
            for p, _, m, _ in newest]))
        sections.append(("oldest", ["Oldest:"] + [
            f"  {os.path.relpath(p, full)} ({_fmt_date(m)})"
            for p, _, m, _ in oldest]))
        cutoff = datetime.datetime.now().timestamp() - STALE_DAYS * 86400
        stale = [f for f in files if f[2] < cutoff]
        stale.sort(key=lambda f: f[2])
        if stale:
            stale_lines = [f"Stale (untouched {STALE_DAYS}+ days): "
                           f"{len(stale)} file(s)"] + [
                f"  {os.path.relpath(p, full)} ({_fmt_date(m)})"
                for p, _, m, _ in stale[:5]]
            if len(stale) > 5:
                stale_lines.append(f"  ... and {len(stale) - 5} more")
        else:
            stale_lines = [f"Stale: nothing - every file was touched "
                           f"in the last {STALE_DAYS} days."]
        sections.append(("stale", stale_lines))

    notes = []
    if skipped:
        notes.append(f"Skipped (not counted): {', '.join(sorted(skipped))}.")
    if capped:
        notes.append(f"Walk stopped after {MAX_WALK_ENTRIES} entries - "
                     f"counts cover that part only.")
    if notes:
        sections.append(("notes", ["Notes:"] +
                         [f"  {n}" for n in notes]))
    return _assemble(sections)


def gist_repo(args, ctx):
    path = str((args or {}).get("path", "") or "").strip()
    full = _resolve(path, ctx) if path else (
        _workspace(ctx) or os.getcwd())
    label = path or full
    ok, out = _git(full, "rev-parse", "--git-dir")
    if not ok:
        if "not installed" in out:
            return "git is not installed - couldn't check the repo."
        if "timed out" in out:
            return f"git timed out checking {label}."
        return f"Not a git repo: {label}."

    ok, branch = _git(full, "branch", "--show-current")
    branch = branch.strip() if ok else ""
    if not branch:
        branch = "(detached HEAD)"
    ok, head = _git(full, "log", "-1", "--format=%h %ad %s",
                    "--date=short")
    head = head.strip() if ok and head.strip() else (
        "No commits yet - the repo has no history.")
    ok, recent = _git(full, "log", "-5", "--format=%h %ad %s",
                      "--date=short")
    commits = [line for line in recent.splitlines() if line.strip()] \
        if ok else []

    ok, status = _git(full, "status", "--porcelain")
    staged = unstaged = untracked = 0
    if ok:
        for line in status.splitlines():
            if line.startswith("??"):
                untracked += 1
            else:
                if len(line) > 0 and line[0] not in " ?":
                    staged += 1
                if len(line) > 1 and line[1] not in " ":
                    unstaged += 1
    changed = staged + unstaged + untracked

    repo_lines = [f"Repo: {os.path.basename(full)}",
                  f"Path: {full}",
                  f"Branch: {branch}",
                  f"Head: {head}",
                  f"Uncommitted: {changed} change(s) "
                  f"({staged} staged, {unstaged} unstaged, "
                  f"{untracked} untracked)"]
    sections = [("repo", repo_lines)]

    if commits:
        sections.append(("commits", ["Last 5 commits:"] +
                         [f"  {line}" for line in commits]))
    else:
        sections.append(("commits", ["Last 5 commits: none - the repo "
                                     "has no history."]))

    readme = _readme_gist(full)
    if readme:
        rname, rlines = readme
        sections.append(("readme", [f"README ({rname}):"] +
                         [f"  {line}" for line in rlines]))
    else:
        sections.append(("readme", ["README: none found."]))
    return _assemble(sections)


def gist_text(args, ctx):
    text = (args or {}).get("text")
    if text is None:
        return "No text given - pass a 'text' argument."
    text = str(text)
    if not text.strip():
        return "The text is empty - nothing to gist."
    lines = text.splitlines()
    words = len(text.split())

    text_lines = [f"Text: {len(lines)} line(s), {words} word(s)"]
    sections = [("text", text_lines)]

    first = _first_nonempty(lines, count=5, skip_headings=False)
    sections.append(("first lines", ["First lines:"] +
                     [f"  {line}" for line in first]))

    heads = _headings(lines, "")
    if heads:
        shown = heads[:10]
        section_lines = ["Sections:"] + [
            f"  line {n}: {text}" for n, text in shown]
        if len(heads) > 10:
            section_lines.append(f"  ... and {len(heads) - 10} more "
                                 f"heading(s)")
    else:
        section_lines = ["Sections: none found."]
    sections.append(("sections", section_lines))

    found = _markers(lines, TEXT_MARKERS)
    if found:
        shown = found[:10]
        marker_lines = ["Markers (TODO/DONE/OPEN/DECISION/FLAG):"] + [
            f"  line {n} [{kind}] {text}" for n, kind, text in shown]
        if len(found) > 10:
            marker_lines.append(f"  ... and {len(found) - 10} more "
                                f"marker(s)")
    else:
        marker_lines = ["Markers: none found."]
    sections.append(("markers", marker_lines))

    missing = []
    if not heads:
        missing.append("sections (no headings in the text)")
    if not found:
        missing.append("marked items (no TODO/DONE/OPEN/DECISION/FLAG "
                       "markers in the text)")
    if missing:
        sections.append(("could not determine",
                         ["Could not determine:"] +
                         [f"  {item}" for item in missing]))
    sections.append(("note", ["This gist only lists what the text "
                              "contains. It does not summarize or "
                              "interpret it."]))
    return _assemble(sections)


HANDLERS = {"gist_file": gist_file,
            "gist_folder": gist_folder,
            "gist_repo": gist_repo,
            "gist_text": gist_text}
