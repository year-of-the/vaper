#!/usr/bin/env python3
"""
vaper — Claude Code status line widget.

Prints one line: how much water you've "boiled" with Claude today (heated from
ROOM_TEMP_C to BOIL_TEMP_C), based on summing all of today's token usage
across every Claude Code session on this machine and converting it to
joules via per-token-type energy coefficients.

Today = since local midnight. Scope = every project under ~/.claude/projects.

It reads stdin (Claude Code passes a session JSON object to status line
scripts) but does not use any of it — the script gets all data from
on-disk session transcripts.

The energy coefficients below are estimates, not measurements. Anthropic
does not publish per-token energy figures; the defaults are middle-of-road
values for an Opus-class model derived from public LLM-energy research:
  - Patterson et al. 2021 (GPT-3 inference energy)
  - Luccioni et al. 2023 (text generation energy)
  - EPRI 2024 (per-query estimates for ChatGPT-class models)
Tune the four constants below to match your own beliefs.
"""

import glob
import json
import os
import sys
from datetime import datetime

# ---- tunables -------------------------------------------------------------

# Joules per token, by type. Output tokens are dominant: each one needs a
# full forward pass through the model. Input/cache_creation tokens go
# through the same compute path but in parallel (prefill), so they're
# roughly 5x cheaper per token. Cache reads are mostly memory I/O — the
# attention KV cache is already populated — so they're another ~20x cheaper.
J_PER_OUTPUT_TOKEN          = 3.0
J_PER_INPUT_TOKEN           = 0.6
J_PER_CACHE_CREATION_TOKEN  = 0.6
J_PER_CACHE_READ_TOKEN      = 0.03

# Water heating math. Specific heat of water is ~4.186 J/(g·K), and 1 mL
# of water is ~1 g. ΔT is BOIL_TEMP_C − ROOM_TEMP_C. Note: this is energy
# to *heat* water to boiling, not to vaporize it (vaporization needs an
# extra ~2260 J/g of latent heat).
SPECIFIC_HEAT_J_PER_G_K = 4.186
ROOM_TEMP_C             = 20
BOIL_TEMP_C             = 100
J_PER_ML = SPECIFIC_HEAT_J_PER_G_K * (BOIL_TEMP_C - ROOM_TEMP_C)  # 334.88

# Where Claude Code stores per-session transcripts. Each session is one
# JSONL file; assistant messages carry message.usage with token counts.
SESSIONS_GLOB = os.path.expanduser("~/.claude/projects/*/*.jsonl")


def local_midnight_epoch() -> float:
    """UNIX epoch seconds at the most recent local midnight."""
    now = datetime.now().astimezone()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.timestamp()


def parse_iso_timestamp(ts: str) -> float:
    """Convert an ISO-8601 timestamp (with trailing Z) to epoch seconds."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def sum_todays_tokens(midnight: float) -> dict:
    """Walk all session files modified since `midnight` and sum tokens."""
    totals = {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}

    for path in glob.glob(SESSIONS_GLOB):
        # mtime prefilter: skip files untouched today. This is the single
        # most important optimization — most of the ~110+ historical files
        # never get opened.
        try:
            if os.path.getmtime(path) < midnight:
                continue
        except OSError:
            continue

        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        msg = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        # Half-written final lines are normal during a
                        # live session — just skip them.
                        continue

                    if msg.get("type") != "assistant":
                        continue

                    ts = msg.get("timestamp")
                    if not ts:
                        continue
                    try:
                        if parse_iso_timestamp(ts) < midnight:
                            continue
                    except ValueError:
                        continue

                    usage = msg.get("message", {}).get("usage") or {}
                    totals["input"]          += usage.get("input_tokens", 0) or 0
                    totals["output"]         += usage.get("output_tokens", 0) or 0
                    totals["cache_creation"] += usage.get("cache_creation_input_tokens", 0) or 0
                    totals["cache_read"]     += usage.get("cache_read_input_tokens", 0) or 0
        except OSError:
            continue

    return totals


def joules_for(totals: dict) -> float:
    return (
        totals["output"]         * J_PER_OUTPUT_TOKEN
        + totals["input"]        * J_PER_INPUT_TOKEN
        + totals["cache_creation"] * J_PER_CACHE_CREATION_TOKEN
        + totals["cache_read"]   * J_PER_CACHE_READ_TOKEN
    )


def format_water(ml: float) -> str:
    if ml >= 1000:
        return f"🚬💧 {ml / 1000:.2f} L boiled today"
    if ml >= 10:
        return f"🚬💧 {ml:.0f} mL boiled today"
    return f"🚬💧 {ml:.1f} mL boiled today"


def main() -> int:
    # Drain stdin so Claude Code's writer doesn't block. We don't use the
    # session JSON for anything — all data comes from on-disk transcripts.
    try:
        sys.stdin.read()
    except Exception:
        pass

    try:
        midnight = local_midnight_epoch()
        totals = sum_todays_tokens(midnight)
        ml = joules_for(totals) / J_PER_ML
        print(format_water(ml))
    except Exception:
        # Never crash the status line. A widget that disappears is worse
        # than one that says "I don't know".
        print("🚬💧 — boiled today")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
