# Switch vaper mode

The user invoked `/vaper:mode $ARGUMENTS`. Switch vaper's display mode to `$ARGUMENTS` and report. Execute end-to-end with no questions.

## Steps

1. **Validate `$ARGUMENTS`** is one of: `water`, `calories`, `bullets`, `btc`. If it isn't (or is empty), print `unknown mode: $ARGUMENTS — valid: water | calories | bullets | btc` and stop.

2. **Read `~/.claude/settings.json`** and find `statusLine.command`. If the file doesn't exist, or the command field doesn't reference the vaper wrapper (`vaper-meter` somewhere in the path), print `vaper isn't set up; run /vaper:init first` and stop.

3. **Rewrite only the `command` field** of the `statusLine` block:

   - For `water` (the default), set the command to the wrapper absolute path with **no** `--mode` flag.
   - For `calories`, `bullets`, or `btc`, set the command to the wrapper absolute path followed by `--mode=$ARGUMENTS`.
   - Leave `type`, `padding`, and every other top-level key in `settings.json` untouched.

4. **Write the file back** with the same formatting it already had (2-space indent, trailing newline).

5. **Print exactly:** `vaper switched to $ARGUMENTS 🤩`
