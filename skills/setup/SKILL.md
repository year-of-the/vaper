---
name: setup
description: Wire up vaper's status line. Run this once after `/plugin install vaper` to point Claude Code's status line at the installed water-meter.py script.
---

# vaper:setup

You are wiring up vaper's status line widget for the user. The plugin is already installed in `~/.claude/plugins/cache/...` — your job is to point the user's `~/.claude/settings.json` at the installed `water-meter.py` so the widget actually appears.

Plugins cannot ship status line entries directly (Claude Code only honors the `agent` key in plugin-bundled `settings.json`), which is why this skill exists.

## Steps

1. **Locate the installed script.** Run:
   ```sh
   find ~/.claude/plugins/cache -path '*vaper*scripts/water-meter.py' 2>/dev/null | sort -V | tail -1
   ```
   Exactly one path should come back. If empty, the plugin isn't installed — tell the user to run `/plugin install vaper` first and stop.

2. **Create a stable wrapper** at `~/.local/bin/vaper-meter` so the path survives `/plugin update`. The wrapper re-finds the latest installed version on each call:
   ```sh
   mkdir -p ~/.local/bin
   cat > ~/.local/bin/vaper-meter << 'EOF'
   #!/bin/sh
   exec "$(find ~/.claude/plugins/cache -path '*vaper*scripts/water-meter.py' 2>/dev/null | sort -V | tail -1)"
   EOF
   chmod +x ~/.local/bin/vaper-meter
   ```
   Resolve `~/.local/bin/vaper-meter` to its absolute path (e.g. `/Users/<them>/.local/bin/vaper-meter`) for use in step 4 — Claude Code's status line `command` field doesn't expand `~` or `$HOME`.

3. **Read `~/.claude/settings.json`.** If the file doesn't exist, treat it as `{}`. Parse it as JSON.

4. **Add a `statusLine` block** that points at the wrapper:
   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "<absolute path to ~/.local/bin/vaper-meter from step 2>",
       "padding": 1
     }
   }
   ```
   - If `settings.json` already has a `statusLine` key pointing at vaper, tell the user it's already wired up and stop.
   - If it has a `statusLine` key pointing at something else, show the user what's there and ask whether to replace it. **Do not silently overwrite.**
   - Preserve every other top-level key in `settings.json` exactly as it was.

5. **Write the merged file back** with the same formatting (2-space indent, trailing newline) the user already had, if you can tell. If not, default to 2-space indent.

6. **Tell the user** to restart Claude Code. The widget will appear at the bottom of the screen and update on its own after every assistant turn. (Do **not** tell them to run `/statusline` — that's the setup wizard for configuring a status line, not a refresh command, and running it would overwrite the block we just wrote.)

## Uninstall path

If the user later runs `/plugin uninstall vaper`, two things stay behind that this skill created:
- The `statusLine` block in `~/.claude/settings.json`
- The wrapper at `~/.local/bin/vaper-meter`

Both can be removed by hand, or by re-invoking this skill in reverse if you decide to extend it.
