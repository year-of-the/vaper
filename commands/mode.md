# Switch vaper mode

The user invoked `/vaper:mode $ARGUMENTS`. Switch vaper's display mode to `$ARGUMENTS` and report. Execute end-to-end with no questions.

`statusLine.command` is a wrapper chain shared with other statusline plugins — see `/vaper:init` for the convention. Vaper's segment is the token ending in `/vaper-meter` plus any immediately-following `--mode=<name>` token. This command updates only that segment; it must not touch other segments in the chain.

## Steps

1. **Validate `$ARGUMENTS`** is one of: `water`, `calories`, `bullets`, `btc`. If it isn't (or is empty), print `unknown mode: $ARGUMENTS — valid: water | calories | bullets | btc` and stop.

2. **Read `~/.claude/settings.json`** and find `statusLine.command`. If the file doesn't exist, or the command field doesn't contain a token ending in `/vaper-meter`, print `vaper isn't set up; run /vaper:init first` and stop.

3. **Update only vaper's segment in `statusLine.command`:**

   - Locate the token ending in `/vaper-meter`. Include any immediately-following `--mode=<value>` token as part of the segment.
   - For `water` (the default), replace the segment with `<vaper-path>` — no mode flag.
   - For `calories`, `bullets`, or `btc`, replace the segment with `<vaper-path> --mode=$ARGUMENTS`.
   - Leave every other token in the command intact (wrapper scripts, segments from other plugins, any custom content). Leave `type`, `padding`, and every other top-level key in `settings.json` untouched.

4. **Write the file back** with the same formatting it already had (2-space indent, trailing newline).

5. **Print exactly:** `vaper switched to $ARGUMENTS 🤩`
