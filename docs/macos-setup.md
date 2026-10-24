# macOS developer setup

This guide supplements the [main README](../README.md). It covers the team RTS
showcase; the separate AgentBridge research runtime has a different API and must
not run on the same ports at the same time.

## Prerequisites and runtime selection

Use Bash 3.2+, Python 3.10+, JDK 17 (including `javac`), and curl or wget.
Ollama cloud access is needed only for the model-driven showcase, not helper tests.
Install dependencies separately; the commands below do not install Python or Java.

```bash
/bin/bash --version
python3 --version
/usr/libexec/java_home -V
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
# Set this to an existing Python 3.10+ interpreter, not the macOS Python 3.9.
export MINDUSTRY_AGENT_PYTHON="/absolute/path/to/python3.13"
"$MINDUSTRY_AGENT_PYTHON" --version
"$JAVA_HOME/bin/java" -version
"$JAVA_HOME/bin/javac" -version
```

Python selection: an explicit `MINDUSTRY_AGENT_PYTHON`, otherwise `python3`, then
`python` on PATH. Each candidate is executed to validate its version. An invalid
explicit override fails rather than silently selecting something else.

Java selection: explicit `JAVA_HOME`, otherwise macOS `java_home -v 17`, then Java
on PATH. Both Java and javac must be version 17. Build and game launch scripts
export the selected `JAVA_HOME` and prepend its bin directory to PATH for children.
No shell profile or system-wide setting is changed by this guide.

## SourceTree and Git setup

Install SourceTree from its official distributor. Launch it normally; do not
bypass Gatekeeper or signature warnings. Add the local repository using the
Local repository browser (or File > Open). UI wording may vary by version.
A hosted-account login is separate from a repository's Git remote configuration.

For a new checkout, fork the team lab to your personal GitHub account, then clone
that fork using SourceTree or Git. Replace `YOUR_ACCOUNT` below. Existing clones
should be inspected before adding or changing any remote.

```bash
git clone --recurse-submodules https://github.com/YOUR_ACCOUNT/mindustry-lab.git
cd mindustry-lab
git remote add upstream https://github.com/time-to-think/mindustry-lab.git
git remote set-url --push upstream DISABLED
git config remote.pushDefault origin
git config push.default simple
git remote -v
git branch -vv
git status --short --branch
```

For an existing checkout, these last three commands are inspection only. `origin`
should be your personal lab fork and `upstream` the team lab. Do not add a second
remote if it already exists. Do not put credentials in remote URLs.

`canonical` is appropriate in the separate game-source repository, where it
identifies `https://github.com/Anuken/Mindustry.git`. The lab has no equivalent
Anuken lab upstream; do not point a lab remote at the unrelated game repository.
Keep the team's `mindustry/` submodule and its reviewed gitlink unchanged. Game
changes use a separate game-fork PR; see [repository layout](repository-layout.md).

Before editing, fetch team metadata and create a feature branch from the reviewed
team baseline. Push only to the personal fork when authorized and request review
into team `develop`. Never force-push or develop directly on team `develop`.

In SourceTree, confirm the correct repository path and feature branch, inspect
History and the remote URLs in Repository Settings, then try a read-only fetch
from the personal fork. Check its result. Git CLI output or a bookmark alone does
not prove the GUI can authenticate, fetch, or display the intended repository.

## Server, client, and showcase

The following procedures write local build/runtime data and may download release
JARs. Run them only when those operations are intended. They are documented
procedures, not a record of successful live verification on this Mac.

From the lab checkout, prepare and start the team server:

```bash
./scripts/setup-server.sh
./scripts/run-rts-server.sh
```

At the server prompt enter `showcase-rts-start`. In a second terminal:

```bash
./scripts/run-client.sh
```

Join `127.0.0.1:6567`. The client launcher adds `-XstartOnFirstThread` on macOS and
installs the spectator mod under `~/Library/Application Support/Mindustry/mods`
(or the directory selected by `MINDUSTRY_DATA_DIR`). Review existing mod files
before installation: the installer replaces the matching spectator JAR.

Only when cloud inference is authorized, enter `/agent-start 500` and `/spectate`
in game chat. Use `/agent-status` and `/agent-stop` for those agents. The optional
terminal route is `run-pvp-agents.sh` / `stop-pvp-agents.sh`; do not start both
routes simultaneously. See the README for models, tokens, and configuration.

## Lightweight verification

These checks do not start the game, Gradle, or a model:

```bash
"$MINDUSTRY_AGENT_PYTHON" -B -m unittest discover -s tests -p 'test_runtime_selection.py' -v
"$MINDUSTRY_AGENT_PYTHON" -B -m unittest discover -s tests -p 'test_cross_platform_launchers.py' -v
for script in scripts/*.sh scripts/lib/*.sh; do /bin/bash -n "$script" || exit 1; done
git diff --check
/bin/bash -c 'source scripts/lib/common.sh; find_python; use_java17; printf "%s\n" "$JAVA_HOME"'
```

## Troubleshooting

- Python 3.9 selected by the OS: set `MINDUSTRY_AGENT_PYTHON` to an installed
  supported interpreter. The launcher does not install or upgrade Python.
- `JAVA_HOME` points to JDK 25: set it to JDK 17. An explicit incompatible home
  fails even when another supported JDK exists.
- `javac` missing: use a full JDK, not only a JRE.
- Ports 6567 or 8765 occupied: identify the owner; do not kill unrelated processes.
- Existing server JAR but stale plugin: run the explicit setup/build procedure
  when safe; merely launching an existing server does not rebuild its plugin.
- SourceTree signature warning: use the official vendor's recovery/reinstallation
  procedure with owner approval; do not disable security checks or remove data.
- GUI starts but cannot join: check server logs, version v159.7, and completion of
  `showcase-rts-start`. A connected client alone does not prove gameplay success.

## Verification boundaries

The runtime-selection work was checked on macOS with Bash 3.2, Python 3.13.5,
and Temurin 17.0.20. Focused tests cover simulated Linux PATH selection, invalid
versions, explicit overrides, paths containing spaces, and JDK propagation to a
mock Gradle child. Real Linux gameplay, Windows execution, real Gradle builds,
SourceTree GUI authentication, and live model/gameplay are not established by
those checks. Keep individual execution evidence separate from instructions.
