#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)"
LOCAL_ROOT="${MINDUSTRY_LOCAL_ROOT:-$REPO_ROOT/.local}"

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}
require_command() {
    command -v "$1" >/dev/null 2>&1 || die "$1 was not found on PATH."
}

find_python() {
    local candidate resolved
    if [[ -n "${MINDUSTRY_AGENT_PYTHON:-}" ]]; then
        resolved="$(command -v "$MINDUSTRY_AGENT_PYTHON" 2>/dev/null || true)"
        if [[ -n "$resolved" ]] && "$resolved" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
            [[ "$resolved" == /* ]] || resolved="$PWD/$resolved"
            printf '%s\n' "$resolved"
            return
        fi
        die "MINDUSTRY_AGENT_PYTHON must name a working Python 3.10+ interpreter."
    fi
    for candidate in python3 python; do
        resolved="$(command -v "$candidate" 2>/dev/null || true)"
        if [[ -n "$resolved" ]] && "$resolved" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
            [[ "$resolved" == /* ]] || resolved="$PWD/$resolved"
            printf '%s\n' "$resolved"
            return
        fi
    done
    die "Python 3.10+ is required. Set MINDUSTRY_AGENT_PYTHON to a supported interpreter or update PATH."
}

java_home_for() {
    local settings line version="" java_home=""
    settings="$("$1" -XshowSettings:properties -version 2>&1)" || return 1
    while IFS= read -r line; do
        if [[ "$line" =~ ^[[:space:]]*java\.specification\.version[[:space:]]*=[[:space:]]*(.*)$ ]]; then
            version="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^[[:space:]]*java\.home[[:space:]]*=[[:space:]]*(.*)$ ]]; then
            java_home="${BASH_REMATCH[1]}"
        fi
    done <<< "$settings"
    [[ "$version" == "17" && -x "$java_home/bin/java" && -x "$java_home/bin/javac" ]] || return 1
    settings="$("$java_home/bin/javac" -version 2>&1)" || return 1
    while IFS= read -r line; do
        if [[ "$line" =~ ^javac[[:space:]]17(\.|-|$) ]]; then
            printf '%s\n' "$java_home"
            return
        fi
    done <<< "$settings"
    return 1
}

find_java() {
    local java_home candidate
    if [[ -n "${JAVA_HOME:-}" ]]; then
        java_home="$(java_home_for "$JAVA_HOME/bin/java")" || die "JAVA_HOME must point to a working JDK 17 (including javac)."
        printf '%s/bin/java\n' "$java_home"
        return
    fi
    if [[ "$(uname -s)" == "Darwin" && -x /usr/libexec/java_home ]]; then
        candidate="$(/usr/libexec/java_home -v 17 2>/dev/null || true)"
        if [[ -n "$candidate" ]] && java_home="$(java_home_for "$candidate/bin/java")"; then
            printf '%s/bin/java\n' "$java_home"
            return
        fi
    fi
    candidate="$(command -v java 2>/dev/null || true)"
    if [[ -n "$candidate" ]] && java_home="$(java_home_for "$candidate")"; then
        printf '%s/bin/java\n' "$java_home"
        return
    fi
    die "JDK 17 is required. Set JAVA_HOME to a JDK 17 installation (including javac)."
}

use_java17() {
    local java_bin
    java_bin="$(find_java)" || return 1
    export JAVA_HOME="${java_bin%/bin/java}"
    export PATH="$JAVA_HOME/bin:$PATH"
}

download_file() {
    local url="$1"
    local destination="$2"
    local temporary="${destination}.part.$$"
    rm -f "$temporary"
    if command -v curl >/dev/null 2>&1; then
        curl --fail --location --retry 3 --output "$temporary" "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget --output-document="$temporary" "$url"
    else
        die "curl or wget is required to download Mindustry."
    fi
    mv "$temporary" "$destination"
}

port_is_open() {
    local python_bin="$1"
    local port="$2"
    "$python_bin" - "$port" <<'PY'
import socket
import sys

sock = socket.socket()
sock.settimeout(0.25)
try:
    result = sock.connect_ex(("127.0.0.1", int(sys.argv[1])))
finally:
    sock.close()
raise SystemExit(0 if result == 0 else 1)
PY
}

mindustry_data_dir() {
    if [[ -n "${MINDUSTRY_DATA_DIR:-}" ]]; then
        printf '%s\n' "$MINDUSTRY_DATA_DIR"
        return
    fi
    case "$(uname -s)" in
        Darwin) printf '%s\n' "$HOME/Library/Application Support/Mindustry" ;;
        Linux) printf '%s\n' "${XDG_DATA_HOME:-$HOME/.local/share}/Mindustry" ;;
        *) die "Unsupported platform. Set MINDUSTRY_DATA_DIR explicitly." ;;
    esac
}
