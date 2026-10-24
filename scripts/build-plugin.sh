#!/usr/bin/env bash

set -Eeuo pipefail
source "$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lib/common.sh"

use_java17
export GRADLE_USER_HOME="${GRADLE_USER_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/mindustry-lab/gradle}"

cd "$REPO_ROOT"
./gradlew jar --no-daemon

server_root="$LOCAL_ROOT/server"
if [[ -d "$server_root" ]]; then
    mkdir -p "$server_root/config/mods"
    cp "$REPO_ROOT/build/libs/mindustry-llm-bridge.jar" "$server_root/config/mods/mindustry-llm-bridge.jar"
    printf 'Deployed plugin to %s\n' "$server_root/config/mods"
fi
