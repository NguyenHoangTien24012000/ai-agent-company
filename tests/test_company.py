"""Kiểm thử CLI bằng state tạm, không chạm dữ liệu công ty thật."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


REPO = Path(__file__).resolve().parents[1]
CLI = REPO / 'bin' / 'company.py'
WAITER = REPO / 'bin' / 'wait-event.sh'


class CompanyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.env = dict(os.environ, SPORTSHUB_CO=str(self.root), PYTHONDONTWRITEBYTECODE='1')
        self.run_cli('room', 'new', 'ATTEND', '--title', 'Có mặt')

    def run_cli(self, *args, code=0):
        result = subprocess.run([sys.executable, str(CLI), *args], env=self.env,
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def data(self, *args):
        return json.loads(self.run_cli(*args, '--json').stdout)

    def events(self):
        return [json.loads(line) for line in (self.root / 'state/events.jsonl').read_text().splitlines()]

    def board(self):
        text = (self.root / 'data/board.js').read_text()
        self.assertTrue(text.startswith('window.BOARD = '))
        return json.loads(text.removeprefix('window.BOARD = ').strip().removesuffix(';'))

    def test_room_defaults_and_all_set_fields(self):
        room = self.data('room', 'show', 'ATTEND')
        self.assertEqual(room['branch'], 'phong/attend')
        self.assertEqual(room['worktree'], '/Users/tien/orca/workspaces/sportshub/attend')
        self.assertEqual(room['step'], 'hoi-dap')
        self.assertEqual(room['gates'], {str(n): None for n in range(1, 7)})
        self.assertEqual(datetime.fromisoformat(room['createdAt']).utcoffset(), timedelta(hours=7))
        self.assertEqual(self.events()[0]['type'], 'room_opened')
        self.run_cli('room', 'set', 'ATTEND', '--step', 'code', '--title', 'Mới',
                     '--manager-terminal', 'term_1', '--roles', 'qa,dev-web',
                     '--needs-app-key', 'no', '--link', 'spec=.scratch/spec.md',
                     '--link', 'featureDoc=docs/features/test.md', '--status', 'active')
        room = self.data('room', 'show', 'ATTEND')
        self.assertEqual((room['title'], room['step'], room['managerTerminal']), ('Mới', 'code', 'term_1'))
        self.assertEqual(room['roles'], ['qa', 'dev-web'])
        self.assertFalse(room['needsAppKey'])
        self.assertEqual(room['links']['spec'], '.scratch/spec.md')
        self.assertEqual(len(self.events()), 2)
        self.assertEqual(self.board()['rooms'], [room])
        self.assertEqual(self.board()['events'][0]['type'], 'room_changed')
        self.run_cli('room', 'new', 'TEAM-STATS', '--title', 'Đội', '--branch', 'custom',
                     '--worktree', '/tmp/example', '--manager-terminal', 'term_2')
        self.run_cli('room', 'set', 'TEAM-STATS', '--status', 'cancelled')
        self.assertEqual(len(self.data('room', 'list')), 1)
        self.assertEqual(len(self.data('room', 'list', '--all')), 2)

    def test_all_steps_and_json_positions(self):
        for step in ('hoi-dap', 'cho-goi', 'thiet-ke', 'kien-truc', 'ke-hoach-test',
                     'code', 'test', 'review', 'cho-check', 'chuan-bi-gop', 'cho-gop', 'xong'):
            self.run_cli('room', 'set', 'ATTEND', '--step', step)
        for args in [('--json', 'room', 'show', 'ATTEND'), ('room', '--json', 'show', 'ATTEND'),
                     ('room', 'show', 'ATTEND', '--json')]:
            self.assertEqual(json.loads(self.run_cli(*args).stdout)['key'], 'ATTEND')

    def test_invalid_input_does_not_change_state(self):
        before = self.events()
        commands = [('room', 'new', '../escape', '--title', 'Sai'),
                    ('room', 'new', 'a', '--title', 'Sai'),
                    ('room', 'new', 'ATTEND', '--title', 'Trùng'),
                    ('room', 'show', 'MISSING'),
                    ('room', 'set', 'ATTEND', '--step', 'bad'),
                    ('room', 'set', 'ATTEND', '--link', 'bad'),
                    ('room', 'set', 'ATTEND', '--roles', 'qa,'),
                    ('ask', 'resolve', '../../x', '--choice', 'ok'),
                    ('ask', 'add', 'ATTEND', '--kind', 'duyet', '--title', 'Thiếu gate'),
                    ('ask', 'add', 'ATTEND', '--kind', 'duyet', '--gate', '7', '--title', 'Sai'),
                    ('ask', 'add', 'ATTEND', '--kind', 'duyet', '--gate', '1', '--title', 'Sai', '--option', 'no=Không'),
                    ('ask', 'add', 'ATTEND', '--kind', 'quyet', '--title', 'Sai', '--option', 'a=A', '--option', 'a=B'),
                    ('ask', 'add', 'ATTEND', '--kind', 'quyet', '--title', 'Sai', '--option', 'a=A', '--option', 'b=B',
                     '--recommend', 'missing')]
        for command in commands:
            with self.subTest(command=command):
                result = self.run_cli(*command, code=2)
                self.assertTrue(result.stderr.strip())
                self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(before, self.events())

    def test_asks_resolve_gates_options_and_sources(self):
        ask_id = self.run_cli('ask', 'add', 'ATTEND', '--kind', 'duyet', '--gate', '1', '--title', 'Duyệt').stdout.strip()
        self.assertEqual(ask_id, 'ATTEND-a1')
        ask = self.data('ask', 'list', '--open', '--room', 'ATTEND')[0]
        self.assertEqual([item['key'] for item in ask['options']], ['ok', 'sua'])
        self.run_cli('ask', 'resolve', ask_id, '--choice', 'missing', code=2)
        self.run_cli('ask', 'resolve', ask_id, '--choice', 'ok', '--note', 'Đồng ý')
        room = self.data('room', 'show', 'ATTEND')
        self.assertEqual(room['gates']['1']['askId'], ask_id)
        self.assertEqual(room['asks'][0]['answeredVia'], 'terminal')
        event = self.events()[-1]
        self.assertEqual((event['type'], event['via'], event['choice'], event['note']),
                         ('ask_resolved', 'terminal', 'ok', 'Đồng ý'))
        self.run_cli('ask', 'resolve', ask_id, '--choice', 'ok', code=2)
        self.run_cli('ask', 'add', 'ATTEND', '--kind', 'duyet', '--gate', '2', '--title', 'Ý tưởng')
        self.run_cli('ask', 'resolve', 'ATTEND-a2', '--choice', 'sua', '--via', 'thu-ky')
        self.assertIsNone(self.data('room', 'show', 'ATTEND')['gates']['2'])
        ask = self.data('ask', 'add', 'ATTEND', '--kind', 'quyet', '--title', 'Chọn', '--context', 'Ngữ cảnh',
                        '--option', 'a=Phương án A', '--option', 'b=Phương án B', '--recommend', 'a', '--link', 'doc.md')
        self.assertEqual(ask['id'], 'ATTEND-a3')
        self.assertEqual(ask['links'], ['doc.md'])
        self.run_cli('ask', 'resolve', ask['id'], '--choice', 'b', '--via', 'board')
        self.run_cli('ask', 'add', 'ATTEND', '--kind', 'thaotac', '--title', 'Tự làm')
        self.run_cli('ask', 'resolve', 'ATTEND-a4', '--choice', 'done')
        self.assertEqual(self.data('ask', 'list', '--open'), [])
        self.assertEqual(len(self.data('ask', 'list')), 4)

    def test_decision_asks_need_options_and_get_an_other_choice(self):
        # Sếp muốn chọn bằng một cú bấm: câu quyết định phải có phương án, "Khác" là lối thoát duy nhất phải gõ.
        before = self.events()
        for options in ([], ['--option', 'a=Một phương án']):
            with self.subTest(options=options):
                result = self.run_cli('ask', 'add', 'ATTEND', '--kind', 'quyet', '--title', 'Hỏi', *options, code=2)
                self.assertIn('2 phương án', result.stderr)
        self.assertEqual(before, self.events())
        ask = self.data('ask', 'add', 'ATTEND', '--kind', 'quyet', '--title', 'Ai chốt có mặt?',
                        '--option', 'a=Đội trưởng', '--option', 'b=Ai cũng chốt được', '--recommend', 'a')
        self.assertEqual([(item['key'], item['label']) for item in ask['options']],
                         [('a', 'Đội trưởng'), ('b', 'Ai cũng chốt được'), ('khac', 'Khác — tự viết')])
        chore = self.data('ask', 'add', 'ATTEND', '--kind', 'thaotac', '--title', 'Bật Docker')
        self.assertEqual([item['key'] for item in chore['options']], ['done'])
        for note in ([], ['--note', '   ']):
            with self.subTest(note=note):
                result = self.run_cli('ask', 'resolve', ask['id'], '--choice', 'khac', *note, code=2)
                self.assertIn('ghi chú', result.stderr)
        self.run_cli('ask', 'resolve', ask['id'], '--choice', 'khac', '--note', 'Phó đội cũng chốt được')
        self.run_cli('ask', 'resolve', chore['id'], '--choice', 'done')
        self.assertEqual(self.data('ask', 'list', '--open'), [])

    def test_gate_choice_question_records_gate_for_concrete_option(self):
        # Cổng 2 là câu chọn hướng (a/b/c), không có 'ok': chọn một hướng cụ thể vẫn là qua cổng.
        def gate_ask():
            return self.data('ask', 'add', 'ATTEND', '--kind', 'quyet', '--gate', '2', '--title', 'Chọn hướng',
                             '--option', 'a=Hướng 1', '--option', 'b=Hướng 2')['id']
        first = gate_ask()
        self.run_cli('ask', 'resolve', first, '--choice', 'khac', '--note', 'Hướng khác hẳn')
        self.assertIsNone(self.data('room', 'show', 'ATTEND')['gates']['2'])
        second = gate_ask()
        self.run_cli('ask', 'resolve', second, '--choice', 'b', '--via', 'board')
        gate = self.data('room', 'show', 'ATTEND')['gates']['2']
        self.assertEqual((gate['askId'], gate['choice']), (second, 'b'))

    def test_cancel_open_ask(self):
        ask = self.data('ask', 'add', 'ATTEND', '--kind', 'quyet', '--title', 'Hỏi',
                        '--option', 'a=A', '--option', 'b=B')
        self.run_cli('ask', 'cancel', ask['id'], '--note', 'Thay bằng ATTEND-a2')
        self.assertEqual(self.data('ask', 'list', '--open'), [])
        self.assertEqual(self.board()['myQueue'], [])
        event = self.events()[-1]
        self.assertEqual((event['type'], event['askId'], event['note']), ('ask_cancelled', ask['id'], 'Thay bằng ATTEND-a2'))
        self.run_cli('ask', 'cancel', ask['id'], code=2)                   # đã rút thì thôi
        self.run_cli('ask', 'resolve', ask['id'], '--choice', 'a', code=2)

    def test_legacy_ask_without_options_shows_default_button_on_board(self):
        # Ask ghi trước bản sửa có options rỗng trong state; board và resolve vẫn phải dùng được.
        self.run_cli('ask', 'add', 'ATTEND', '--kind', 'quyet', '--title', 'Cũ', '--option', 'a=A', '--option', 'b=B')
        path = self.root / 'state/rooms/ATTEND.json'
        room = json.loads(path.read_text()); room['asks'][0]['options'] = []
        path.write_text(json.dumps(room))
        queue = self.data('snapshot')['myQueue']
        self.assertEqual([item['key'] for item in queue[0]['options']], ['tra-loi'])
        self.assertEqual(json.loads(path.read_text())['asks'][0]['options'], [])
        self.run_cli('ask', 'resolve', 'ATTEND-a1', '--choice', 'tra-loi', code=2)
        self.run_cli('ask', 'resolve', 'ATTEND-a1', '--choice', 'tra-loi', '--note', 'Trả lời')

    def test_reopen_ask_after_mistaken_answer(self):
        ask_id = self.run_cli('ask', 'add', 'ATTEND', '--kind', 'duyet', '--gate', '1', '--title', 'Duyệt').stdout.strip()
        self.run_cli('ask', 'reopen', ask_id, code=2)                      # đang mở thì không mở lại
        self.run_cli('ask', 'resolve', ask_id, '--choice', 'ok', '--via', 'board')
        self.assertIsNotNone(self.data('room', 'show', 'ATTEND')['gates']['1'])
        self.run_cli('ask', 'reopen', ask_id, '--note', 'Sếp bấm nhầm')
        room = self.data('room', 'show', 'ATTEND')
        self.assertIsNone(room['gates']['1'])                              # bấm nhầm không được coi là đã duyệt
        ask = room['asks'][0]
        self.assertEqual((ask['status'], ask['choice'], ask['note'], ask['answeredVia'], ask['resolvedAt']),
                         ('open', None, None, None, None))
        event = self.events()[-1]
        self.assertEqual((event['type'], event['askId'], event['note'], event['previousChoice']),
                         ('ask_reopened', ask_id, 'Sếp bấm nhầm', 'ok'))
        self.assertEqual([item['id'] for item in self.board()['myQueue']], [ask_id])
        self.run_cli('ask', 'reopen', 'ATTEND-a9', code=2)

    def test_reopen_keeps_gate_recorded_by_a_later_ask(self):
        first = self.run_cli('ask', 'add', 'ATTEND', '--kind', 'duyet', '--gate', '2', '--title', 'Bản 1').stdout.strip()
        self.run_cli('ask', 'resolve', first, '--choice', 'sua', '--note', 'Sửa màu')
        second = self.run_cli('ask', 'add', 'ATTEND', '--kind', 'duyet', '--gate', '2', '--title', 'Bản 2').stdout.strip()
        self.run_cli('ask', 'resolve', second, '--choice', 'ok')
        self.run_cli('ask', 'reopen', first)
        self.assertEqual(self.data('room', 'show', 'ATTEND')['gates']['2']['askId'], second)

    def test_lane_lifecycle(self):
        lane = self.data('lane', 'add', 'ATTEND', '--role', 'qa', '--handle', 'term_qa', '--model', 'opus')
        self.assertEqual(lane['status'], 'running')
        self.run_cli('lane', 'add', 'ATTEND', '--role', 'qa', '--handle', 'term_qa', code=2)
        for status in ('waiting', 'done', 'closed'):
            lane = self.data('lane', 'set', 'ATTEND', '--handle', 'term_qa', '--status', status, '--note', 'Ghi chú')
            self.assertEqual(lane['status'], status)
            self.assertEqual(lane['note'], 'Ghi chú')
        self.run_cli('lane', 'set', 'ATTEND', '--handle', 'missing', '--status', 'done', code=2)
        self.assertEqual(self.events()[-1]['type'], 'lane_changed')

    def test_bug_lifecycle_qa_only_closure_and_queue(self):
        bug = self.data('bug', 'add', 'ATTEND', '--title', 'Lỗi', '--area', 'web', '--steps', 'Mở trang',
                        '--shot', 'a.png', '--shot', 'b.png', '--severity', 'high', '--needs-boss', '--by', 'qa')
        self.assertEqual(bug['id'], 'ATTEND-b1')
        self.assertEqual(bug['shots'], ['a.png', 'b.png'])
        self.assertEqual(self.data('snapshot')['myQueue'][0]['id'], bug['id'])
        self.run_cli('bug', 'set', bug['id'], '--status', 'closed', '--by', 'qa', code=2)
        for status in ('fixing', 'retest', 'fixing', 'retest'):
            self.run_cli('bug', 'set', bug['id'], '--status', status, '--assignee', 'dev-web', '--note', 'Kiểm tra', '--by', 'dev-web')
        self.run_cli('bug', 'set', bug['id'], '--status', 'closed', '--by', 'dev-web', code=2)
        bug = self.data('bug', 'set', bug['id'], '--status', 'closed', '--by', 'qa')
        self.assertEqual(bug['status'], 'closed')
        self.assertEqual(len(bug['history']), 6)
        self.assertEqual(self.data('snapshot')['myQueue'], [])
        self.assertEqual(self.events()[-1]['assignee'], 'dev-web')
        self.run_cli('bug', 'set', bug['id'], '--status', 'fixing', '--by', 'qa', code=2)

    def test_app_key_exclusion_release_and_room_done(self):
        self.run_cli('room', 'new', 'TEAM', '--title', 'Đội')
        self.run_cli('key', 'take', 'ATTEND')
        since = self.data('key', 'status')['appKey']['since']
        self.run_cli('key', 'take', 'ATTEND')
        self.assertEqual(self.data('key', 'status')['appKey']['since'], since)
        busy = self.run_cli('key', 'take', 'TEAM', code=3)
        self.assertIn('ATTEND', busy.stderr)
        self.run_cli('key', 'release', 'TEAM', code=3)
        self.run_cli('key', 'release', 'ATTEND')
        self.assertIsNone(self.data('key', 'status')['appKey'])
        self.run_cli('key', 'take', 'ATTEND')
        before = len(self.events())
        done = self.run_cli('room', 'done', 'ATTEND')
        self.assertIn('git worktree remove -- ', done.stdout)
        self.assertEqual(len(self.events()), before + 1)
        self.assertEqual(self.events()[-1]['type'], 'room_done')
        self.assertIsNone(self.board()['appKey'])
        room = self.data('room', 'show', 'ATTEND')
        self.assertEqual((room['status'], room['step']), ('done', 'xong'))
        self.run_cli('key', 'take', 'ATTEND', code=2)

    def test_overlap_evidence_note(self):
        self.run_cli('room', 'new', 'TEAM', '--title', 'Đội')
        self.run_cli('overlap', 'ATTEND', '--with', 'TEAM', '--files', 'a.py,b.py', '--conflict')
        self.assertEqual(self.data('room', 'show', 'ATTEND')['overlaps'][0]['files'], ['a.py', 'b.py'])
        self.run_cli('overlap', 'ATTEND', '--with', 'TEAM', '--clear')
        self.assertEqual(self.data('room', 'show', 'ATTEND')['overlaps'], [])
        for flag in ('--ok', '--mismatch'):
            evidence = self.data('evidence', 'ATTEND', '--claim', 'Đã test', '--manager', 'Xanh',
                                 '--thu-ky', 'Chạy lại', '--cmd', 'python3 -m unittest', flag)
            self.assertEqual(evidence['ok'], flag == '--ok')
        self.run_cli('note', 'ATTEND', 'Ghi chú tiếng Việt')
        self.assertEqual(self.events()[-1]['text'], 'Ghi chú tiếng Việt')
        self.assertEqual(self.board()['events'][0]['type'], 'note')

    def test_snapshot_visibility_queue_and_fifty_events(self):
        self.run_cli('room', 'new', 'OLD', '--title', 'Cũ')
        self.run_cli('room', 'done', 'OLD')
        path = self.root / 'state/rooms/OLD.json'
        room = json.loads(path.read_text())
        room['updatedAt'] = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        path.write_text(json.dumps(room))
        self.run_cli('room', 'new', 'RECENT', '--title', 'Vừa xong')
        self.run_cli('room', 'done', 'RECENT')
        self.run_cli('ask', 'add', 'ATTEND', '--kind', 'thaotac', '--title', 'Việc trước')
        self.run_cli('bug', 'add', 'ATTEND', '--title', 'Việc sau', '--area', 'server', '--needs-boss', '--by', 'qa')
        for index in range(52):
            self.run_cli('note', 'ATTEND', str(index))
        snapshot = self.data('snapshot')
        self.assertEqual([room['key'] for room in snapshot['rooms']], ['ATTEND', 'RECENT'])
        self.assertEqual([item['id'] for item in snapshot['myQueue']], ['ATTEND-a1', 'ATTEND-b1'])
        self.assertEqual(len(snapshot['events']), 50)
        self.assertEqual((snapshot['events'][0]['text'], snapshot['events'][-1]['text']), ('51', '2'))
        board = self.board()
        for field in ('rooms', 'myQueue', 'events', 'appKey'):
            self.assertEqual(snapshot[field], board[field])

    def test_twenty_concurrent_writers_preserve_ids_and_events(self):
        def write(index):
            return subprocess.run([sys.executable, str(CLI), 'ask', 'add', 'ATTEND', '--kind', 'quyet',
                                   '--title', str(index), '--option', 'ok=OK', '--option', 'no=Không'], env=self.env,
                                  text=True, capture_output=True, timeout=20)
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(write, range(20)))
        for result in results:
            self.assertEqual(result.returncode, 0, result.stderr)
        room = self.data('room', 'show', 'ATTEND')
        self.assertEqual({ask['id'] for ask in room['asks']}, {'ATTEND-a' + str(n) for n in range(1, 21)})
        self.assertEqual(len(self.events()), 21)
        self.assertEqual(self.board()['rooms'][0]['asks'], room['asks'])
        self.assertEqual(len(self.board()['events']), 21)


    def test_dev_web_lane_waits_for_gate_three_when_room_has_designer(self):
        # Code web trước khi Sếp duyệt giao diện mẫu là làm hai lần: phòng có designer thì chặn tới cổng 3.
        before = self.events()
        result = self.run_cli('lane', 'add', 'ATTEND', '--role', 'dev-web', '--handle', 'term_web', code=2)
        self.assertIn('cổng 3', result.stderr)
        self.assertIn('--force-gate', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(before, self.events())
        self.run_cli('lane', 'add', 'ATTEND', '--role', 'dev-server', '--handle', 'term_server')   # vai khác không chặn
        ask_id = self.run_cli('ask', 'add', 'ATTEND', '--kind', 'duyet', '--gate', '3', '--title', 'Mẫu').stdout.strip()
        self.run_cli('ask', 'resolve', ask_id, '--choice', 'ok')
        lane = self.data('lane', 'add', 'ATTEND', '--role', 'dev-web', '--handle', 'term_web')
        self.assertEqual(lane['status'], 'running')
        event = self.events()[-1]
        self.assertEqual((event['type'], event['note']), ('lane_changed', ''))
        self.assertNotIn('forceGate', event)

    def test_dev_web_lane_without_designer_is_not_gated(self):
        self.run_cli('room', 'set', 'ATTEND', '--roles', 'techlead,dev-server,dev-web,qa,review')
        self.run_cli('lane', 'add', 'ATTEND', '--role', 'dev-web', '--handle', 'term_web')
        self.assertNotIn('forceGate', self.events()[-1])

    def test_force_gate_opens_dev_web_lane_and_leaves_a_note(self):
        lane = self.data('lane', 'add', 'ATTEND', '--role', 'dev-web', '--handle', 'term_web', '--force-gate')
        self.assertEqual(lane['role'], 'dev-web')
        event = self.events()[-1]
        self.assertEqual((event['type'], event['handle'], event['forceGate']), ('lane_changed', 'term_web', True))
        self.assertIn('cổng 3', event['note'])
        self.assertIn('--force-gate', event['note'])

    def test_bug_deferred_to_backlog(self):
        def bug(title, *flags):
            return self.data('bug', 'add', 'ATTEND', '--title', title, '--area', 'web', *flags, '--by', 'qa')['id']
        first, second, third = bug('Từ open', '--needs-boss'), bug('Từ fixing', '--needs-boss'), bug('Từ retest')
        self.assertEqual(len(self.board()['myQueue']), 2)
        before = self.events()
        for note in ([], ['--note', '  ']):
            with self.subTest(note=note):
                result = self.run_cli('bug', 'set', first, '--status', 'deferred', *note, '--by', 'manager', code=2)
                self.assertIn('backlog', result.stderr)
        self.assertEqual(before, self.events())
        deferred = self.data('bug', 'set', first, '--status', 'deferred', '--note', 'backlog: dòng "Lỗi màu nền"',
                             '--by', 'manager')
        self.assertEqual(deferred['history'][-1]['note'], 'backlog: dòng "Lỗi màu nền"')
        self.assertEqual(self.events()[-1]['status'], 'deferred')
        self.run_cli('bug', 'set', second, '--status', 'fixing', '--by', 'manager')
        self.run_cli('bug', 'set', second, '--status', 'deferred', '--note', 'commit abc1234', '--by', 'manager')
        self.assertEqual(self.board()['myQueue'], [])            # needsBoss mà dời backlog thì thôi hỏi Sếp
        for status in ('fixing', 'retest'):
            self.run_cli('bug', 'set', third, '--status', status, '--by', 'dev-web')
        self.run_cli('bug', 'set', third, '--status', 'deferred', '--note', 'x', '--by', 'manager', code=2)
        for status in ('open', 'fixing', 'retest', 'closed'):
            self.run_cli('bug', 'set', first, '--status', status, '--by', 'qa', code=2)   # dời rồi là hết vòng

    def company_state(self):
        return json.loads((self.root / 'state/company.json').read_text())

    def test_key_request_queues_and_release_hands_over(self):
        self.run_cli('room', 'new', 'FUND', '--title', 'Quỹ')
        self.run_cli('room', 'new', 'STATS', '--title', 'Thống kê')
        self.run_cli('key', 'request', 'ATTEND')
        self.assertEqual(self.company_state()['appKey']['room'], 'ATTEND')
        self.run_cli('key', 'request', 'FUND', '--reason', 'QA test quỹ')
        self.run_cli('key', 'request', 'STATS')
        self.run_cli('key', 'request', 'FUND')  # xin lại không xếp hàng hai lần
        state = self.company_state()
        self.assertEqual([q['room'] for q in state['keyQueue']], ['FUND', 'STATS'])
        requested = [e for e in self.events() if e['type'] == 'key_requested']
        self.assertEqual((requested[0]['holder'], requested[0]['position'], requested[0]['reason']),
                         ('ATTEND', 1, 'QA test quỹ'))
        self.run_cli('key', 'take', 'FUND', code=3)
        self.run_cli('key', 'release', 'ATTEND', '--note', 'QA xong')
        state = self.company_state()
        self.assertEqual(state['appKey']['room'], 'FUND')
        self.assertEqual([q['room'] for q in state['keyQueue']], ['STATS'])
        self.assertEqual(self.events()[-1]['handedTo'], 'FUND')
        self.assertEqual(self.board()['keyQueue'][0]['room'], 'STATS')

    def test_closed_room_hands_key_over_and_leaves_queue(self):
        self.run_cli('room', 'new', 'FUND', '--title', 'Quỹ')
        self.run_cli('room', 'new', 'STATS', '--title', 'Thống kê')
        self.run_cli('key', 'request', 'ATTEND')
        self.run_cli('key', 'request', 'FUND')
        self.run_cli('key', 'request', 'STATS')
        self.run_cli('room', 'set', 'FUND', '--status', 'cancelled')
        self.assertEqual([q['room'] for q in self.company_state()['keyQueue']], ['STATS'])
        self.run_cli('room', 'done', 'ATTEND')
        state = self.company_state()
        self.assertEqual((state['appKey']['room'], state['keyQueue']), ('STATS', []))
        self.assertEqual(self.events()[-1]['keyHandedTo'], 'STATS')


HEARTBEAT = REPO / 'bin' / 'heartbeat.py'


class HeartbeatTests(unittest.TestCase):
    """Nhịp kiểm chạy bằng giờ giả (--now), không sleep."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.env = dict(os.environ, SPORTSHUB_CO=str(self.root), PYTHONDONTWRITEBYTECODE='1')
        # Mặc định có watcher Thư ký đang chạy: test không phụ thuộc tiến trình thật trên máy.
        self.ps = self.root / 'ps.txt'
        self.ps.write_text('/bin/bash bin/wait-event.sh --timeout 14400\n')
        self.env['HEARTBEAT_PS_FILE'] = str(self.ps)
        self.cli('room', 'new', 'ATTEND', '--title', 'Có mặt')
        self.cli('lane', 'add', 'ATTEND', '--role', 'qa', '--handle', 'term_qa')
        self.start = datetime.now(timezone(timedelta(hours=7)))

    def cli(self, *args):
        result = subprocess.run([sys.executable, str(CLI), *args], env=self.env, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def beat(self, minutes, *args, code=0):
        when = (self.start + timedelta(minutes=minutes)).isoformat()
        result = subprocess.run([sys.executable, str(HEARTBEAT), '--once', '--now', when, *args], env=self.env,
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def events(self, *types):
        lines = (self.root / 'state/events.jsonl').read_text().splitlines()
        return [e for e in map(json.loads, lines) if not types or e['type'] in types]

    def board(self):
        text = (self.root / 'data/board.js').read_text()
        return json.loads(text.removeprefix('window.BOARD = ').strip().removesuffix(';'))

    def age_lane(self, minutes):
        # Giả lane đứng yên từ lâu mà sổ sự kiện vẫn mới (Manager vừa ghi gì đó).
        path = self.root / 'state/rooms/ATTEND.json'
        room = json.loads(path.read_text())
        room['lanes'][0]['updatedAt'] = (self.start - timedelta(minutes=minutes)).isoformat()
        path.write_text(json.dumps(room))

    def test_quiet_room_with_stale_running_lane_is_reported_once_per_threshold(self):
        self.beat(30)
        self.assertEqual(self.events('lane_stale'), [])                    # chưa tới ngưỡng 45'
        room_before = (self.root / 'state/rooms/ATTEND.json').read_text()
        self.beat(50)
        stale = self.events('lane_stale')
        self.assertEqual(len(stale), 1)
        self.assertEqual({k: stale[0][k] for k in ('room', 'handle', 'role', 'minutes')},
                         {'room': 'ATTEND', 'handle': 'term_qa', 'role': 'qa', 'minutes': 50})
        self.assertEqual(room_before, (self.root / 'state/rooms/ATTEND.json').read_text())   # không đụng state phòng
        self.assertEqual(self.board()['events'][0]['type'], 'lane_stale')
        self.beat(80)
        self.assertEqual(len(self.events('lane_stale')), 1)                # chưa qua thêm một ngưỡng
        self.beat(96)
        self.assertEqual([e['minutes'] for e in self.events('lane_stale')], [50, 96])
        marks = json.loads((self.root / 'state/heartbeat.json').read_text())
        self.assertIn('ATTEND/term_qa', marks['lanes'])

    def test_recent_room_event_or_non_running_lane_is_not_reported(self):
        self.age_lane(120)
        self.cli('note', 'ATTEND', 'Manager vẫn đang làm')
        self.beat(1)
        self.assertEqual(self.events('lane_stale'), [])                    # phòng có sự kiện trong 45' gần nhất
        self.beat(60, '--stale-minutes', '90')
        self.assertEqual(self.events('lane_stale'), [])                    # ngưỡng tuỳ chỉnh
        self.cli('lane', 'set', 'ATTEND', '--handle', 'term_qa', '--status', 'waiting')
        self.beat(300)
        self.assertEqual(self.events('lane_stale'), [])
        self.cli('room', 'new', 'DONE-ROOM', '--title', 'Xong')
        self.cli('lane', 'add', 'DONE-ROOM', '--role', 'qa', '--handle', 'term_done')
        self.cli('room', 'done', 'DONE-ROOM')
        self.beat(300)
        self.assertEqual(self.events('lane_stale'), [])                    # phòng không active thì thôi

    def test_thu_ky_silence_is_a_company_event(self):
        ps = self.ps
        ps.write_text('/bin/bash bin/wait-event.sh --timeout 14400 --types ask_opened\n'
                      '/bin/bash bin/wait-event.sh --room ATTEND\n')
        self.beat(0)
        self.beat(120)
        self.assertEqual(self.events('thu_ky_silent'), [])                 # watcher Thư ký còn chạy
        ps.write_text('/bin/bash bin/wait-event.sh --room ATTEND\n')       # chỉ còn watcher Manager
        self.beat(130)                                                     # bắt đầu đếm từ đây
        self.beat(150)
        self.assertEqual(self.events('thu_ky_silent'), [])
        self.beat(161)
        silent = self.events('thu_ky_silent')
        self.assertEqual(len(silent), 1)
        self.assertIsNone(silent[0]['room'])
        self.assertEqual(silent[0]['minutes'], 31)
        self.assertEqual(self.board()['events'][0]['type'], 'thu_ky_silent')
        self.beat(175)
        self.assertEqual(len(self.events('thu_ky_silent')), 1)             # không báo lặp trong cùng ngưỡng
        ps.write_text('/bin/bash bin/wait-event.sh --timeout 14400\n')    # Thư ký arm lại
        self.beat(200)
        self.beat(240)
        self.assertEqual(len(self.events('thu_ky_silent')), 1)

    def test_company_event_wakes_unfiltered_waiter_but_not_room_waiter(self):
        self.ps.write_text('')                                           # không còn watcher Thư ký
        self.beat(0)                                                       # bắt đầu đếm im lặng
        def waiter(*args):
            process = subprocess.Popen(['bash', str(WAITER), '--timeout', '1.5', '--interval', '0.02', *args],
                                       env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.addCleanup(lambda: process.poll() is None and process.kill())
            return process
        thu_ky, manager = waiter('--types', 'lane_stale,thu_ky_silent'), waiter('--room', 'ATTEND')
        time.sleep(0.2)   # cho hai watcher lấy mốc (giống WaitEventTests), không phải để giả giờ
        self.beat(40)
        output, _ = thu_ky.communicate(timeout=5)
        self.assertEqual((thu_ky.returncode, json.loads(output)['type']), (0, 'thu_ky_silent'))
        output, _ = manager.communicate(timeout=5)
        self.assertEqual((manager.returncode, output), (2, ''))            # room null không đánh thức Manager

    def test_invalid_arguments(self):
        for args in (['--now', 'không phải giờ'], ['--stale-minutes', '0'], ['--interval', '-1']):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, str(HEARTBEAT), '--once', *args], env=self.env,
                                        text=True, capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 2)
        result = subprocess.run([sys.executable, str(HEARTBEAT), '--now', self.start.isoformat()], env=self.env,
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2)                              # --now không kèm --once: không chạy vòng


class WaitEventTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.env = dict(os.environ, SPORTSHUB_CO=str(self.root))
        self.path = self.root / 'state/events.jsonl'
        self.path.parent.mkdir()
        self.path.write_text('')

    def start(self, *args):
        process = subprocess.Popen(['bash', str(WAITER), '--timeout', '1.5', '--interval', '0.02', *args],
                                   env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.communicate()
        self.addCleanup(cleanup)
        # Đợi tiến trình con thiết lập mốc trước khi thêm sự kiện mới.
        time.sleep(0.2)
        return process

    def append(self, room, kind, **fields):
        with self.path.open('a') as stream:
            stream.write(json.dumps({'room': room, 'type': kind, **fields}) + '\n')

    def test_filters_skip_old_and_nonmatching_events(self):
        self.append('ATTEND', 'ask_resolved', old=True)
        process = self.start('--room', 'ATTEND', '--types', 'ask_resolved,bug_changed')
        self.append('OTHER', 'ask_resolved')
        self.append('ATTEND', 'note')
        time.sleep(0.08)
        self.assertIsNone(process.poll())
        self.append('ATTEND', 'bug_changed', status='retest')
        output, error = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 0, error)
        lines = [json.loads(line) for line in output.splitlines()]
        self.assertEqual(lines, [{'room': 'ATTEND', 'type': 'bug_changed', 'status': 'retest'}])

    def test_timeout_with_only_nonmatching_lines(self):
        process = self.start('--room', 'ATTEND', '--timeout', '0.4')
        self.append('OTHER', 'note')
        output, error = process.communicate(timeout=2)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(output, '')
        self.assertTrue(error)

    def test_missing_file_then_multiple_events_without_filter(self):
        self.path.unlink()
        process = self.start()
        self.path.write_text('{"room":"AA","type":"note"}\n{"room":"BB","type":"ask_opened"}\n')
        output, error = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 0, error)
        self.assertEqual(len(output.splitlines()), 2)

    def test_partial_lines_and_rotation(self):
        self.append('AA', 'note', old=True)
        process = self.start('--types', 'ask_resolved')
        self.path.rename(self.path.with_suffix('.old'))
        self.path.write_text('bad json\n[]\n{"room":"AA","type":')
        time.sleep(0.08)
        self.assertIsNone(process.poll())
        with self.path.open('a') as stream:
            stream.write('"ask_resolved"}\n')
        output, error = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 0, error)
        self.assertEqual(json.loads(output)['type'], 'ask_resolved')

    def test_invalid_timing(self):
        for flag, value in [('--interval', '0'), ('--timeout', '-1'), ('--timeout', 'nan'), ('--interval', 'inf')]:
            result = subprocess.run(['bash', str(WAITER), flag, value], env=self.env, text=True,
                                    capture_output=True, timeout=2)
            self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
