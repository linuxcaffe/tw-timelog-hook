#!/usr/bin/env python3
"""
on-modify_timelog.py — Write hledger timeclock entries on task start/stop

When a task is started or stopped, writes a timeclock i/o pair to the
configured file, queryable with hledger or ledger for time reports.

Config: ~/.task/config/timelog.rc
  timelog.file = ~/.task/time/tw.timeclock

Backdate: add a plain-number annotation when starting/stopping to backdate:
  task <id> start; task <id> annotate 15   → start recorded 15 minutes ago
  task <id> stop;  task <id> annotate 10   → stop  recorded 10 minutes ago

Install: ~/.task/hooks/on-modify_timelog.py
Version: 1.0.0
"""

import sys
import json
import re
import calendar
from datetime import datetime, timedelta
from pathlib import Path

CONFIG_FILE = Path.home() / '.task' / 'config' / 'timelog.rc'
DEFAULT_FILE = Path.home() / '.task' / 'time' / 'tw.timeclock'
VERSION = '1.0.0'


def get_config(key: str, default: str = '') -> str:
    """Read timelog.<key> from timelog.rc."""
    if not CONFIG_FILE.exists():
        return default
    with CONFIG_FILE.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            if k.strip() == f'timelog.{key}':
                return v.strip()
    return default


def tw_to_dt(s: str) -> datetime:
    return datetime.strptime(s, '%Y%m%dT%H%M%SZ')


def dt_to_tw(d: datetime) -> str:
    return d.strftime('%Y%m%dT%H%M%SZ')


def to_local(d: datetime) -> datetime:
    """Convert UTC datetime to local time."""
    return datetime.fromtimestamp(calendar.timegm(d.timetuple()))


def tc_ts(d: datetime) -> str:
    """Format as hledger timeclock timestamp."""
    return d.strftime('%Y/%m/%d %H:%M:%S')


def anno_count_grew(old: dict, new: dict) -> bool:
    return len(new.get('annotations', [])) > len(old.get('annotations', []))


def pop_backdate(task: dict) -> tuple:
    """If the newest annotation is a plain integer, remove it and return (task, minutes).
    Otherwise return (task, 0)."""
    annos = task.get('annotations', [])
    if not annos:
        return task, 0
    by_entry = sorted(annos, key=lambda a: a['entry'])
    last = by_entry[-1]['description']
    if not re.match(r'^\d+$', last):
        return task, 0
    task = dict(task)
    task['annotations'] = by_entry[:-1]
    if not task['annotations']:
        del task['annotations']
    return task, int(last)


def main() -> None:
    old = json.loads(sys.stdin.readline())
    new = json.loads(sys.stdin.readline())

    tc_str = get_config('file', str(DEFAULT_FILE))
    tc_path = Path(tc_str.replace('~', str(Path.home())))

    added = anno_count_grew(old, new)

    # --- Task started ---
    if 'start' in new and 'start' not in old:
        if added:
            new, minutes = pop_backdate(new)
            if minutes:
                start_dt = tw_to_dt(new['start']) - timedelta(minutes=minutes)
                new['start'] = dt_to_tw(start_dt)
                print(f'Timelog: started {minutes}m ago.')
                # Don't let backdated start precede task entry date
                if tw_to_dt(new['start']) < tw_to_dt(new['entry']):
                    new['entry'] = new['start']

    # --- Task stopped ---
    elif 'start' in old and 'start' not in new:
        started = to_local(tw_to_dt(old['start']))
        stopped = datetime.now()

        if added:
            new, minutes = pop_backdate(new)
            if minutes:
                stopped -= timedelta(minutes=minutes)
                if stopped < started:
                    print(f'ERROR: -{minutes}m would precede start time', file=sys.stderr)
                    sys.exit(1)
                print(f'Timelog: stopped {minutes}m ago.')

        project = new.get('project', 'no:project').replace('.', ':')
        desc    = new.get('description', '')
        tags    = new.get('tags', [])
        uuid    = new['uuid']

        tag_str = ', '.join(tags)
        comment = f'; {tag_str}  uuid:{uuid}' if tag_str else f'; uuid:{uuid}'

        entry = (
            f'i {tc_ts(started)} {project}  {desc}  {comment}\n'
            f'o {tc_ts(stopped)}\n\n'
        )

        tc_path.parent.mkdir(parents=True, exist_ok=True)
        with tc_path.open('a', encoding='utf-8') as f:
            f.write(entry)

    print(json.dumps(new))


if __name__ == '__main__':
    main()
