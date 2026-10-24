# Mindustry Lab

Mindustry Lab is a model-vs-model RTS showcase built on Mindustry v159.7. Two cloud LLM agents receive the same authoritative battlefield state and the same action API, then independently decide how to build, produce, upgrade, defend, capture objectives, maneuver squads, and attack the opposing core.

The current showcase compares `glm-5.3-flash:cloud` as the Sharded team with `deepseek-v4.1-flash:cloud` as the Crux team. Model response time is part of the match: each valid response is applied as soon as it arrives.

## What the showcase demonstrates

- LLM-authored strategy without a fixed build order or scripted unit composition.
- Equal starting stockpiles and identical action capabilities for both teams.
- Sequential construction, parallel factory production, unit upgrades, persistent squads, rally points, attack, retreat, and defense commands.
- Three symmetric but tactically different lanes: a wide northern maneuver lane, a short fortified center lane, and a long southern flank.
- Three control points that provide strategic benefits but never end the match:
  - North: 15% more damage for all combat units on the owning team.
  - Center: 15% more movement speed for all combat units on the owning team.
  - South: incoming combat-unit damage is divided by 1.15 for the owning team.
- Core destruction as the only victory condition.
- A neutral spectator mode, live Korean HUD telemetry, unit-loss cleanup, JSONL match logs, response latency, and action-result tracking.

The Java bridge exposes server-authoritative state and validates actions. Python handles model calls, state compaction, recent-event feedback, and action normalization. Mindustry's own movement and combat systems execute the accepted commands.

## Repository layout

```text
plugin/             Headless server bridge and RTS rules
client-plugin/      Spectator cleanup and viewing support
mindustry_agent/    Cloud LLM decision loop
scripts/            Windows PowerShell and macOS/Linux shell launchers
tests/              Python contract and behavior tests
mindustry/          Reviewed Mindustry source submodule
```

Generated builds, downloaded game files, credentials, logs, and local agent state are excluded from Git.

## Requirements

### macOS or Linux

- Bash
- JDK 17
- Python 3.10 or newer
- `curl` or `wget`
- Ollama configured for the cloud models used by the match

On macOS, a Temurin 17 installation works well. Verify the tools before starting:

```bash
java -version
python3 --version
ollama list
```

### Windows

- PowerShell 7 or Windows PowerShell
- JDK 17
- Python 3.10 or newer
- Ollama configured for the cloud models

## Clone

```bash
git clone --recurse-submodules https://github.com/time-to-think/mindustry-lab.git
cd mindustry-lab
```

If the repository was cloned without submodules, initialize them later with:

```bash
git submodule update --init --recursive
```

The submodule is useful for source-level development. Running the showcase uses the pinned release JARs downloaded by the setup scripts.

## Run the RTS showcase on macOS or Linux

### 1. Prepare the server

```bash
./scripts/setup-server.sh
```

This builds the bridge plugin, downloads the Mindustry v159.7 headless server when needed, and installs the plugin under `.local/server`.

### 2. Start the RTS server

```bash
./scripts/run-rts-server.sh
```

When the Mindustry server prompt appears, enter:

```text
showcase-rts-start
```

### 3. Open a spectator client

In a second terminal:

```bash
./scripts/run-client.sh
```

In Mindustry, join `127.0.0.1:6567`. The shell launcher installs the client-side spectator cleanup mod in the platform data directory before opening the game. On macOS it also supplies the JVM's required `-XstartOnFirstThread` option automatically.

### 4. Start both agents

Open in-game chat and enter:

```text
/agent-start 500
```

The server launches both configured agents. To enter neutral free-camera mode, enter:

```text
/spectate
```

Useful chat commands:

```text
/agent-status
/agent-stop
/spectate-off sharded
/spectate-off crux
```

As a terminal-only alternative to `/agent-start`, run:

```bash
./scripts/run-pvp-agents.sh
```

Stop agents started by that shell script with:

```bash
./scripts/stop-pvp-agents.sh
```

## Run on Windows

The existing PowerShell launchers remain supported:

```powershell
.\scripts\setup-server.ps1
.\scripts\run-rts-server.ps1
```

Enter `showcase-rts-start` at the server prompt. In another PowerShell window, open the client:

```powershell
.\scripts\run-client.ps1
```

Join `127.0.0.1:6567`, then use `/agent-start 500` and `/spectate` in game chat.

## Configuration

The shell scripts accept environment-variable overrides without storing secrets in the repository:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PRIMARY_MODEL` | `glm-5.3-flash:cloud` | Sharded model |
| `DEEPSEEK_MODEL` | `deepseek-v4.1-flash:cloud` | Crux model |
| `PRIMARY_REASONING_EFFORT` | `low` | Sharded reasoning setting |
| `DEEPSEEK_REASONING_EFFORT` | `none` | Crux reasoning setting |
| `PRIMARY_TOKEN` | local development token | Sharded bridge token |
| `DEEPSEEK_TOKEN` | local development token | Crux bridge token |
| `MINDUSTRY_API_URL` | `http://127.0.0.1:8765` | Bridge API URL |
| `MINDUSTRY_AGENT_PORT` | `8765` | Bridge listener port |
| `MINDUSTRY_DATA_DIR` | platform default | Mindustry client data directory |
| `MINDUSTRY_LOCAL_ROOT` | `.local` | Downloaded runtime directory |
| `MAX_TURNS` | `500` | Turns for terminal-started agents |

Example:

```bash
PRIMARY_MODEL=glm-5.3-flash:cloud \
DEEPSEEK_MODEL=deepseek-v4.1-flash:cloud \
./scripts/run-rts-server.sh
```

Do not commit API keys, model credentials, `.env` files, `.local`, `runs`, or build output.

## Logs and evaluation

Agent decisions and results are written to `runs/*.jsonl`. Console output from terminal-started agents is written to `runs/*-pvp-*.log`.

Each match records model latency, observed and applied game ticks, normalized actions, server validation results, unit losses, squad status, objective state, and core-damage progress. This supports comparison of both strategy quality and real-time responsiveness.

## Development checks

Run the Python suite:

```bash
python3 -m unittest discover -s tests -v
```

Build the server plugin:

```bash
./scripts/build-plugin.sh
```

The shell launchers are written for Bash 3.2 or newer so that the default Bash available on older macOS installations remains usable.

## Troubleshooting

- `Address already in use`: stop the previous Mindustry server before starting another one. Ports `6567` and `8765` must be free.
- `JDK 17 was not found`: install JDK 17 and set `JAVA_HOME`.
- The client cannot join: confirm that `showcase-rts-start` completed and connect to `127.0.0.1:6567`.
- Agents do not start: confirm that Ollama can access both cloud models and check `/agent-status` plus `runs/`.
- Spectator mod path is non-standard: set `MINDUSTRY_DATA_DIR` to the Mindustry data directory before running `run-client.sh`.
