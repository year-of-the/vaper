#!/usr/bin/env python3
"""Idempotent vaper installer.

Run by the SessionStart hook on every session, and by /vaper:init,
/vaper:uninstall on explicit user request. Also called with no flags
on first install (when the launcher in CLAUDE_PLUGIN_DATA does not
yet exist) to compose vaper into the user's statusLine.

Modes:
  (no flag)     heal-only — re-point any existing vaper-meter token to
                the current launcher path. First-run upgrades to install.
  --install     compose vaper into ~/.claude/settings.json (idempotent).
  --uninstall   remove vaper from ~/.claude/settings.json and delete the
                launcher.

The launcher lives at ${CLAUDE_PLUGIN_DATA}/vaper-meter — a stable path
across plugin updates, auto-removed by Claude Code on /plugin uninstall.
"""

import json
import os
import shlex
import sys
from pathlib import Path

PLUGIN_ROOT = Path(os.environ["CLAUDE_PLUGIN_ROOT"]).resolve()
DATA_DIR    = Path(os.environ["CLAUDE_PLUGIN_DATA"]).resolve()
SCRIPT      = PLUGIN_ROOT / "scripts" / "water-meter.py"
LAUNCHER    = DATA_DIR / "vaper-meter"
MODE_FILE   = DATA_DIR / "mode"
SETTINGS    = Path.home() / ".claude" / "settings.json"


def write_launcher() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAUNCHER.write_text(
        "#!/bin/sh\n"
        f"mode=$(cat {shlex.quote(str(MODE_FILE))} 2>/dev/null)\n"
        '[ -z "$mode" ] && mode=water\n'
        f'exec {shlex.quote(str(SCRIPT))} --mode="$mode" "$@"\n'
    )
    LAUNCHER.chmod(0o755)


def read_settings() -> dict:
    if not SETTINGS.exists():
        return {}
    try:
        return json.loads(SETTINGS.read_text() or "{}")
    except json.JSONDecodeError:
        return {}


def write_settings(data: dict) -> None:
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(data, indent=2) + "\n")


def is_vaper_token(tok: str) -> bool:
    return tok == "vaper-meter" or tok.endswith("/vaper-meter")


def repoint(cmd: str, launcher: str) -> str:
    """Replace any vaper-meter token (and any immediately-following
    --mode=<x> token, leftover from older installs) with launcher."""
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return cmd
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if is_vaper_token(t):
            out.append(launcher)
            i += 1
            if i < len(toks) and toks[i].startswith("--mode="):
                i += 1
            continue
        out.append(t)
        i += 1
    return shlex.join(out)


def strip_vaper(cmd: str) -> str:
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return cmd
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if is_vaper_token(t):
            i += 1
            if i < len(toks) and toks[i].startswith("--mode="):
                i += 1
            continue
        out.append(t)
        i += 1
    # also drop a trailing standalone "--" left over from `multi.sh -- vaper-meter`
    while out and out[-1] == "--":
        out.pop()
    return shlex.join(out)


def install() -> None:
    data = read_settings()
    sl = data.get("statusLine") or {}
    cmd = sl.get("command", "")
    if cmd and "vaper-meter" in cmd:
        new_cmd = repoint(cmd, str(LAUNCHER))
    elif cmd:
        # existing non-vaper command (e.g. a multi-statusline wrapper):
        # append vaper at the innermost position.
        new_cmd = cmd + " " + shlex.quote(str(LAUNCHER))
    else:
        new_cmd = str(LAUNCHER)
    new_sl = {"type": sl.get("type", "command"), "command": new_cmd}
    for k, v in sl.items():
        if k not in ("type", "command"):
            new_sl[k] = v
    if not cmd and "padding" not in new_sl:
        new_sl["padding"] = 1
    if new_sl == sl:
        return
    data["statusLine"] = new_sl
    write_settings(data)


def heal() -> None:
    data = read_settings()
    sl = data.get("statusLine") or {}
    cmd = sl.get("command", "")
    if not cmd or "vaper-meter" not in cmd:
        return
    new_cmd = repoint(cmd, str(LAUNCHER))
    if new_cmd == cmd:
        return
    data["statusLine"] = {**sl, "command": new_cmd}
    write_settings(data)


def uninstall() -> None:
    try:
        LAUNCHER.unlink()
    except FileNotFoundError:
        pass
    data = read_settings()
    sl = data.get("statusLine") or {}
    cmd = sl.get("command", "")
    if not cmd or "vaper-meter" not in cmd:
        return
    new_cmd = strip_vaper(cmd).strip()
    if not new_cmd:
        data.pop("statusLine", None)
    else:
        data["statusLine"] = {**sl, "command": new_cmd}
    write_settings(data)


def main() -> int:
    flags = set(sys.argv[1:])
    if "--uninstall" in flags:
        uninstall()
        print("vaper removed from your statusLine. You can now run /plugin uninstall vaper.")
        return 0

    first_time = not LAUNCHER.exists()
    write_launcher()

    if "--install" in flags or first_time:
        install()
        if "--install" in flags:
            print("vaper installed in water mode. Restart Claude Code to see the banner.")
            print("Switch modes with:")
            print("  /vaper:mode <name>")
            print("Modes: water (default), calories, bullets, btc.")
    else:
        heal()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # never crash the SessionStart hook
        print(f"vaper install: {e}", file=sys.stderr)
        sys.exit(0)
