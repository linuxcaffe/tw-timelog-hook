#!/usr/bin/env bash
# on-exit_stop-started.sh — when a task is started, stop the other active tasks
#
# Ensures only one task runs at a time, whatever the context. The tasks this
# command started (on stdin, as JSON, one per line) keep running. Each stopped
# task fires on-modify, which triggers on-modify_timelog.py to write its
# timeclock entry cleanly.
#
# Install: ~/.task/hooks/on-exit_stop-started.sh
# Version: 1.1.0

tw_command=""
for arg in "$@"; do
    if [[ "${arg:0:8}" == "command:" ]]; then
        tw_command="${arg:8}"
        break
    fi
done

[[ "$tw_command" == "start" ]] || exit 0

# Without jq it can't tell which task was just started: stop nothing
command -v jq &>/dev/null || exit 0

just_started=$(jq -r 'select(.start) | .uuid' 2>/dev/null)

for uuid in $(task rc.context=none status:pending +ACTIVE _uuids 2>/dev/null); do
    grep -qxF "$uuid" <<<"$just_started" && continue
    task rc.context=none rc.confirmation=off rc.verbose=nothing "$uuid" stop
done
