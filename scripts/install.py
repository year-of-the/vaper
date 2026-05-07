#!/usr/bin/env python3
"""Idempotent vaper installer.

Run by the SessionStart hook on every session, and by /vaper:init,
/vaper:uninstall on explicit user request. First run (no launcher in
${CLAUDE_PLUGIN_DATA}) auto-upgrades to install.

Modes:
  (no flag)     heal-only — re-point any existing vaper-meter token to
                the current launcher path. First-run upgrades to install.
  --install     compose vaper into the active statusLine chain.
  --uninstall   remove vaper from the chain and delete the launcher.

Two chain owners are supported:

  - ~/.claude/settings.json's statusLine.command (the default).
  - ~/.claude/personas/wrapped-statusline.txt (when the personas kit
    has captured the prior statusLine into its own chain). If that
    file exists, vaper writes there instead of settings.json — personas
    owns settings.json's command and would silently swallow vaper's
    output if we appended to it.

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
WRAPPED     = Path.home() / ".claude" / "personas" / "wrapped-statusline.txt"


def write_launcher() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAUNCHER.write_text(
        "#!/bin/sh\n"
        f"mode=$(cat {shlex.quote(str(MODE_FILE))} 2>/dev/null)\n"
        '[ -z "$mode" ] && mode=water\n'
        f'exec {shlex.quote(str(SCRIPT))} --mode="$mode" "$@"\n'
    )
    LAUNCHER.chmod(0o755)


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
    # drop a trailing standalone "--" left over from `multi.sh -- vaper-meter`
    while out and out[-1] == "--":
        out.pop()
    return shlex.join(out)


def compose(cmd: str) -> str:
    """Splice vaper into a chain command: heal if vaper is already there,
    else append at the innermost position."""
    if "vaper-meter" in cmd:
        return repoint(cmd, str(LAUNCHER))
    if cmd.strip():
        return cmd + " " + shlex.quote(str(LAUNCHER))
    return str(LAUNCHER)


# ---- chain owners --------------------------------------------------------

def read_settings_cmd() -> tuple[dict, dict, str]:
    """Return (full settings dict, statusLine block, command string)."""
    data: dict = {}
    if SETTINGS.exists():
        try:
            data = json.loads(SETTINGS.read_text() or "{}")
        except json.JSONDecodeError:
            data = {}
    sl = data.get("statusLine") or {}
    return data, sl, sl.get("command", "")


def write_settings_cmd(data: dict, sl: dict, new_cmd: str) -> None:
    new_sl = {"type": sl.get("type", "command"), "command": new_cmd}
    for k, v in sl.items():
        if k not in ("type", "command"):
            new_sl[k] = v
    if "padding" not in new_sl and not sl:
        new_sl["padding"] = 1
    data["statusLine"] = new_sl
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(data, indent=2) + "\n")


def read_wrapped_cmd() -> str:
    try:
        return WRAPPED.read_text().strip()
    except FileNotFoundError:
        return ""


def write_wrapped_cmd(new_cmd: str) -> None:
    WRAPPED.parent.mkdir(parents=True, exist_ok=True)
    WRAPPED.write_text(new_cmd + "\n")


# ---- operations ----------------------------------------------------------

def install() -> None:
    """Compose vaper into whichever chain owner is in front."""
    if WRAPPED.exists():
        # Personas owns settings.json. Write to the wrapped chain.
        old = read_wrapped_cmd()
        new = compose(old)
        if new != old:
            write_wrapped_cmd(new)
        return

    data, sl, cmd = read_settings_cmd()
    new_cmd = compose(cmd)
    if new_cmd == cmd and sl.get("type") == "command":
        return
    write_settings_cmd(data, sl, new_cmd)


def heal() -> None:
    """Re-point any vaper-meter token in either chain owner."""
    if WRAPPED.exists():
        old = read_wrapped_cmd()
        if "vaper-meter" in old:
            new = repoint(old, str(LAUNCHER))
            if new != old:
                write_wrapped_cmd(new)

    data, sl, cmd = read_settings_cmd()
    if cmd and "vaper-meter" in cmd:
        new_cmd = repoint(cmd, str(LAUNCHER))
        if new_cmd != cmd:
            data["statusLine"] = {**sl, "command": new_cmd}
            SETTINGS.write_text(json.dumps(data, indent=2) + "\n")


def uninstall() -> None:
    try:
        LAUNCHER.unlink()
    except FileNotFoundError:
        pass

    if WRAPPED.exists():
        old = read_wrapped_cmd()
        if "vaper-meter" in old:
            new = strip_vaper(old).strip()
            if new:
                write_wrapped_cmd(new)
            else:
                # Leave the file in place but empty so personas knows
                # it's still wrapping (just with no inner content).
                WRAPPED.write_text("")

    data, sl, cmd = read_settings_cmd()
    if cmd and "vaper-meter" in cmd:
        new_cmd = strip_vaper(cmd).strip()
        if not new_cmd:
            data.pop("statusLine", None)
        else:
            data["statusLine"] = {**sl, "command": new_cmd}
        SETTINGS.write_text(json.dumps(data, indent=2) + "\n")


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
