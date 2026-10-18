#!/usr/bin/env python3
"""Nhịp kiểm của công ty agent — script thường, KHÔNG dùng AI.

Mỗi lượt đọc state và ghi sự kiện (qua Company.record, không ghi tay file) khi:
- `lane_stale`: lane `running` mà `updatedAt` cũ hơn ngưỡng VÀ phòng đó không có sự kiện nào trong cùng khoảng
  (lane treo im lặng — trước đây không ai biết, chỉ có Orca báo terminal đứng yên);
- `thu_ky_silent`: không còn tiến trình `wait-event.sh` không lọc `--room` (watcher của Thư ký) quá ngưỡng ⇒ Thư ký ngủ quên;
- `lane_error`: màn hình lane `running` hay terminal Manager dừng ở một dòng lỗi API/mạng (Codex "at capacity", Claude
  "API Error"…) mà không còn chạy ⇒ báo ngay lượt này, không chờ ngưỡng `lane_stale` (từng có lane chết lặng 145 phút).

Không báo lặp: cùng một lane (hay Thư ký) chỉ báo lại khi đã qua thêm một ngưỡng nữa kể từ lần báo trước;
dấu lưu ở `state/heartbeat.json`. `--now` giả giờ cho test, nên test không phải sleep. Biến `ORCA` thay Orca CLI
(test dùng orca giả, không bao giờ đọc terminal thật).
"""

import argparse
from datetime import datetime, timedelta
import hashlib
import json
import subprocess
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from company import TZ, Company, atomic_write, read_json  # noqa: E402

# Sự kiện do chính nhịp kiểm ghi không được tính là "phòng còn hoạt động", nếu không lần báo sau sẽ tự che lần báo trước.
OWN_TYPES = ('lane_stale', 'thu_ky_silent', 'lane_error')
THU_KY = 'thu-ky'
ORCA = os.environ.get('ORCA', '/Applications/Orca.app/Contents/Resources/bin/orca')

# Dòng lỗi khiến lane đứng im ở dấu nhắc (so không phân biệt hoa thường). Chỉ xét ERROR_TAIL dòng cuối khác rỗng:
# lỗi cũ đã trôi lên trên mà lane chạy tiếp thì không tính.
ERROR_PATTERNS = ('model is at capacity', 'api error', 'connection lost', 'response stopped arriving',
                  'stream disconnected', 'network error', 'econnreset', 'fetch failed', 'rate limit')
# Còn thấy dấu đang chạy (Claude: "esc to interrupt", Codex: "Working (") ⇒ lane đang tự thử lại, chưa chết.
BUSY_PATTERNS = ('esc to interrupt', 'working (')
ERROR_TAIL = 12
SCREEN_ROWS = 30
LINE_MAX = 200


def parse_time(value):
    stamp = datetime.fromisoformat(value)
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=TZ)


def recent_rooms(events_path, since):
    """Tập phòng có sự kiện (không phải của nhịp kiểm) từ mốc `since` trở đi."""
    rooms = set()
    if not events_path.exists():
        return rooms
    with events_path.open(encoding='utf-8') as stream:
        for line in stream:
            try:
                event = json.loads(line)
                if event.get('type') in OWN_TYPES or not event.get('room'):
                    continue
                if parse_time(event['ts']) >= since:
                    rooms.add(event['room'])
            except (ValueError, KeyError, TypeError):
                continue   # dòng hỏng hay đang ghi dở: bỏ qua, lượt sau đọc lại
    return rooms


def due(marks, key, current, threshold):
    """Chưa báo lần nào, hoặc lần báo trước đã cách ít nhất một ngưỡng."""
    last = marks.get(key)
    return last is None or current - parse_time(last) >= threshold


def thu_ky_watching():
    """Có watcher của Thư ký đang chạy không. HEARTBEAT_PS_FILE (test) thay cho `ps`."""
    fake = os.environ.get('HEARTBEAT_PS_FILE')
    if fake:
        lines = Path(fake).read_text(encoding='utf-8').splitlines()
    else:
        lines = subprocess.run(['ps', '-eo', 'command'], capture_output=True, text=True).stdout.splitlines()
    return any('wait-event.sh' in line and '--room' not in line for line in lines)


def read_screen(handle):
    """Màn hình terminal Orca dạng chữ; lỗi gì (Orca tắt, handle chết, quá giờ) cũng trả None — không làm chết nhịp."""
    try:
        result = subprocess.run([ORCA, 'terminal', 'read', '--terminal', handle, '--screen', '--limit', str(SCREEN_ROWS)],
                                capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def screen_error(screen):
    """(dòng lỗi, dấu màn hình) nếu lane dừng ở lỗi; None nếu không lỗi hoặc còn đang chạy."""
    lowered = screen.lower()
    if any(busy in lowered for busy in BUSY_PATTERNS):
        return None
    tail = [line.strip() for line in screen.splitlines() if line.strip()][-ERROR_TAIL:]
    # Lấy dòng khớp gần đáy nhất: đó là lỗi mới nhất, lỗi trên nó có thể đã được thử lại.
    for line in reversed(tail):
        if any(pattern in line.lower() for pattern in ERROR_PATTERNS):
            # Dấu = băm phần đáy màn hình: cùng dòng lỗi mà màn hình đổi (đã thử lại rồi lỗi tiếp) thì báo lại.
            return line[:LINE_MAX], hashlib.sha256('\n'.join(tail).encode('utf-8')).hexdigest()[:16]
    return None


def check_errors(company, active, marks):
    """Ghi `lane_error` cho lane running và terminal Manager của phòng active đang dừng ở dòng lỗi."""
    old, kept, written = marks.get('errors', {}), {}, []
    for room in active:
        targets = {}
        if room.get('managerTerminal'):
            targets[room['managerTerminal']] = 'manager'
        for lane in room.get('lanes', []):
            if lane.get('status') == 'running' and lane.get('handle'):
                targets.setdefault(lane['handle'], lane['role'])
        for handle, role in targets.items():
            mark = room['key'] + '/' + handle
            screen = read_screen(handle)
            if screen is None:
                # Đọc lỗi ⇒ không biết gì mới: giữ dấu cũ, tránh báo lại cùng lỗi khi Orca chập chờn.
                if mark in old:
                    kept[mark] = old[mark]
                continue
            found = screen_error(screen)
            if not found:
                continue      # hết lỗi (hay đang chạy) ⇒ bỏ dấu, lỗi sau báo như mới
            line, digest = found
            kept[mark] = {'line': line, 'screen': digest}
            if old.get(mark) == kept[mark]:
                continue      # màn hình chưa đổi: đã báo rồi
            written.append(company.record('lane_error', {'handle': handle, 'role': role, 'line': line}, room['key']))
    # Lane hết running / phòng đóng thì dấu tự rơi (không nằm trong targets nữa).
    marks['errors'] = kept
    return written


def beat(company, current, stale, silent):
    """Chạy một lượt; trả về danh sách sự kiện đã ghi."""
    marks_path = company.state / 'heartbeat.json'
    marks = read_json(marks_path, {})
    lane_marks = marks.get('lanes', {})
    written = []

    active_lanes = {}
    active = [room for room in company.rooms() if room and room.get('status') == 'active']
    busy = recent_rooms(company.state / 'events.jsonl', current - stale)
    for room in active:
        for lane in room.get('lanes', []):
            if lane.get('status') != 'running':
                continue
            mark = room['key'] + '/' + lane['handle']
            active_lanes[mark] = lane_marks.get(mark)
            idle = current - parse_time(lane['updatedAt'])
            if idle < stale or room['key'] in busy or not due(lane_marks, mark, current, stale):
                continue
            fields = {'handle': lane['handle'], 'role': lane['role'], 'minutes': int(idle.total_seconds() // 60)}
            written.append(company.record('lane_stale', fields, room['key']))
            active_lanes[mark] = current.isoformat()
    # Lane đã xong/đóng thì bỏ dấu, để lần chạy lại sau này được báo như mới.
    marks['lanes'] = {mark: at for mark, at in active_lanes.items() if at}
    written += check_errors(company, active, marks)

    # Thư ký còn canh = có tiến trình wait-event.sh KHÔNG lọc --room (watcher của Manager luôn có --room).
    # Đo tiến trình thay vì file mốc: watcher chờ tới 4 tiếng mà vẫn khoẻ, không phải đánh thức Thư ký định kỳ.
    if thu_ky_watching():
        marks.pop('thuKyMissingSince', None)
    else:
        since = parse_time(marks.setdefault('thuKyMissingSince', current.isoformat()))
        quiet = current - since
        if quiet >= silent and due(marks, THU_KY, current, silent):
            written.append(company.record('thu_ky_silent', {'minutes': int(quiet.total_seconds() // 60)}))
            marks[THU_KY] = current.isoformat()

    atomic_write(marks_path, json.dumps(marks, ensure_ascii=False, indent=2) + '\n')
    return written


def positive(value):
    number = float(value)
    if not number > 0:
        raise argparse.ArgumentTypeError('Phải là số dương.')
    return number


def main(argv=None):
    p = argparse.ArgumentParser(description='Nhịp kiểm lane đứng yên và Thư ký ngủ quên (không dùng AI).')
    p.add_argument('--interval', type=positive, default=900, help='Giây giữa hai lượt (mặc định 900).')
    p.add_argument('--stale-minutes', type=positive, default=45, help='Ngưỡng lane đứng yên (mặc định 45).')
    p.add_argument('--thu-ky-minutes', type=positive, default=30, help='Ngưỡng Thư ký im lặng (mặc định 30).')
    p.add_argument('--once', action='store_true', help='Chạy một lượt rồi thoát.')
    p.add_argument('--now', type=parse_time, help='Giờ giả ISO 8601 (chỉ cho test, đi kèm --once).')
    a = p.parse_args(argv)
    if a.now and not a.once:
        p.error('--now chỉ dùng kèm --once.')
    company = Company()
    stale, silent = timedelta(minutes=a.stale_minutes), timedelta(minutes=a.thu_ky_minutes)
    while True:
        current = a.now or datetime.now(TZ)
        try:
            written = beat(company, current, stale, silent)
            summary = ', '.join(e['type'] + ' ' + str(e.get('room') or 'công ty') +
                                (' ' + e['handle'] if 'handle' in e else '') for e in written)
            print(current.isoformat(timespec='seconds'), summary or 'ổn', flush=True)
        except Exception as exc:   # vòng nền không được chết vì một lượt hỏng; ghi log rồi chờ lượt sau
            print(current.isoformat(timespec='seconds'), 'lỗi:', repr(exc), file=sys.stderr, flush=True)
            if a.once:
                return 2
        if a.once:
            return 0
        time.sleep(a.interval)


if __name__ == '__main__':
    sys.exit(main())
