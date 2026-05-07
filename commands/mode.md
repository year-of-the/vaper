# Switch vaper mode

The user invoked `/vaper:mode $ARGUMENTS`. Switch vaper's display mode and report.

If `$ARGUMENTS` (treated as a literal string) is **not** one of `water`, `calories`, `bullets`, or `btc`, print exactly:

```
unknown mode: $ARGUMENTS — valid: water | calories | bullets | btc
```

and stop.

Otherwise, write `$ARGUMENTS` (no trailing newline, create parent dirs if needed) to:

```
${CLAUDE_PLUGIN_DATA}/mode
```

Then print exactly: `vaper switched to $ARGUMENTS 🤩`

Do not edit `~/.claude/settings.json`. Do not run any other commands.
