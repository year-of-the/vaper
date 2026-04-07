# vaper

A Claude Code status line widget that shows how much water you've "boiled" with Claude today.

```
🚬💧 13.61 L boiled today
```

It scans your Claude Code session transcripts on disk, sums today's token usage across every project, multiplies by per-token-type joule estimates, and divides by the energy needed to heat 1 mL of water from 20°C to 100°C (≈ 334.88 J).

## Install

### 1. Add the marketplace and install the plugin

In Claude Code:

```
/plugin marketplace add year-of-the/vaper
/plugin install vaper@vaper
```

The plugin gets cached at `~/.claude/plugins/cache/vaper/vaper/<version>/`.

### 2. Wire up the status line

Plugins can't auto-configure status lines yet — Claude Code only honors the `agent` key in plugin-bundled settings, so you have to point your own `~/.claude/settings.json` at the script. The install path is version-tied, so the cleanest way to do it once is a tiny wrapper that always finds the latest installed version:

```sh
mkdir -p ~/.local/bin
cat > ~/.local/bin/vaper-meter << 'EOF'
#!/bin/sh
exec "$(find ~/.claude/plugins/cache -path '*vaper*scripts/water-meter.py' 2>/dev/null | sort | tail -1)"
EOF
chmod +x ~/.local/bin/vaper-meter
```

Then add this to `~/.claude/settings.json` (merge with existing keys):

```json
{
  "statusLine": {
    "type": "command",
    "command": "/Users/YOU/.local/bin/vaper-meter",
    "padding": 1
  }
}
```

Replace `/Users/YOU` with your actual home path (Claude Code's status line command field doesn't expand `~` or `$HOME`).

Restart Claude Code or run `/statusline`. The widget should appear at the bottom and refresh after every turn.

## Tuning

The four energy coefficients are constants at the top of `scripts/water-meter.py`. Open the installed copy and edit them in place:

| Constant | Default | Meaning |
| --- | --- | --- |
| `J_PER_OUTPUT_TOKEN` | `3.0` | Each generated token needs a full forward pass — dominant cost. |
| `J_PER_INPUT_TOKEN` | `0.6` | Prefill is parallelized, so input tokens are ~5× cheaper than output. |
| `J_PER_CACHE_CREATION_TOKEN` | `0.6` | Same compute path as fresh input. |
| `J_PER_CACHE_READ_TOKEN` | `0.03` | Mostly memory I/O — the KV cache is already populated. |

Bigger numbers = bigger meter. Smaller numbers = smaller meter. They are estimates, not measurements (see *Caveats*).

## How it works

Claude Code already writes every session as JSONL under `~/.claude/projects/<project>/<session-id>.jsonl`, and every assistant message line carries `message.usage` with input/output/cache token counts and an ISO timestamp. The script:

1. Computes the local-midnight cutoff.
2. Globs all session files, fast-skipping any whose mtime is older than today.
3. Reads remaining files line-by-line, summing today's tokens by category.
4. Multiplies by the per-type joule coefficients above.
5. Divides total joules by 334.88 J/mL to get milliliters of water heated.
6. Prints one line, auto-formatting between mL and L.

A full scan takes ~25 ms on a busy day; the status line debounce is 300 ms.

## Caveats

- The energy coefficients are **estimates**, derived from public LLM-energy research (Patterson 2021, Luccioni 2023, EPRI 2024). Anthropic does not publish per-token figures. If you have better numbers, edit the constants.
- "Boiled" here means *heated to 100°C*, not vaporized. Actually vaporizing the water would need an extra ~2260 J/g of latent heat — roughly 7× more energy than just bringing it to a boil.
- Scope is **all projects on this machine**. If you only want one project, change `SESSIONS_GLOB` in the script.
- "Today" is **local midnight**.
- Status line wiring is manual because plugin-bundled `settings.json` only honors the `agent` key as of Claude Code 2.x. If/when status line auto-config lands, this README will get shorter.

## Develop

To work on the plugin locally:

```
git clone https://github.com/year-of-the/vaper
cd vaper
chmod +x scripts/water-meter.py
echo '{}' | scripts/water-meter.py    # should print "🚬💧 ... boiled today"
```

For a tighter dev loop, point `statusLine.command` at the absolute path of the cloned `scripts/water-meter.py` instead of the wrapper. No marketplace install needed.

## License

MIT.
