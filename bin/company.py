#!/usr/bin/env python3
"""Quản lý phòng, câu hỏi và sổ sự kiện SportsHub bằng thư viện chuẩn."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile


TZ = timezone(timedelta(hours=7))
STEPS = ('hoi-dap', 'cho-goi', 'thiet-ke', 'kien-truc', 'ke-hoach-test',
         'code', 'test', 'review', 'cho-check', 'chuan-bi-gop', 'cho-gop', 'xong')
ROLES = ['designer', 'techlead', 'dev-server', 'dev-web', 'qa', 'review']
VIA = ('terminal', 'board', 'thu-ky')
OPEN_ANSWER = 'tra-loi'   # câu hỏi mở kiểu cũ (ask ghi trước khi bắt buộc phương án)
OTHER = 'khac'            # 'Khác — tự viết': Sếp thấy không phương án nào ổn thì mới gõ
NOTE_CHOICES = (OPEN_ANSWER, OTHER)


def effective_options(ask):
    """Phương án thật của một ask. Ask không ghi phương án vẫn phải có nút trên board:
    câu hỏi mở ⇒ gửi câu trả lời (bắt buộc ghi chú), việc Sếp tự làm ⇒ báo đã xong."""
    if ask['options']:
        return ask['options']
    if ask['kind'] == 'duyet':
        return [{'key': 'ok', 'label': 'Duyệt'}, {'key': 'sua', 'label': 'Cần sửa'}]
    if ask['kind'] == 'thaotac':
        return [{'key': 'done', 'label': 'Đã làm xong'}]
    return [{'key': OPEN_ANSWER, 'label': 'Gửi câu trả lời'}]
# deferred = dời sang backlog: lỗi có thật nhưng cố ý không sửa trong phòng này (W7). Chỉ từ open/fixing,
# bắt buộc ghi chú trỏ tới dòng backlog hay commit; không còn tính là "chưa đóng", không lên "Việc của anh".
BUG_TRANSITIONS = {'open': {'fixing', 'deferred'}, 'fixing': {'retest', 'deferred'},
                   'retest': {'fixing', 'closed'}, 'closed': set(), 'deferred': set()}
BUG_SETTLED = ('closed', 'deferred')
# Cổng 3 (giao diện mẫu) chặn mở lane dev-web khi phòng có Designer: code web trước khi Sếp duyệt mẫu là làm hai lần.
UI_GATE = '3'


class UserError(ValueError):
    """Lỗi đầu vào có thể sửa bởi người dùng."""


class KeyBusy(UserError):
    """Chìa khoá app đang thuộc phòng khác."""


def now():
    return datetime.now(TZ).isoformat(timespec='microseconds')


def root_path():
    return Path(os.environ.get('SPORTSHUB_CO', Path(__file__).resolve().parents[1]))


def validate_key(key):
    if not isinstance(key, str) or not re.fullmatch(r'[A-Z0-9-]{2,24}', key):
        raise UserError('KEY phải gồm 2–24 chữ hoa, số hoặc gạch ngang.')
    return key


def nonempty(value):
    if not isinstance(value, str) or not value.strip():
        raise argparse.ArgumentTypeError('Giá trị không được rỗng.')
    return value


def pair(value):
    key, sep, content = value.partition('=')
    if not sep or not key.strip() or not content.strip():
        raise argparse.ArgumentTypeError('Cần định dạng name=value.')
    return key, content


def csv(value):
    parts = [part.strip() for part in value.split(',')]
    if not all(parts):
        raise argparse.ArgumentTypeError('Danh sách phân cách bằng dấu phẩy không được có mục rỗng.')
    return list(dict.fromkeys(parts))


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default


class Company:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else root_path()
        self.state = self.root / 'state'

    @contextmanager
    def lock(self):
        self.state.mkdir(parents=True, exist_ok=True)
        # Không xoá file khoá: mọi tiến trình phải khoá cùng một inode.
        with (self.state / '.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def room(self, key):
        validate_key(key)
        result = read_json(self.state / 'rooms' / (key + '.json'), None)
        if result is None:
            raise UserError('Không tìm thấy phòng: ' + key)
        return result

    def rooms(self):
        return [read_json(path, None) for path in sorted((self.state / 'rooms').glob('*.json'))]

    def company(self):
        company = read_json(self.state / 'company.json', {'appKey': None})
        company.setdefault('keyQueue', [])
        return company

    def _hand_over(self, company):
        """Nhả chìa khoá; còn phòng active xếp hàng thì chuyển ngay cho phòng đầu hàng."""
        company['appKey'] = None
        while company['keyQueue']:
            nxt = company['keyQueue'].pop(0)
            path = self.state / 'rooms' / (nxt['room'] + '.json')
            if path.exists() and read_json(path, {}).get('status') == 'active':
                company['appKey'] = {'room': nxt['room'], 'since': now()}
                return nxt['room']
        return None

    def _snapshot(self):
        rooms = self.rooms()
        cutoff = datetime.now(TZ) - timedelta(days=7)
        visible = [room for room in rooms if room['status'] == 'active' or
                   (room['status'] == 'done' and datetime.fromisoformat(room['updatedAt']) >= cutoff)]
        visible.sort(key=lambda room: (room['status'] != 'active', room['createdAt'], room['key']))
        queue = []
        for room in rooms:
            queue.extend(dict(ask, options=effective_options(ask)) for ask in room['asks'] if ask['status'] == 'open')
            queue.extend(bug for bug in room['bugs'] if bug['needsBoss'] and bug['status'] not in BUG_SETTLED)
        queue.sort(key=lambda item: (item['createdAt'], item['id']))
        events_path = self.state / 'events.jsonl'
        events = []
        if events_path.exists():
            with events_path.open(encoding='utf-8') as stream:
                from collections import deque
                events = [json.loads(line) for line in deque(stream, maxlen=50) if line.strip()]
        return {'generatedAt': now(), 'appKey': self.company()['appKey'], 'keyQueue': self.company()['keyQueue'],
                'rooms': visible, 'myQueue': queue, 'events': events[::-1]}

    def snapshot(self):
        with self.lock():
            return self._snapshot()

    def save(self, room, event_type, fields=None, company=None):
        """Gọi khi đã giữ khoá; mỗi lệnh ghi đúng một sự kiện."""
        stamp = now()
        room['updatedAt'] = stamp
        atomic_write(self.state / 'rooms' / (room['key'] + '.json'),
                     json.dumps(room, ensure_ascii=False, indent=2) + '\n')
        if company is not None or not (self.state / 'company.json').exists():
            atomic_write(self.state / 'company.json',
                         json.dumps(company if company is not None else self.company(), ensure_ascii=False) + '\n')
        self._append_event(stamp, event_type, room['key'], fields)

    def _append_event(self, stamp, event_type, room_key, fields):
        event = {'ts': stamp, 'type': event_type, 'room': room_key, **(fields or {})}
        with (self.state / 'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        atomic_write(self.root / 'data' / 'board.js',
                     'window.BOARD = ' + json.dumps(self._snapshot(), ensure_ascii=False) + ';\n')
        return event

    def record(self, event_type, fields=None, room_key=None):
        """Ghi một sự kiện mà KHÔNG đổi state phòng (nhịp kiểm dùng). room_key=None ⇒ sự kiện cấp công ty,
        không gắn phòng nào; wait-event --room KEY sẽ không khớp nó, Thư ký (không lọc phòng) thì có."""
        with self.lock():
            if room_key is not None:
                self.room(room_key)
            return self._append_event(now(), event_type, room_key, fields)

    def find_item(self, item_id, collection, marker):
        if not isinstance(item_id, str):
            raise UserError('ID phải là chuỗi.')
        match = re.fullmatch(r'([A-Z0-9-]{2,24})-' + marker + r'([1-9][0-9]*)', item_id)
        if not match:
            raise UserError('ID không hợp lệ: ' + item_id)
        room = self.room(match.group(1))
        item = next((item for item in room[collection] if item['id'] == item_id), None)
        if item is None:
            raise UserError('Không tìm thấy ID: ' + item_id)
        return room, item

    def resolve_ask(self, ask_id, choice, note=None, via='terminal'):
        if not isinstance(choice, str) or not choice.strip():
            raise UserError('choice phải là chuỗi không rỗng.')
        if note is not None and not isinstance(note, str):
            raise UserError('note phải là chuỗi.')
        if via not in VIA:
            raise UserError('Nguồn trả lời không hợp lệ.')
        with self.lock():
            room, ask = self.find_item(ask_id, 'asks', 'a')
            if ask['status'] != 'open':
                raise UserError('Câu hỏi đã được trả lời: ' + ask_id)
            keys = [option['key'] for option in effective_options(ask)]
            if choice not in keys:
                raise UserError('choice phải khớp một phương án: ' + ', '.join(keys))
            if choice in NOTE_CHOICES and not (note or '').strip():
                raise UserError('Phương án này cần câu trả lời trong ghi chú — gõ vào ô ghi chú rồi mới gửi.')
            stamp = now()
            ask.update(status='resolved', choice=choice, note=note, answeredVia=via, resolvedAt=stamp)
            # Qua cổng = chọn một phương án cụ thể: 'ok' của câu duyệt, hay hướng a/b/c của cổng 2.
            # 'sua' (cần sửa) và 'khac' (Sếp tự viết hướng khác) thì Manager phải trình lại.
            if ask['gate'] is not None and choice not in ('sua', OTHER):
                room['gates'][str(ask['gate'])] = {'at': stamp, 'choice': choice, 'askId': ask_id}
            self.save(room, 'ask_resolved', {'askId': ask_id, 'via': via, 'choice': choice, 'note': note})
            return ask

    def reopen_ask(self, ask_id, note=None):
        """Sếp bấm nhầm: đưa câu hỏi về trạng thái mở, gỡ cổng mà chính câu trả lời đó đã ghi."""
        with self.lock():
            room, ask = self.find_item(ask_id, 'asks', 'a')
            if ask['status'] != 'resolved':
                raise UserError('Câu hỏi đang mở, không cần mở lại: ' + ask_id)
            if ask['gate'] is not None:
                gate = room['gates'].get(str(ask['gate']))
                # Chỉ gỡ khi cổng do chính ask này ghi; ask sau đã duyệt lại thì giữ.
                if gate and gate.get('askId') == ask_id:
                    room['gates'][str(ask['gate'])] = None
            previous = ask['choice']
            ask.update(status='open', choice=None, note=None, answeredVia=None, resolvedAt=None)
            self.save(room, 'ask_reopened', {'askId': ask_id, 'note': note, 'previousChoice': previous})
            return ask

    def cancel_ask(self, ask_id, note=None):
        """Manager rút câu hỏi chưa ai trả lời (ví dụ thay câu hỏi mở bằng câu có phương án)."""
        with self.lock():
            room, ask = self.find_item(ask_id, 'asks', 'a')
            if ask['status'] != 'open':
                raise UserError('Chỉ rút được câu hỏi đang mở: ' + ask_id)
            ask.update(status='cancelled', note=note, resolvedAt=now())
            self.save(room, 'ask_cancelled', {'askId': ask_id, 'note': note})
            return ask

    def forward_failed(self, ask_id, detail):
        """Board không chuyển được câu trả lời vào terminal Manager ⇒ để lại sự kiện cho Thư ký xử lý tay."""
        with self.lock():
            room, _ = self.find_item(ask_id, 'asks', 'a')
            self.save(room, 'forward_failed', {'askId': ask_id, 'detail': detail})

    def execute(self, args):
        if args.command == 'snapshot':
            return self.snapshot()
        if args.command == 'ask' and args.action == 'resolve':
            return self.resolve_ask(args.id, args.choice, args.note, args.via)
        if args.command == 'ask' and args.action == 'reopen':
            return self.reopen_ask(args.id, args.note)
        if args.command == 'ask' and args.action == 'cancel':
            return self.cancel_ask(args.id, args.note)
        with self.lock():
            return self._execute(args)

    def _execute(self, a):
        command, action = a.command, getattr(a, 'action', None)
        if command == 'room' and action == 'show':
            return self.room(a.key)
        if command == 'room' and action == 'list':
            return [room for room in self.rooms() if a.all or room['status'] == 'active']
        if command == 'ask' and action == 'list':
            rooms = [self.room(a.room)] if a.room else self.rooms()
            return [ask for room in rooms for ask in room['asks'] if not a.open or ask['status'] == 'open']
        if command == 'key' and action == 'status':
            return self.company()

        fields, company = {}, None
        if command == 'room' and action == 'new':
            validate_key(a.key)
            if (self.state / 'rooms' / (a.key + '.json')).exists():
                raise UserError('Phòng đã tồn tại: ' + a.key)
            stamp = now()
            room = {'key': a.key, 'title': a.title, 'status': 'active', 'step': 'hoi-dap',
                    'branch': a.branch or 'phong/' + a.key.lower(),
                    'worktree': a.worktree or '/Users/tien/orca/workspaces/sportshub/' + a.key.lower(),
                    'managerTerminal': a.manager_terminal, 'roles': list(ROLES), 'needsAppKey': True,
                    'lanes': [], 'asks': [], 'bugs': [], 'gates': {str(n): None for n in range(1, 7)},
                    'links': {}, 'overlaps': [], 'evidence': [], 'createdAt': stamp, 'updatedAt': stamp}
            event_type, result = 'room_opened', room
        else:
            if command == 'bug' and action == 'set':
                room, bug = self.find_item(a.id, 'bugs', 'b')
            else:
                room = self.room(a.key)
            result = room
            if command == 'room':
                if action == 'set':
                    for arg, field in [('step', 'step'), ('title', 'title'), ('manager_terminal', 'managerTerminal'),
                                       ('roles', 'roles'), ('status', 'status')]:
                        value = getattr(a, arg)
                        if value is not None:
                            room[field] = value
                            fields[field] = value
                    if a.needs_app_key is not None:
                        room['needsAppKey'] = a.needs_app_key == 'yes'
                        fields['needsAppKey'] = room['needsAppKey']
                    if a.link:
                        room['links'].update(a.link)
                        fields['links'] = dict(a.link)
                    if a.status in ('done', 'cancelled'):
                        # Phòng đóng hay huỷ thì không được ôm chìa khoá hay chỗ xếp hàng.
                        company = self.company()
                        company['keyQueue'] = [q for q in company['keyQueue'] if q['room'] != room['key']]
                        if company['appKey'] and company['appKey']['room'] == room['key']:
                            fields['keyHandedTo'] = self._hand_over(company)
                    event_type = 'room_changed'
                else:
                    room.update(status='done', step='xong')
                    company = self.company()
                    company['keyQueue'] = [q for q in company['keyQueue'] if q['room'] != room['key']]
                    if company['appKey'] and company['appKey']['room'] == room['key']:
                        fields['keyReleased'] = True
                        fields['keyHandedTo'] = self._hand_over(company)
                    event_type = 'room_done'
                    result = {'room': room, 'cleanupCommand': 'git worktree remove -- ' + shlex.quote(room['worktree'])}
            elif command == 'lane':
                lane = next((lane for lane in room['lanes'] if lane['handle'] == a.handle), None)
                if action == 'add':
                    if lane is not None:
                        raise UserError('Handle lane đã tồn tại: ' + a.handle)
                    gate_bypassed = (a.role == 'dev-web' and 'designer' in room['roles']
                                     and not room['gates'].get(UI_GATE))
                    if gate_bypassed and not a.force_gate:
                        raise UserError('Phòng ' + room['key'] + ' có vai designer mà cổng 3 (giao diện mẫu) chưa duyệt '
                                        '— chưa được mở lane dev-web. Chờ Sếp duyệt cổng 3; Sếp đã đồng ý ngoại lệ '
                                        'thì chạy lại với --force-gate.')
                    lane = {'role': a.role, 'handle': a.handle, 'model': a.model,
                            'status': 'running', 'note': '', 'updatedAt': now()}
                    room['lanes'].append(lane)
                else:
                    if lane is None:
                        raise UserError('Không tìm thấy lane: ' + a.handle)
                    lane.update(status=a.status, updatedAt=now())
                    if a.note is not None:
                        lane['note'] = a.note
                event_type, fields, result = 'lane_changed', dict(lane), lane
                if action == 'add' and gate_bypassed:
                    # Để lại dấu trong sổ sự kiện: ai đọc lại cũng thấy lane này mở trước cổng 3.
                    fields.update(note='Mở lane dev-web trước cổng 3 (--force-gate): Sếp đồng ý ngoại lệ.',
                                  forceGate=True)
            elif command == 'ask':
                if a.kind == 'duyet' and a.gate is None:
                    raise UserError('Câu hỏi duyệt cần --gate 1–6.')
                options = a.option or [(option['key'], option['label'])
                                       for option in effective_options({'kind': a.kind, 'options': []})]
                if a.kind == 'quyet':
                    # Sếp chọn bằng một cú bấm; chỉ gõ khi không phương án nào ổn.
                    if len([key for key, _ in a.option if key != OTHER]) < 2:
                        raise UserError('Câu quyết định cần ít nhất 2 phương án (--option k="…"), kèm --recommend. '
                                        'Mỗi câu hỏi một ask; CLI tự thêm phương án "Khác — tự viết".')
                    if OTHER not in [key for key, _ in options]:
                        options = options + [(OTHER, 'Khác — tự viết')]
                keys = [key for key, _ in options]
                if len(set(keys)) != len(keys):
                    raise UserError('Khoá phương án không được trùng.')
                if a.kind == 'duyet' and 'ok' not in keys:
                    raise UserError('Câu hỏi duyệt phải có phương án ok.')
                if a.recommend is not None and a.recommend not in keys:
                    raise UserError('--recommend phải khớp một phương án.')
                number = max((int(ask['id'].rsplit('-a', 1)[1]) for ask in room['asks']), default=0) + 1
                ask = {'id': room['key'] + '-a' + str(number), 'room': room['key'], 'kind': a.kind,
                       'gate': a.gate, 'title': a.title, 'context': a.context,
                       'options': [{'key': key, 'label': label} for key, label in options],
                       'recommend': a.recommend, 'links': a.link, 'status': 'open', 'choice': None,
                       'note': None, 'answeredVia': None, 'createdAt': now(), 'resolvedAt': None}
                room['asks'].append(ask)
                event_type, fields, result = 'ask_opened', {'askId': ask['id']}, ask
            elif command == 'bug':
                if action == 'add':
                    number = max((int(bug['id'].rsplit('-b', 1)[1]) for bug in room['bugs']), default=0) + 1
                    stamp = now()
                    bug = {'id': room['key'] + '-b' + str(number), 'room': room['key'], 'title': a.title,
                           'area': a.area, 'steps': a.steps, 'shots': a.shot, 'severity': a.severity,
                           'status': 'open', 'assignee': None, 'needsBoss': a.needs_boss,
                           'history': [{'at': stamp, 'by': a.by, 'status': 'open', 'note': ''}],
                           'createdAt': stamp, 'updatedAt': stamp}
                    room['bugs'].append(bug)
                    event_type = 'bug_opened'
                else:
                    if a.status == 'closed' and a.by != 'qa':
                        raise UserError('Chỉ --by qa được đóng bug.')
                    if a.status == 'deferred' and a.status != bug['status'] and not (a.note or '').strip():
                        raise UserError('Dời lỗi sang backlog cần --note trỏ tới dòng backlog hoặc commit ghi nó.')
                    if a.status and a.status != bug['status'] and a.status not in BUG_TRANSITIONS[bug['status']]:
                        raise UserError('Chuyển trạng thái bug không hợp lệ: ' + bug['status'] + ' → ' + a.status)
                    if a.status:
                        bug['status'] = a.status
                    if a.assignee is not None:
                        bug['assignee'] = a.assignee
                    bug['updatedAt'] = now()
                    bug['history'].append({'at': bug['updatedAt'], 'by': a.by,
                                           'status': bug['status'], 'note': a.note or ''})
                    event_type = 'bug_changed'
                fields = {'bugId': bug['id'], 'status': bug['status'], 'assignee': bug['assignee']}
                result = bug
            elif command == 'key':
                company = self.company()
                holder = company['appKey']
                if action == 'request':
                    # Xin chìa khoá: trống thì nhận luôn; phòng khác giữ thì xếp hàng, Thư ký đi hỏi phòng đang giữ.
                    if room['status'] != 'active':
                        raise UserError('Chỉ phòng active được giữ chìa khoá app.')
                    if holder is None:
                        company['appKey'] = {'room': room['key'], 'since': now()}
                        event_type = 'key_taken'
                    elif holder['room'] == room['key']:
                        event_type, fields = 'note', {'text': 'Đã giữ chìa khoá app.'}
                    else:
                        if all(q['room'] != room['key'] for q in company['keyQueue']):
                            company['keyQueue'].append({'room': room['key'], 'since': now(), 'reason': a.reason or ''})
                        event_type = 'key_requested'
                        fields = {'holder': holder['room'], 'reason': a.reason or '',
                                  'position': [q['room'] for q in company['keyQueue']].index(room['key']) + 1}
                    result = company
                    self.save(room, event_type, fields, company)
                    return result
                if holder and holder['room'] != room['key']:
                    raise KeyBusy('Chìa khoá app đang thuộc phòng ' + holder['room'])
                if action == 'take':
                    if room['status'] != 'active':
                        raise UserError('Chỉ phòng active được giữ chìa khoá app.')
                    company['appKey'] = holder or {'room': room['key'], 'since': now()}
                    event_type = 'key_taken'
                else:
                    handed = self._hand_over(company) if holder else None
                    event_type = 'key_released'
                    fields = {'handedTo': handed, 'note': a.note or ''}
                result = company
            elif command == 'overlap':
                self.room(a.other)
                if a.other == room['key']:
                    raise UserError('Phòng không thể chồng lấn với chính nó.')
                if not a.clear and not a.files:
                    raise UserError('Cần --files khi ghi chồng lấn.')
                room['overlaps'] = [entry for entry in room['overlaps'] if entry['with'] != a.other]
                fields = {'with': a.other, 'files': a.files or [], 'conflict': a.conflict, 'clear': a.clear}
                if not a.clear:
                    room['overlaps'].append({'with': a.other, 'files': a.files, 'conflict': a.conflict, 'at': now()})
                event_type = 'overlap'
            elif command == 'evidence':
                result = {'claim': a.claim, 'manager': a.manager, 'thuKy': a.thu_ky,
                          'cmd': a.cmd, 'ok': a.ok, 'at': now()}
                room['evidence'].append(result)
                event_type, fields = 'evidence', dict(result)
            elif command == 'note':
                event_type, fields = 'note', {'text': a.text}
        self.save(room, event_type, fields, company)
        return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--json', action='store_true', help='In JSON.')
    commands = p.add_subparsers(dest='command', required=True)

    def group(name, actions):
        parent = commands.add_parser(name)
        subs = parent.add_subparsers(dest='action', required=True)
        return [subs.add_parser(action) for action in actions]

    new, setting, show, listing, done = group('room', ['new', 'set', 'show', 'list', 'done'])
    for sub in (new, setting, show, done):
        sub.add_argument('key')
    new.add_argument('--title', required=True, type=nonempty)
    for name in ('branch', 'worktree', 'manager-terminal'):
        new.add_argument('--' + name, type=nonempty)
    setting.add_argument('--step', choices=STEPS)
    setting.add_argument('--title', type=nonempty)
    setting.add_argument('--manager-terminal', type=nonempty)
    setting.add_argument('--roles', type=csv)
    setting.add_argument('--needs-app-key', choices=('yes', 'no'))
    setting.add_argument('--link', action='append', type=pair, default=[])
    setting.add_argument('--status', choices=('active', 'done', 'cancelled'))
    listing.add_argument('--all', action='store_true')
    add, setting = group('lane', ['add', 'set'])
    for sub in (add, setting):
        sub.add_argument('key')
        sub.add_argument('--handle', required=True, type=nonempty)
    add.add_argument('--role', required=True, type=nonempty)
    add.add_argument('--model', default=None, type=nonempty)
    add.add_argument('--force-gate', action='store_true',
                     help='Mở lane dev-web dù cổng 3 chưa duyệt — chỉ khi Sếp đã đồng ý ngoại lệ.')
    setting.add_argument('--status', required=True, choices=('running', 'waiting', 'done', 'closed'))
    setting.add_argument('--note')
    add, resolve, reopen, cancel, listing = group('ask', ['add', 'resolve', 'reopen', 'cancel', 'list'])
    for sub in (reopen, cancel):
        sub.add_argument('id')
        sub.add_argument('--note')
    add.add_argument('key')
    add.add_argument('--kind', required=True, choices=('duyet', 'quyet', 'thaotac'))
    add.add_argument('--gate', type=int, choices=range(1, 7))
    add.add_argument('--title', required=True, type=nonempty)
    add.add_argument('--context', default='')
    add.add_argument('--option', action='append', type=pair, default=[])
    add.add_argument('--recommend', type=nonempty)
    add.add_argument('--link', action='append', default=[])
    resolve.add_argument('id')
    resolve.add_argument('--choice', required=True, type=nonempty)
    resolve.add_argument('--note')
    resolve.add_argument('--via', choices=VIA, default='terminal')
    listing.add_argument('--open', action='store_true')
    listing.add_argument('--room')
    add, setting = group('bug', ['add', 'set'])
    add.add_argument('key')
    add.add_argument('--title', required=True, type=nonempty)
    add.add_argument('--area', required=True, choices=('server', 'web'))
    add.add_argument('--steps', default='')
    add.add_argument('--shot', action='append', default=[])
    add.add_argument('--severity', choices=('high', 'normal'), default='normal')
    add.add_argument('--needs-boss', action='store_true')
    setting.add_argument('id')
    setting.add_argument('--status', choices=tuple(BUG_TRANSITIONS))
    setting.add_argument('--assignee', type=nonempty)
    setting.add_argument('--note')
    for sub in (add, setting):
        sub.add_argument('--by', required=True, type=nonempty)
    take, release, status, request = group('key', ['take', 'release', 'status', 'request'])
    for sub in (take, release, request):
        sub.add_argument('key')
    request.add_argument('--reason')
    release.add_argument('--note')
    overlap = commands.add_parser('overlap')
    overlap.add_argument('key')
    overlap.add_argument('--with', dest='other', required=True)
    overlap.add_argument('--files', type=csv)
    overlap.add_argument('--conflict', action='store_true')
    overlap.add_argument('--clear', action='store_true')
    evidence = commands.add_parser('evidence')
    evidence.add_argument('key')
    for name in ('claim', 'manager', 'thu-ky', 'cmd'):
        evidence.add_argument('--' + name, required=True, type=nonempty)
    outcome = evidence.add_mutually_exclusive_group(required=True)
    outcome.add_argument('--ok', dest='ok', action='store_true')
    outcome.add_argument('--mismatch', dest='ok', action='store_false')
    note = commands.add_parser('note')
    note.add_argument('key')
    note.add_argument('text', type=nonempty)
    commands.add_parser('snapshot')
    # Cho phép --json ở mọi cấp lệnh mà không xử lý lại giá trị của option khác.
    def add_json(subparser):
        for action in subparser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for child in action.choices.values():
                    child.add_argument('--json', action='store_true', default=argparse.SUPPRESS)
                    add_json(child)
    add_json(p)
    return p


def main(argv=None):
    p = parser()
    a = p.parse_args(argv)
    try:
        result = Company().execute(a)
        if a.json or a.command == 'snapshot' or getattr(a, 'action', None) in ('show', 'list', 'status'):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif a.command == 'ask' and a.action == 'add':
            print(result['id'])
        elif a.command == 'room' and a.action == 'done':
            print('Phòng đã xong. Lệnh dọn worktree (chưa chạy):\n' + result['cleanupCommand'])
        elif isinstance(result, dict) and 'id' in result:
            print(result['id'])
        else:
            print('OK')
        return 0
    except KeyBusy as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except (UserError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
