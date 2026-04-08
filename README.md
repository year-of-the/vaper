# vaper

A Claude Code status line widget that converts today's token energy into one of four absurd units: water boiled, Big Macs, 9mm rounds, or 2010-era BTC mined.

```
🚬💧 7.63 L boiled today              # default
🫦🍔 8.4 Big Macs consumed today      # --mode=calories
💥🔫 10,170 9mm rounds today          # --mode=bullets
🤞₿ 5.49 BTC (2010) mined today       # --mode=btc
```

It scans your Claude Code session transcripts on disk, sums today's token usage across every project, multiplies by per-token-type joule estimates to get a total energy in joules, then divides by the chosen mode's denominator. Same joule total, four different jokes — switch modes with `/vaper:mode <name>`.

## Install

```
/plugin install vaper
/vaper:init
```

`/vaper:init` finds the installed `water-meter.py`, drops a stable wrapper at `~/.local/bin/vaper-meter` so future `/plugin update`s don't break the path, and adds a `statusLine` block to your `~/.claude/settings.json` pointing at the wrapper. It runs in **water mode by default**, asks no questions, and overwrites any existing `statusLine` block.

Restart Claude Code and the widget appears at the bottom of the screen, refreshing on its own after every assistant turn.

## Modes

Same joules total, four different jokes. Switch with `/vaper:mode <name>`:

```
/vaper:mode water
/vaper:mode calories
/vaper:mode bullets
/vaper:mode btc
```

| Mode | What it shows | Constant |
| --- | --- | --- |
| `water` (default) | mL/L of water heated from 20°C and fully vaporized | 2,592 J/mL |
| `calories` | Big Macs of food energy (or kcal under 1 Big Mac) | 2.36 MJ/Big Mac |
| `bullets` | 9mm rounds' worth of chemical energy (powder, not muzzle) | 1,944 J/round |
| `btc` | BTC you could have mined in 2010 with that energy | 3.6 MJ/BTC (1 kWh) |

All four numbers come from the same joules total — different denominators, same energy. The constants are tunable in `scripts/water-meter.py` if you have stronger opinions about powder loads or 2010 mining hash rates.

## Manage

While installed, you can pause and resume the widget without uninstalling:

| Command | Effect |
| --- | --- |
| `/plugin` | Opens the four-tab UI: Discover, Installed, Marketplaces, Errors |
| `/plugin disable vaper` | Pauses the plugin (cache stays on disk) |
| `/plugin enable vaper` | Resumes a previously disabled plugin |
| `/reload-plugins` | Picks up changes after editing the script in `~/.claude/plugins/cache/...` without restarting |

There are `claude plugin <cmd>` CLI equivalents (`claude plugin disable vaper`, etc.) for shell scripts.

## Uninstall

```
/plugin uninstall vaper
```

This removes the plugin and its cache at `~/.claude/plugins/cache/vaper/...` automatically. To also tear down what `/vaper:init` wired in:

1. Delete the `statusLine` block from `~/.claude/settings.json`.
2. `rm ~/.local/bin/vaper-meter`

Restart Claude Code and the widget is gone. Nothing else lingers — no temp files, no daemons, no global git config, no hooks.

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
4. Multiplies by the per-type joule coefficients above to get a total in joules.
5. Divides that total by the chosen mode's denominator — 2591.88 J/mL for water (sensible heat 20°C → 100°C plus latent heat of vaporization), 2,355,592 J/Big Mac for calories, 1944 J for bullets, 3.6 MJ for btc.
6. Prints one line, auto-formatting between sub-units (mL/L, kcal/Big Macs, mBTC/BTC) as the magnitude grows.

A full scan takes ~25 ms on a busy day; the status line debounce is 300 ms.

## Caveats

- The energy coefficients are **estimates**, derived from public LLM-energy research (Patterson 2021, Luccioni 2023, EPRI 2024). Anthropic does not publish per-token figures. If you have better numbers, edit the constants.
- Scope is **all projects on this machine**. If you only want one project, change `SESSIONS_GLOB` in the script.
- "Today" is **local midnight**.

## Privacy

vaper runs entirely on your local machine. It reads Claude Code's session transcript files at `~/.claude/projects/*/*.jsonl` — files Claude Code already writes locally for its own use — and sums today's token counts.

- It transmits **nothing** to any server, ever.
- It collects no telemetry, analytics, or usage stats.
- It has no network code: no `requests`, no `urllib`, no sockets.
- The displayed value is computed locally and never leaves your machine.
- It writes nothing to disk and creates no files of its own.

The whole script is at [`scripts/water-meter.py`](scripts/water-meter.py).

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

MIT — see [LICENSE](LICENSE).
