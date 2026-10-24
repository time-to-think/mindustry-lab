"""Offline statistics for team JSONL logs; never echo payloads or error messages."""
from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any
import json


def statistics(values: list[float]) -> dict[str, Any]:
    """Use the nearest-rank percentile, including for single-sample groups."""
    ordered = sorted(values)
    if not ordered:
        return {"count": 0, "mean": None, "p50": None, "p95": None, "min": None, "max": None}
    return {"count": len(ordered), "mean": mean(ordered), "p50": mean(ordered[(len(ordered) - 1) // 2:len(ordered) // 2 + 1]),
            "p95": ordered[math.ceil(0.95 * len(ordered)) - 1],
            "min": ordered[0], "max": ordered[-1]}


def duration(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def label(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and value else fallback


def analyze(paths: list[Path]) -> dict[str, Any]:
    diagnostics: Counter = Counter(lines=0, malformed=0, ignored=0, decisions=0,
                                    missing_latency=0, invalid_latency=0)
    groups: dict[tuple, dict[str, Any]] = {}
    for source_index, path in enumerate(paths, 1):
        context: dict[str, Any] = {}
        session_index = 0
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                diagnostics["lines"] += 1
                try:
                    record = json.loads(line)
                except (ValueError, RecursionError):
                    diagnostics["malformed"] += 1
                    continue
                if not isinstance(record, dict):
                    diagnostics["malformed"] += 1
                    continue
                kind = record.get("kind")
                if kind == "run_start":
                    session_index += 1
                    context = record
                    diagnostics["ignored"] += 1
                    continue
                if kind not in ("turn", "turn_error") and not (
                    kind == "run_end" and "discarded_decision" in record
                ):
                    diagnostics["ignored"] += 1
                    continue
                diagnostics["decisions"] += 1
                def field(name: str) -> Any:
                    return record.get(name, context.get(name))
                state = record.get("state")
                episode = field("episode_id")
                if episode is None and isinstance(state, dict):
                    episode = state.get("episode_id")
                response = record.get("action_response")
                response = response if isinstance(response, dict) else {}
                results = response.get("results")
                outcome = "failed" if kind == "turn_error" else "discarded" if kind == "run_end" else "completed"
                if kind == "turn" and response.get("ok") is False:
                    outcome = "action_rejected"
                elif kind == "turn" and isinstance(results, list) and any(
                    isinstance(item, dict) and item.get("ok") is False for item in results
                ):
                    outcome = "action_partial_failure"
                mode = "dry_run" if field("dry_run") is True or response.get("dry_run") is True else (
                    "live" if field("dry_run") is False else "unknown")
                repair = record.get("llm_json_repair_attempted")
                repair = "yes" if repair is True else "no" if repair is False else "unknown"
                identity = {"experiment": label(field("experiment_id"), f"input-{source_index}"),
                            "run": f"input-{source_index}:session-{session_index}",
                            "episode": label(episode, "unknown"),
                            "model": label(field("model"), "unknown"),
                            "team": label(field("team"), "unknown"),
                            "mode": mode, "outcome": outcome, "repair": repair}
                key = tuple(identity.values())
                if key not in groups:
                    groups[key] = {**identity, "records": 0, "missing_latency": 0,
                                   "invalid_latency": 0, "values": [], "stages": {}}
                group = groups[key]
                group["records"] += 1
                value = record.get("llm_latency_seconds")
                if value is None:
                    group["missing_latency"] += 1
                    diagnostics["missing_latency"] += 1
                elif not duration(value):
                    group["invalid_latency"] += 1
                    diagnostics["invalid_latency"] += 1
                else:
                    group["values"].append(value)
                timing = record.get("python_timing")
                if isinstance(timing, dict):
                    stages = timing.get("stages_seconds")
                    if isinstance(stages, dict):
                        # Restrict output to known stage names, never arbitrary log keys.
                        for name in ("state_retrieval", "state_compaction", "llm_decide",
                                     "action_preparation", "state_revalidation", "execution_compaction", "action_submission"):
                            value = stages.get(name)
                            if duration(value):
                                group["stages"].setdefault(name, []).append(value)
                    if duration(timing.get("elapsed_seconds")):
                        group["stages"].setdefault("observe_to_log_record", []).append(timing["elapsed_seconds"])
    output = []
    for key in sorted(groups):
        group = groups[key]
        values, stages = group.pop("values"), group.pop("stages")
        output.append({**group, "latency_seconds": statistics(values),
                       "python_stage_seconds": {name: statistics(samples) for name, samples in sorted(stages.items())}})
    return {"schema_version": 1, "metric": "llm_latency_seconds", "percentile_method": "nearest-rank p95; median p50",
            "diagnostics": dict(diagnostics), "groups": output}
