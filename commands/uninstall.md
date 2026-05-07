# Uninstall vaper

The user invoked `/vaper:uninstall`. Run the uninstaller and print its output verbatim. Do not ask the user anything; do not edit any files yourself.

```sh
"${CLAUDE_PLUGIN_ROOT}/scripts/install.py" --uninstall
```

The script removes vaper from `~/.claude/settings.json` (preserving any wrapper around it) and deletes the launcher. After it succeeds, the user can run `/plugin uninstall vaper` to remove the plugin itself.
