#!/usr/bin/env bash
# on-exit_stop-started.sh — stop all active tasks when a new task is started
#
# Ensures only one task runs at a time. Each stopped task fires on-modify,
# which triggers on-modify_timelog.py to write its timeclock entry cleanly.
#
# Install: ~/.task/hooks/on-exit_stop-started.sh
# Version: 1.0.0

tw_command=""
for arg in "$@"; do
    if [[ "${arg:0:8}" == "command:" ]]; then
        tw_command="${arg:8}"
        break
    fi
done

[[ "$tw_command" == "start" ]] || exit 0

for uuid in $(task status:pending +ACTIVE _uuids 2>/dev/null); do
    task rc.confirmation=off rc.verbose=nothing "$uuid" stop
done
