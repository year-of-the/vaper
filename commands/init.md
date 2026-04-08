# Initialize vaper

The user invoked `/vaper:init`. Set up vaper's status line widget in water mode (default), with no further questions. Execute the entire procedure end-to-end and report. Do **not** ask the user anything — overwrite any existing `statusLine` block in `~/.claude/settings.json` if there is one, regardless of what it points at.

## Steps

1. **Locate the installed water-meter.py:**

   ```sh
   find ~/.claude/plugins/cache -path '*vaper*scripts/water-meter.py' 2>/dev/null | sort -V | tail -1
   ```

   Exactly one path should come back. If empty, print `vaper isn't installed; run /plugin install vaper first` and stop.

2. **Create the stable wrapper at `~/.local/bin/vaper-meter`** so the path survives `/plugin update`. Idempotent — rewrite if it already exists. The wrapper re-finds the latest installed `water-meter.py` on each call and forwards CLI args:

   ```sh
   mkdir -p ~/.local/bin
   cat > ~/.local/bin/vaper-meter << 'EOF'
   #!/bin/sh
   exec "$(find ~/.claude/plugins/cache -path '*vaper*scripts/water-meter.py' 2>/dev/null | sort -V | tail -1)" "$@"
   EOF
   chmod +x ~/.local/bin/vaper-meter
   ```

   Resolve `~/.local/bin/vaper-meter` to its absolute path (e.g. `/Users/<them>/.local/bin/vaper-meter`) — Claude Code's `statusLine.command` field doesn't expand `~` or `$HOME`.

3. **Read `~/.claude/settings.json`.** If it doesn't exist, treat it as `{}`. Parse as JSON.

4. **Set the `statusLine` block** to point at the wrapper, water mode (no `--mode` flag — water is the default and omitting the flag keeps the command stable):

   ```json
   "statusLine": {
     "type": "command",
     "command": "<absolute wrapper path>",
     "padding": 1
   }
   ```

   - **Overwrite any existing `statusLine` block**, whatever it points at, without asking. The user explicitly opted into this when they ran `/vaper:init`.
   - **Preserve every other top-level key** in `settings.json` exactly as it was.

5. **Write the merged file back** with 2-space indent and a trailing newline (or whatever formatting `settings.json` already had, if you can tell).

6. **Print exactly these four lines and nothing else:**

   ```
   vaper installed in water mode. Restart Claude Code to see the banner.
   Switch modes with:
     /vaper:mode <name>
   Modes: water (default), calories, bullets, btc.
   ```
