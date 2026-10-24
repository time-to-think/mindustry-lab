# LLM latency evaluation

Audit baseline: `fb6c3e2` (team develop). Prepared 2026-10-24. This work adds
measurement and offline analysis; it does not establish a latency reduction.

## Execution path and existing measurement

`runner.run` reads `/health` and an initial `/v1/state`, writes `run_start`, then
repeats: state retrieval, episode checks, factual event/backlog updates, state
compaction, `llm.decide`, action normalization, another state/episode check,
execution-time validation, `/v1/action`, logging/feedback, and a delay.

`llm.decide` builds its prompts before its existing `perf_counter` start. Its
`llm_latency_seconds` spans the first `request_json` call through message extraction,
JSON extraction/validation, and an optional second repair request/validation.
It includes HTTP encoding, transport, provider waiting/generation, response JSON
handling and local decision validation. It excludes initial prompt construction,
state retrieval/compaction, action dispatch, usage aggregation after that timer,
logging, and inter-turn waiting. It is neither pure model inference time nor
end-to-end decision latency. Failed calls do not return this legacy metric.

The old `report.summarize` reports a mean and defaults missing latency to zero.
It remains unchanged for compatibility; use the new analyzer for explicit
missing-value and outcome handling.

Potential bottlenecks are large serialized state/prompts, provider/network queues,
generation length, JSON repairs, state endpoint retries (503 backoff), and action
submission. These are hypotheses, not measured rankings. Stockpile RTS waits
0.5 seconds after each completed turn; other modes use the configured/model delay.
Two teams have independent processes, and decisions apply as they arrive. Existing
behavior is preserved; no new prompt, model, strategy, or scheduling policy is used.

## Additive Python timing

`CycleTimer` uses one process's monotonic `perf_counter`, including on exceptions.
The optional-to-read `python_timing` object is added to `turn`, `turn_error`, and
inference-discard `run_end` records. Old log fields retain their meanings.

| Field in `stages_seconds` | Boundary |
| --- | --- |
| `state_retrieval` | Per-turn `game.state`, including its internal retries |
| `state_compaction` | First `compact_state` call |
| `llm_decide` | Whole provider method, including prompt preparation, HTTP, repair, validation and usage handling |
| `action_preparation` | Existing `prepare_decision_actions` |
| `state_revalidation` | Fresh state read immediately before action handling |
| `execution_compaction` | Fresh-state compaction |
| `action_submission` | `game.act` until return or raised exception; absent in dry runs |

`elapsed_seconds` spans the per-turn state read through construction of that log
record, including otherwise uninstrumented Python work. It excludes initial
health/state setup, log writes, post-log feedback, and polling/wait time. It is
named `observe_to_log_record` in analyzer stage summaries. A failed or discarded
cycle has an earlier endpoint; its outcome group stays separate. It does not
prove in-game action completion. Stage statistics have their own coverage counts;
missing stages are not zero. These measurements are always additive in new runs;
existing logs need not contain them.

Separate prompt, HTTP-only, JSON-only, retry-attempt, token-generation and server
execution durations remain unavailable. Do not derive these by subtracting medians
or p95 values. Per-record differences, if studied later, still include timer
boundary/overhead differences. Game ticks and wall time are different clocks;
do not subtract game ticks from Python timestamps or assume a fixed tick rate.

## Offline analysis

```bash
python3 scripts/analyze_llm_latency.py runs/example.jsonl
python3 scripts/analyze_llm_latency.py runs/*.jsonl --json
```

Requires Python 3.10+, standard library only; performs no game/provider requests.
Use unique input files. Repeating an input repeats its samples (no implicit dedup).
JSON output includes groups and diagnostics. Human output summarizes the legacy
latency; stage aggregates are available in JSON.

Grouping: experiment ID if present, otherwise input ordinal; derived run session;
episode, model, team, live/dry/unknown mode, turn outcome, and
repaired/unrepaired/unknown response. Each group adds a `run` label, also shown in
human output. `input-N:session-M` uses the 1-based input ordinal and a per-file
counter incremented on every valid `run_start` object. Identical metadata never
merges separate sessions, including across files with the same experiment ID.

Session 0 covers legacy records before the first `run_start`, or an entire file
without that marker. It is an unmarked segment, not a verified single run. A
`run_end` does not increment the counter. Concatenated legacy runs without start
markers cannot be separated reliably. These labels depend on input order and are
not persistent run IDs or a mechanism for deduplicating overlapping files.

`run_start` provides context; subsequent `run_start` replaces it. Record-level
metadata overrides inherited metadata, but cannot override the derived session
label. Unknown labels mean unavailable metadata, not inferred settings. Do not
treat input ordinals as scientifically controlled experiments.

Statistics are run-level distributions, further split by the other labels, not
pooled experiment-level statistics. The experiment label retains experimental
membership for later reviewed analysis. The analyzer does not average per-run
p95 values or automatically pool sessions. Any experiment-level comparison must
choose its weighting and account for within-run dependence explicitly.

Only `turn`, `turn_error`, and `run_end` with `discarded_decision` are decision
records. Other events are ignored and counted. Terminal summaries are not extra
samples. Completed means the Python turn was recorded, not a game victory or an
all-actions-success guarantee. Action rejection and explicit per-action failure
are separate from completed turns; a turn error may be compaction or provider
failure, not necessarily a sent request. Error messages and state/prompt payloads
are not copied to analysis output.

Latencies must be finite, nonnegative numeric values; booleans, strings and invalid
numbers are rejected. Missing/null values stay missing. JSONL parse errors and
non-object rows are counted without echoing input; blank lines are skipped.
Unreadable files/invalid file encoding cause a clear CLI error. Mean, median/p50,
nearest-rank p95 (`ceil(0.95*n)`), min/max and valid count are reported per group.
Empty distributions use null, not zero. Small-sample p95 is descriptive, not a
stable tail estimate. Failed attempts without a metric still count as missing;
success-only latency is subject to survivor bias.

## Available evidence and limits

No team-schema real JSONL logs were found in the inspected `runs/` directories of
the original lab or macOS worktree. Tests and CLI examples generated during this
work use explicitly synthetic fixtures. No cloud call, game, or new benchmark was
run. Legacy AgentBridge demo logs use another schema and are not substituted.
The meeting statement of approximately 20 ms is unverified and has no established
model, hardware, workload, endpoint, or measurement boundary here.

## Next bounded pilot (proposal; not executed)

First collect a small approved instrumented baseline with fixed model/revision,
provider, reasoning effort, token cap, prompts, game version, map/seed, starting
state, teams and hardware. Record warmup separately, failures and repairs, stage
coverage and game action validity. Swap sides and interleave repeats. Report
per-episode distributions; do not assume turns in one match are independent.

If generation dominates, propose one controlled intervention, such as a smaller
output-token budget, only after approval: this can truncate decisions and change
quality. If prompt compaction dominates, profile it on recorded snapshots first
and require identical compact outputs for any mechanical optimization. Pilot
planning/analysis is roughly 0.5-1 engineer-day, excluding obtaining live logs;
no statistical power claim follows from a small pilot. Do not reduce the 0.5-second
wait or add parallel calls merely to improve apparent responsiveness.

Acceptance: compare identical metric boundaries and failure/repair rates alongside
action validity and game outcomes. Claim improvement only with actual comparable
measurements and uncertainty. See [AI options](ai-technology-options.md).
