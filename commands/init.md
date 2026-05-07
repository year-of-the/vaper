# Initialize vaper

The user invoked `/vaper:init`. Run the installer and print its output verbatim. Do not ask the user anything; do not edit any files yourself; do not paraphrase the script's output.

```sh
"${CLAUDE_PLUGIN_ROOT}/scripts/install.py" --install
```

The script is idempotent. It writes a launcher to `${CLAUDE_PLUGIN_DATA}/vaper-meter` and composes vaper into `~/.claude/settings.json` — preserving any wrapper (e.g. `statusline-multi.sh`) already present.
