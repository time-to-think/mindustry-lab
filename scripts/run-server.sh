#!/usr/bin/env bash

set -Eeuo pipefail
source "$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lib/common.sh"

use_java17
java_bin="$JAVA_HOME/bin/java"
python_bin="$(find_python)"

server_root="$LOCAL_ROOT/server"
server_jar="$server_root/server-release.jar"
if [[ ! -f "$server_jar" ]]; then
    "$SCRIPT_DIR/setup-server.sh"
fi

export MINDUSTRY_AGENT_PROJECT_DIR="$REPO_ROOT"
export MINDUSTRY_AGENT_PYTHON="$python_bin"
export LLM_MODEL="${LLM_MODEL:-deepseek-v4.1-flash:cloud}"
export LLM_REASONING_EFFORT="${LLM_REASONING_EFFORT:-none}"

bridge_port="${MINDUSTRY_AGENT_PORT:-8765}"
for port in "$bridge_port" 6567; do
    if port_is_open "$python_bin" "$port"; then
        die "TCP port $port is already in use. Stop the existing Mindustry server and retry."
    fi
done

cd "$server_root"
exec "$java_bin" -jar "$server_jar"
