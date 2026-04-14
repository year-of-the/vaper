# Initialize vaper

The user invoked `/vaper:init`. Set up vaper's status line widget in water mode (default), with no further questions. Execute the entire procedure end-to-end and report. Do **not** ask the user anything.

## The statusLine is a shared resource

Claude Code's `statusLine.command` is a single string, but multiple plugins want to contribute to it. The convention we follow here (and that other plugins like `principled-mode` follow): treat `statusLine.command` as a **wrapper chain** of the form `wrapper-N ... wrapper-1 inner [inner-args...]`. Each wrapper is an executable path that takes the rest of the chain as positional arguments, runs them, and transforms the output. Each plugin owns one segment of this chain and only adds, updates, or removes **its own segment** — never someone else's.

Vaper is the **inner command** of the chain — it produces content from scratch (no input). Its segment is the token ending in `/vaper-meter` plus any immediately-following `--mode=<name>` token. Vaper must sit at the innermost (end) position of the chain, because a wrapper needs something to wrap.

The steps below preserve other plugins' wrapper segments. If you overwrite the chain, you break every other statusline plugin the user has installed.

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

4. **Merge the `statusLine` block** to place vaper's segment in the innermost position, preserving any wrapper chain already set up by other plugins:

   - **If `.statusLine.command` is unset or empty:** set the block to
     ```json
     "statusLine": { "type": "command", "command": "<wrapper-absolute-path>", "padding": 1 }
     ```
   - **If `.statusLine.command` already contains a token ending in `/vaper-meter`:** find that token plus any immediately-following `--mode=<value>` token, and replace that span with `<wrapper-absolute-path>` (no mode flag — `/vaper:init` resets to the water default). Leave every other token in the command, and `type` / `padding` / every other top-level key, exactly as they were.
   - **Otherwise (command is set, but has no `/vaper-meter` token):** append ` <wrapper-absolute-path>` to the end of the existing command. This puts vaper at the innermost position of the wrapper chain. Leave `type`, `padding`, and every other top-level key exactly as they were.

5. **Write the merged file back** with 2-space indent and a trailing newline (or whatever formatting `settings.json` already had, if you can tell).

6. **Print exactly these four lines and nothing else:**

   ```
   vaper installed in water mode. Restart Claude Code to see the banner.
   Switch modes with:
     /vaper:mode <name>
   Modes: water (default), calories, bullets, btc.
   ```
