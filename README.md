# vaper

A Claude Code status line widget that shows how much water you've "boiled" with Claude today.

```
🚬💧 13.61 L boiled today
```

It scans your Claude Code session transcripts on disk, sums today's token usage across every project, multiplies by per-token-type joule estimates, and divides by the energy needed to fully boil 1 mL of water — heat it from 20°C to 100°C and vaporize it (≈ 2592 J).

## Install

```
/plugin install vaper
/vaper:setup
```

`/vaper:setup` is a skill that ships with the plugin. It finds the installed `water-meter.py`, drops a stable wrapper at `~/.local/bin/vaper-meter` so future `/plugin update`s don't break the path, and adds a `statusLine` block to your `~/.claude/settings.json` pointing at it. It asks before touching any existing config.

After it finishes, run `/statusline` (or restart Claude Code) and the widget appears at the bottom of the screen, refreshing after every assistant turn.

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

This removes the plugin and its cache at `~/.claude/plugins/cache/vaper/...` automatically. To also tear down what `/vaper:setup` wired in:

1. Delete the `statusLine` block from `~/.claude/settings.json`.
2. `rm ~/.local/bin/vaper-meter`

Restart or run `/statusline` and the widget is gone. Nothing else lingers — no temp files, no daemons, no global git config, no hooks.

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
5. Divides total joules by 2591.88 J/mL (sensible heat from 20°C to 100°C plus latent heat of vaporization) to get milliliters of water actually boiled away.
6. Prints one line, auto-formatting between mL and L.

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
- The displayed water-boiled value is computed locally and never leaves your machine.
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
