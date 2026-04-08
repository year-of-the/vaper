#!/usr/bin/env python3
"""
vaper — Claude Code status line widget.

Prints one line: today's Claude Code token energy converted into one
of four absurd units. The same joule total drives four interchangeable
modes, picked via --mode=<name>:

  water    (default) — mL/L of water heated from 20°C and vaporized
  calories            — Big Macs (or kcal under 1 Big Mac) of food energy
  bullets             — 9mm rounds, chemical energy of the propellant
  btc                 — BTC mined back when 2010-era CPUs could do it

The joule total comes from summing today's token usage across every
Claude Code session on this machine and multiplying by per-token-type
joule coefficients; each mode just divides that total by a different
denominator. Today = since local midnight. Scope = every project
under ~/.claude/projects.

It reads stdin (Claude Code passes a session JSON object to status line
scripts) but does not use any of it — the script gets all data from
on-disk session transcripts.

The energy coefficients below are estimates, not measurements. Anthropic
does not publish per-token energy figures; the defaults are middle-of-road
values for an Opus-class model derived from public LLM-energy research:
  - Patterson et al. 2021 (GPT-3 inference energy)
  - Luccioni et al. 2023 (text generation energy)
  - EPRI 2024 (per-query estimates for ChatGPT-class models)
Tune the four token constants and four mode constants to match your
own beliefs.
"""

import argparse
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

# Water boiling math. To fully boil 1 g (≈ 1 mL) of water from room
# temperature, we need TWO things: bring it to 100°C, then vaporize it.
#   sensible heat:  c · ΔT  =  4.186 J/(g·K) · 80 K  ≈   334.88 J/g
#   latent heat:    L_vap                            ≈  2257    J/g
#   total:                                               2591.88 J/g
# (Latent heat dominates by ~7×, which is why a kettle full of water
# at 99°C still takes ages to actually boil away.)
SPECIFIC_HEAT_J_PER_G_K          = 4.186
LATENT_HEAT_VAPORIZATION_J_PER_G = 2257
ROOM_TEMP_C                      = 20
BOIL_TEMP_C                      = 100
J_PER_ML = (
    SPECIFIC_HEAT_J_PER_G_K * (BOIL_TEMP_C - ROOM_TEMP_C)
    + LATENT_HEAT_VAPORIZATION_J_PER_G
)  # 2591.88

# ---- mode constants ------------------------------------------------------
# Each mode divides the same joules total by a different denominator.

# Heat / food calories. 1 food Calorie = 1 kcal = 4184 J.
J_PER_KCAL    = 4184
J_PER_BIG_MAC = J_PER_KCAL * 563   # 563 kcal per Big Mac → 2,355,592 J

# 9mm Luger, *chemical* energy of the propellant when the round goes off.
# A typical 115 gr load uses 6 grains of smokeless powder; smokeless
# powder energy density is 5 kJ/g, so one round releases:
#   6 gr × 0.0648 g/gr × 5000 J/g  =  1944 J
# Only 25% of that ends up as kinetic energy in the bullet (muzzle
# energy is about 480 J for the same load) — the rest goes to heat,
# gas expansion, sound, and muzzle flash. We use the chemical figure
# because the mode is named "detonated", not "fired".
J_PER_9MM_ROUND = 1944

# Bitcoin mined in 2010. Difficulty grew 14,000× during 2010 as mining
# moved from CPUs to early GPUs, so per-BTC energy varied wildly across
# the year. 1 kWh = 3.6 MJ is a defensible mid-2010 figure and produces
# the satisfyingly absurd "you could have mined several whole bitcoin"
# comparison this mode is here to deliver.
J_PER_BTC_2010 = 3_600_000

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


def format_water(joules: float) -> str:
    ml = joules / J_PER_ML
    if ml >= 1000:
        return f"🚬💧 {ml / 1000:.2f} L boiled today"
    if ml >= 10:
        return f"🚬💧 {ml:.0f} mL boiled today"
    return f"🚬💧 {ml:.1f} mL boiled today"


def format_calories(joules: float) -> str:
    big_macs = joules / J_PER_BIG_MAC
    if big_macs < 1:
        # Tiny days: show raw kcal so the number isn't just "0.3 Big Macs".
        return f"🫦🍔 {joules / J_PER_KCAL:.0f} kcal consumed today"
    if big_macs >= 100:
        return f"🫦🍔 {big_macs:.0f} Big Macs' calories burned today"
    return f"🫦🍔 {big_macs:.1f} Big Macs' calories burned today"


def format_bullets(joules: float) -> str:
    rounds = joules / J_PER_9MM_ROUND
    if rounds < 1:
        return "💥🔫 0 9mm rounds today"
    if rounds < 2:
        return "💥🔫 1 9mm round today"
    return f"💥🔫 {rounds:,.0f} 9mm rounds today"


def format_btc(joules: float) -> str:
    btc = joules / J_PER_BTC_2010
    if btc < 0.01:
        # Underflow tier: show in mBTC so the number isn't just "0.00 BTC".
        return f"🤞₿ {btc * 1000:.1f} mBTC (2010) mined today"
    return f"🤞₿ {btc:.2f} BTC (2010) mined today"


MODES = {
    "water":    format_water,
    "calories": format_calories,
    "bullets":  format_bullets,
    "btc":      format_btc,
}
DEFAULT_MODE = "water"


def main() -> int:
    # Drain stdin so Claude Code's writer doesn't block. We don't use the
    # session JSON for anything — all data comes from on-disk transcripts.
    try:
        sys.stdin.read()
    except Exception:
        pass

    # Parse --mode. On any failure (unknown choice, malformed args), fall
    # back to the default mode rather than letting argparse exit — same
    # philosophy as the broader exception handler below.
    mode = DEFAULT_MODE
    try:
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--mode", choices=list(MODES), default=DEFAULT_MODE)
        args, _ = parser.parse_known_args()
        mode = args.mode
    except SystemExit:
        mode = DEFAULT_MODE
    except Exception:
        mode = DEFAULT_MODE

    try:
        midnight = local_midnight_epoch()
        totals = sum_todays_tokens(midnight)
        joules = joules_for(totals)
        print(MODES[mode](joules))
    except Exception:
        # Never crash the status line. A widget that disappears is worse
        # than one that says "I don't know".
        print("🚬💧 — boiled today")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
