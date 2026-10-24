#!/usr/bin/env bash

set -Eeuo pipefail
source "$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lib/common.sh"

use_java17
export GRADLE_USER_HOME="${GRADLE_USER_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/mindustry-lab/gradle}"
cd "$REPO_ROOT"
./gradlew spectatorJar --no-daemon

client_mods="$(mindustry_data_dir)/mods"
mkdir -p "$client_mods"
cp "$REPO_ROOT/build/libs/mindustry-rts-spectator.jar" "$client_mods/mindustry-rts-spectator.jar"
printf 'RTS spectator cleanup mod installed at %s\n' "$client_mods"
