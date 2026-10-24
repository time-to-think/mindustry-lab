#!/usr/bin/env python3
"""Analyze existing logs without contacting the game or a model provider."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mindustry_agent.latency import analyze


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Team JSONL run logs; shell globs are supported.")
    parser.add_argument("--json", action="store_true", help="Write machine-readable aggregate statistics.")
    args = parser.parse_args()
    try:
        report = analyze(args.paths)
    except (OSError, UnicodeError) as error:
        parser.error(str(error))
    if args.json:
        print(json.dumps(report, indent=2, allow_nan=False))
        return
    print("Metric: llm_latency_seconds (seconds); not total decision-to-action latency")
    print("Diagnostics: " + json.dumps(report["diagnostics"], sort_keys=True))
    for group in report["groups"]:
        identity = {key: group[key] for key in ("experiment", "run", "episode", "model", "team", "mode", "outcome", "repair")}
        # JSON escaping prevents terminal control characters in identifiers.
        print(json.dumps(identity, ensure_ascii=True))
        print("  seconds: " + json.dumps(group["latency_seconds"], sort_keys=True))
        print(f"  records={group['records']} missing={group['missing_latency']} invalid={group['invalid_latency']}")


if __name__ == "__main__":
    main()
