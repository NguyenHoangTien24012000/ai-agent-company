#!/usr/bin/env bash
# Chờ dòng sự kiện mới khớp bộ lọc; hết giờ trả exit 2.
set -euo pipefail
COMPANY_ROOT="${SPORTSHUB_CO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
exec python3 - "$COMPANY_ROOT" "$@" <<'PY'
import argparse
import json
import math
from pathlib import Path
import re
import sys
import time

root = Path(sys.argv[1])
parser = argparse.ArgumentParser(description='Chờ sự kiện mới của công ty.')
parser.add_argument('--room')
parser.add_argument('--types')
parser.add_argument('--timeout', type=float, default=14400)
parser.add_argument('--interval', type=float, default=5)
args = parser.parse_args(sys.argv[2:])
if not math.isfinite(args.timeout) or args.timeout < 0:
    parser.error('--timeout phải là số hữu hạn không âm.')
if not math.isfinite(args.interval) or args.interval <= 0:
    parser.error('--interval phải là số hữu hạn dương.')
if args.room and not re.fullmatch(r'[A-Z0-9-]{2,24}', args.room):
    parser.error('KEY không hợp lệ.')
types = {value.strip() for value in args.types.split(',')} if args.types else None
if types is not None and '' in types:
    parser.error('--types không được có mục rỗng.')
path = root / 'state' / 'events.jsonl'

def position():
    try:
        stat = path.stat()
        return (stat.st_dev, stat.st_ino), stat.st_size
    except FileNotFoundError:
        return None, 0

try:
    identity, offset = position()
    pending = b''
    deadline = time.monotonic() + args.timeout
    while True:
        current_identity, size = position()
        if current_identity != identity or size < offset:
            identity, offset, pending = current_identity, 0, b''
        matched = []
        if size > offset:
            try:
                with path.open('rb') as stream:
                    stream.seek(offset)
                    chunk = stream.read(size - offset)
                    offset = stream.tell()
            except FileNotFoundError:
                continue
            lines = (pending + chunk).split(b'\n')
            pending = lines.pop()
            for raw in lines:
                try:
                    event = json.loads(raw)
                except (ValueError, UnicodeError):
                    continue
                if not isinstance(event, dict):
                    continue
                if args.room and event.get('room') != args.room:
                    continue
                if types is not None and event.get('type') not in types:
                    continue
                matched.append(raw.decode('utf-8'))
        if matched:
            print('\n'.join(matched))
            sys.exit(0)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            print('Hết thời gian chờ sự kiện khớp bộ lọc.', file=sys.stderr)
            sys.exit(2)
        time.sleep(min(args.interval, remaining))
except OSError as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(2)
PY
