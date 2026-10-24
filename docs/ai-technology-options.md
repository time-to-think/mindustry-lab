# AI technology options for Mindustry

Prepared 2026-10-24 for mentor discussion. All Mindustry-specific performance,
generalization, and effort estimates below are engineering hypotheses unless
explicitly described as inspected implementation facts. No RL training, live LLM
benchmark, or comparison experiment was performed.

## Current compatibility and candidate comparison

The current team runtime already connects a cloud LLM to authoritative state,
validated actions, and normal engine movement/combat. Deterministic execution and
persistent orders let the game progress between Python decisions. This is not an
implemented learned tactical policy. The showcase exposes full battlefield state;
a fog-limited experiment would require a separately agreed observation contract.

| Criterion | LLM strategy | RL policy | Hybrid candidate |
| --- | --- | --- | --- |
| Real-time response | Cloud/network/generation delays; inspect measured stages first | A bounded deployed network may respond quickly, but hardware/model benchmarks are required | Infrequent strategy plus local tactical actions could reduce cloud dependency; handoff adds delay |
| Decision quality | Flexible interpretation; schema and causal errors remain possible | Reward-aligned within trained distribution; reward exploitation is a risk | Could combine strengths; conflicting controllers may reduce quality |
| Data and compute | No project training required for baseline; inference budget still matters | Needs resettable episodes, observations/actions/rewards, many samples and training compute | LLM baseline plus RL data/training if tactics are learned |
| New maps | May interpret new symbolic state, not proven to generalize here | Requires map randomization/held-out evaluation | Both strategic and tactical generalization need separate tests |
| New unit compositions | Catalog-based reasoning is available, effectiveness unproven | Policy input/action masks must support composition changes; retraining may be needed | Interface must expose unit capabilities and handle unsupported commands |
| Reproducibility | Pin provider/model revision/settings where available; cloud nondeterminism remains | Pin seeds/checkpoints/environment/hardware; training is still stochastic | Must pin both policies and handoff/scheduling settings |
| Fair evaluation | Same observations/action support/budget, with latency included | Same task limits; disclose training budget and evaluation hardware | Same executor and helper behavior; measure which controller chose each action |
| Development effort | Lowest integration effort given existing code | Highest: simulator adapter, reset, reward design, training and evaluation | Moderate if deterministic tactics; high if learned tactics |
| Fit with team code | Already implemented baseline | No training/reset harness established by this task | Existing bridge reusable; learned tactical controller and arbitration are not implemented |

No approach is declared the winner. The current LLM path is the cheapest baseline
to evaluate, while RL and hybrid options remain research candidates.

## Published evidence and its limits

- [SC2LE, Vinyals et al. (2017)](https://arxiv.org/abs/1708.04782) defines an RTS
  observation/action/reward interface and smaller tasks. It motivates a bounded
  training problem before full-game RL; it is not a Mindustry implementation.
- [PPO, Schulman et al. (2017)](https://arxiv.org/abs/1707.06347) describes a policy
  gradient training method based on environment interaction. PPO is a candidate
  for a discrete tactical pilot, not evidence of a 20 ms Mindustry policy.
- [AlphaStar, Vinyals et al. (2019)](https://www.nature.com/articles/s41586-019-1724-z)
  demonstrates strong StarCraft II play through a substantial learning system.
  This task verified publication/search metadata; full Nature access was blocked.
  Do not transfer its results, compute budget, or control semantics to this project.
- [Voyager, Wang et al. (2023)](https://arxiv.org/abs/2305.16291) uses an LLM,
  executable skill library and environment feedback in Minecraft. It motivates
  temporally extended actions as a candidate, but does not validate an LLM-plus-RL
  tactical stack or real-time Mindustry latency.

## Proposed experiments and decision gates

1. **No retraining:** analyze existing/new approved baseline logs with the latency
   tool. Existing context compaction and single JSON repair already exist; do not
   reimplement them as new improvements. Offline analysis is roughly half a day
   once suitable logs exist. No speedup has been measured.
2. **More observability:** if aggregated `llm_decide` dominates, separately measure
   HTTP attempts, prompt bytes and parsing with a reviewed schema. Provider TTFT
   requires streaming/provider metrics and cannot be inferred from total duration.
   Estimated small instrumentation task: 1-2 days plus review.
3. **Architectural change:** a strategic LLM plus deterministic or learned tactical
   executor requires an explicit ownership/handoff contract, stale-state policy,
   equal helper budgets and attribution logs. Several integration days plus
   gameplay validation; do not implement without architecture approval.
4. **RL experiment:** propose one small control task (for example, attack/retreat
   for a fixed squad) with a fixed observation/action interface and legal action
   mask. Start with a deterministic baseline; evaluate PPO only after reset and
   reward semantics are verified. Multi-week exploration is an estimate, not a
   commitment. Full-game economic strategy and multi-agent RL are outside this pilot.

Hold out maps and unit compositions; report action invalidity, task success,
resource/unit losses, latency distributions, timeout/failure rate, training samples,
and compute. Separate equal simulated-time evaluation from real-time wall-clock
competition. Do not give one condition extra hidden state, repeated decisions,
scripted strategic help, or unreported training. Freeze task termination and reset
rules before comparing. Side swaps and multiple seeds reduce fixture bias;
confidence claims require more than a few demonstration matches.

The approximately 20 ms meeting remark is unverified: it may refer to another
boundary or workload. It is neither a project baseline nor an acceptance target
until the mentor clarifies it. See [latency evaluation](llm-latency-evaluation.md)
for the immediate measurement-first pilot and remaining implementation gaps.
