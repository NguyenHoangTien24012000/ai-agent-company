"""Kiểm thử HTTP với dữ liệu tạm; chạy thêm qua TCP nếu sandbox cho phép."""

from email.parser import BytesParser
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location('board_server', REPO / 'bin/board-server.py')
SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        # ORCA giả: server thật trong test KHÔNG BAO GIỜ được gõ vào terminal Orca thật.
        cls.env = dict(os.environ, SPORTSHUB_CO=str(cls.root), PYTHONDONTWRITEBYTECODE='1', ORCA='/usr/bin/false')
        (cls.root / 'board.html').write_text('<!doctype html><h1>Board thử</h1>')
        subprocess.run([sys.executable, str(REPO / 'bin/company.py'), 'room', 'new', 'ATTEND', '--title', 'Thử'],
                       env=cls.env, capture_output=True, check=True, timeout=10)
        cls.port = 8765
        cls.server = SimpleNamespace(company=SERVER.Company(cls.root), server_address=('127.0.0.1', cls.port))
        cls.forwarded = []
        cls.server.forward = cls.forwarded.append

    def ask(self):
        result = subprocess.run([sys.executable, str(REPO / 'bin/company.py'), 'ask', 'add', 'ATTEND',
                                 '--kind', 'duyet', '--gate', '1', '--title', 'Duyệt'],
                                env=self.env, text=True, capture_output=True, check=True, timeout=10)
        return result.stdout.strip()

    def request(self, method, path, body=None, headers=None):
        body = body.encode('utf-8') if isinstance(body, str) else body or b''
        headers = dict(headers or {})
        headers.setdefault('Content-Length', str(len(body)))
        raw = (f'{method} {path} HTTP/1.0\r\n' +
               ''.join(f'{key}: {value}\r\n' for key, value in headers.items()) + '\r\n').encode() + body

        class MemorySocket:
            def __init__(self):
                self.output = bytearray()

            def makefile(self, *args):
                return io.BytesIO(raw)

            def sendall(self, value):
                self.output.extend(value)

            def settimeout(self, timeout):
                pass

        class QuietHandler(SERVER.BoardHandler):
            def log_message(self, *args):
                pass

        connection = MemorySocket()
        QuietHandler(connection, ('127.0.0.1', 12345), self.server)
        head, payload = bytes(connection.output).split(b'\r\n\r\n', 1)
        status_line, raw_headers = head.split(b'\r\n', 1)
        return int(status_line.split()[1]), dict(BytesParser().parsebytes(raw_headers).items()), payload

    def answer(self, value, headers=None):
        return self.request('POST', '/api/answer', json.dumps(value), headers if headers is not None else
                            {'Content-Type': 'application/json', 'X-Company': '1'})

    def test_server_binds_only_loopback(self):
        with mock.patch.object(SERVER, 'ThreadingHTTPServer') as server_class:
            SERVER.make_server(8765, self.root)
            server_class.assert_called_once_with(('127.0.0.1', 8765), SERVER.BoardHandler)

    def test_get_routes_and_no_cache(self):
        for path in ('/', '/board.html', '/data/board.js', '/api/state', '/api/health'):
            status, headers, payload = self.request('GET', path)
            self.assertEqual(status, 200, payload)
            self.assertIn('no-store', headers['Cache-Control'])
        self.assertEqual(json.loads(self.request('GET', '/api/health')[2]), {'ok': True})
        state = json.loads(self.request('GET', '/api/state')[2])
        self.assertEqual(state['rooms'][0]['key'], 'ATTEND')
        self.assertEqual(self.request('GET', '/state/company.json')[0], 404)
        self.assertEqual(self.request('GET', '/../docs/CONTRACT.md')[0], 404)

    def test_files_route_serves_only_allowed_roots_and_types(self):
        if type(self).__name__ == 'LiveServerTests':
            self.skipTest('server chạy tiến trình riêng, không nhận biến môi trường vá trong test')
        # Board chạy http:// nên trình duyệt chặn link file:// âm thầm: Sếp bấm ảnh, báo cáo mà không ra gì (31/10).
        allowed = self.root / 'wt/.scratch/x'
        allowed.mkdir(parents=True)
        (allowed / 'a b.png').write_bytes(b'PNGDATA')
        (allowed / 'page.html').write_text('<h1>x</h1>')
        (allowed / '.env.local').write_text('SECRET=1')
        (allowed / 'secret.key').write_text('k')
        (self.root / 'wt/.git').mkdir()
        (self.root / 'wt/.git/config.html').write_text('x')
        outside = self.root.parent / (self.root.name + '-ngoai.png')
        outside.write_bytes(b'x')
        self.addCleanup(outside.unlink)
        (allowed / 'link.png').symlink_to(outside)
        with mock.patch.dict(os.environ, {'SPORTSHUB_FILE_ROOTS': str(self.root / 'wt')}):
            status, headers, payload = self.request('GET', f'/files{allowed}/a%20b.png')
            self.assertEqual((status, payload), (200, b'PNGDATA'))
            self.assertEqual(headers['Content-Type'], 'image/png')
            status, headers, _ = self.request('GET', f'/files{allowed}/page.html')
            self.assertEqual(status, 200)
            self.assertIn('text/html', headers['Content-Type'])
            for path in (f'{allowed}/.env.local', f'{allowed}/secret.key', f'{self.root}/wt/.git/config.html',
                         str(outside), f'{allowed}/link.png', f'{allowed}/../../../board.html', f'{allowed}/khong-co.png'):
                self.assertEqual(self.request('GET', '/files' + path)[0], 404, path)

    def test_files_html_and_svg_run_with_opaque_origin_on_every_way_of_opening(self):
        # Sandbox của iframe chỉ áp trong cửa sổ xem; "Mở tab riêng" hay chuột giữa thì trang chạy cùng nguồn với board,
        # script của nó gửi được câu trả lời giả tới terminal Manager. Header của server áp cho mọi đường mở.
        if type(self).__name__ == 'LiveServerTests':
            self.skipTest('server chạy tiến trình riêng, không nhận biến môi trường vá trong test')
        folder = self.root / 'wt-csp'
        folder.mkdir(exist_ok=True)
        (folder / 'p.html').write_text('<h1>x</h1>')
        (folder / 'a.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        (folder / 'b.png').write_bytes(b'x')
        link = folder / 'fake.pdf'
        if not link.is_symlink():
            link.symlink_to(folder / 'p.html')
        with mock.patch.dict(os.environ, {'SPORTSHUB_FILE_ROOTS': str(folder)}):
            for name in ('p.html', 'a.svg', 'fake.pdf'):
                headers = self.request('GET', f'/files{folder}/{name}')[1]
                self.assertIn('sandbox', headers.get('Content-Security-Policy', ''), name)
                self.assertNotIn('allow-same-origin', headers['Content-Security-Policy'])
            self.assertIsNone(self.request('GET', f'/files{folder}/b.png')[1].get('Content-Security-Policy'))

    def test_foreign_host_is_refused_so_dns_rebinding_reads_nothing(self):
        port = self.port
        for path in ('/api/state', '/', '/files/etc/hosts'):
            self.assertEqual(self.request('GET', path, headers={'Host': f'evil.example:{port}'})[0], 403, path)
        self.assertEqual(self.request('POST', '/api/answer', '{}', {'Host': 'evil.example', 'Content-Type': 'application/json', 'X-Company': '1'})[0], 403)
        for host in (f'127.0.0.1:{port}', f'localhost:{port}'):
            self.assertEqual(self.request('GET', '/api/health', headers={'Host': host})[0], 200)

    def test_board_page_cannot_be_framed_by_other_sites(self):
        self.assertEqual(self.request('GET', '/')[1].get('X-Frame-Options'), 'DENY')

    def test_files_block_is_case_insensitive_and_json_is_not_served(self):
        # Đĩa macOS không phân biệt hoa thường: .GIT cùng là .git. JSON có thể chứa thẻ đăng nhập của QA, không ai cần xem.
        if type(self).__name__ == 'LiveServerTests':
            self.skipTest('server chạy tiến trình riêng, không nhận biến môi trường vá trong test')
        folder = self.root / 'wt-case'
        (folder / '.GIT').mkdir(parents=True, exist_ok=True)
        (folder / '.GIT/x.md').write_text('x')
        (folder / '.ENV.md').write_text('x')
        (folder / 'ids.json').write_text('{}')
        with mock.patch.dict(os.environ, {'SPORTSHUB_FILE_ROOTS': str(folder)}):
            for name in ('.GIT/x.md', '.ENV.md', 'ids.json'):
                self.assertEqual(self.request('GET', f'/files{folder}/{name}')[0], 404, name)

    def test_state_carries_repo_root_for_links_of_tasks_without_room(self):
        if type(self).__name__ == 'LiveServerTests':
            self.skipTest('server chạy tiến trình riêng, không nhận biến môi trường vá trong test')
        with mock.patch.dict(os.environ, {'SPORTSHUB_REPO': '/tmp/repo-thu'}):
            self.assertEqual(json.loads(self.request('GET', '/api/state')[2])['repoRoot'], '/tmp/repo-thu')

    def test_csrf_rejections_leave_ask_open(self):
        ask_id = self.ask()
        for headers in [
                {'Content-Type': 'application/json'},
                {'Content-Type': 'application/json', 'X-Company': '0'},
                {'Content-Type': 'text/plain', 'X-Company': '1'},
                {'Content-Type': 'application/json', 'X-Company': '1', 'Origin': 'https://evil.test'},
                {'Content-Type': 'application/json', 'X-Company': '1', 'Origin': 'null'},
                {'Content-Type': 'application/json', 'X-Company': '1', 'Origin': 'http://localhost:1'}]:
            with self.subTest(headers=headers):
                status, _, payload = self.answer({'askId': ask_id, 'choice': 'ok'}, headers)
                self.assertEqual(status, 403, payload)
                self.assertFalse(json.loads(payload)['ok'])
        state = json.loads(self.request('GET', '/api/state')[2])
        self.assertEqual(next(ask for ask in state['rooms'][0]['asks'] if ask['id'] == ask_id)['status'], 'open')

    def test_valid_answer_records_board_source_and_gate(self):
        for origin in (None, f'http://127.0.0.1:{self.port}', f'http://localhost:{self.port}'):
            ask_id = self.ask()
            headers = {'Content-Type': 'application/json; charset=utf-8', 'X-Company': '1'}
            if origin:
                headers['Origin'] = origin
            status, _, payload = self.answer({'askId': ask_id, 'choice': 'ok', 'note': 'Đồng ý'}, headers)
            self.assertEqual(status, 200, payload)
            value = json.loads(payload)
            self.assertTrue(value['ok'])
            self.assertEqual(value['ask']['answeredVia'], 'board')
            state = json.loads(self.request('GET', '/api/state')[2])
            self.assertEqual(state['rooms'][0]['gates']['1']['askId'], ask_id)
            # Không lấy events[0]: luồng chuyển câu trả lời có thể ghi forward_failed chen lên trước.
            event = next(e for e in state['events'] if e['type'] == 'ask_resolved' and e['askId'] == ask_id)
            self.assertEqual((event['type'], event['via'], event['choice'], event['note']),
                             ('ask_resolved', 'board', 'ok', 'Đồng ý'))
            self.assertEqual(self.answer({'askId': ask_id, 'choice': 'ok'})[0], 400)

    def test_other_choice_needs_a_note_from_board(self):
        result = subprocess.run([sys.executable, str(REPO / 'bin/company.py'), 'ask', 'add', 'ATTEND', '--kind', 'quyet',
                                 '--title', 'Hỏi', '--option', 'a=A', '--option', 'b=B'], env=self.env, text=True, capture_output=True, check=True,
                                timeout=10)
        ask_id = result.stdout.strip()
        for note in (None, '', '  '):
            with self.subTest(note=note):
                status, _, payload = self.answer({'askId': ask_id, 'choice': 'khac', 'note': note})
                self.assertEqual(status, 400, payload)
        status, _, payload = self.answer({'askId': ask_id, 'choice': 'khac', 'note': 'Chốt sau trận'})
        self.assertEqual(status, 200, payload)

    def test_board_answer_is_handed_to_forwarder(self):
        # Sếp bấm trên board ⇒ server tự chuyển cho Manager, không chờ Thư ký thức dậy.
        ask_id = self.ask()
        self.forwarded.clear()
        status, _, payload = self.answer({'askId': ask_id, 'choice': 'ok', 'note': 'Đồng ý'})
        self.assertEqual(status, 200, payload)
        self.assertEqual([(ask['id'], ask['choice']) for ask in self.forwarded], [(ask_id, 'ok')])
        self.answer({'askId': ask_id, 'choice': 'ok'})                    # trả lời lại bị từ chối ⇒ không chuyển
        self.assertEqual(len(self.forwarded), 1)

    def fake_orca(self, code=0):
        log = self.root / 'orca.log'
        script = self.root / f'orca-{code}.sh'
        script.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > {log}\necho input_accepted\nexit {code}\n')
        script.chmod(0o755)
        return str(script), log

    def resolved_ask(self, terminal):
        path = self.root / 'state/rooms/ATTEND.json'
        room = json.loads(path.read_text())
        room['managerTerminal'] = terminal or None
        path.write_text(json.dumps(room))
        result = subprocess.run([sys.executable, str(REPO / 'bin/company.py'), 'ask', 'add', 'ATTEND', '--kind', 'quyet',
                                 '--title', 'Ai chốt?', '--option', 'a=Đội trưởng', '--option', 'b=Ai cũng được'],
                                env=self.env, text=True, capture_output=True, check=True, timeout=10)
        return self.server.company.resolve_ask(result.stdout.strip(), 'khac', 'Phó đội cũng chốt', via='board')

    def events(self):
        return [json.loads(line) for line in (self.root / 'state/events.jsonl').read_text().splitlines()]

    def test_forward_sends_exact_answer_to_manager_terminal(self):
        orca, log = self.fake_orca()
        ask = self.resolved_ask('term_manager')
        ok, _ = SERVER.forward_answer(self.server.company, ask, orca)
        self.assertTrue(ok)
        args = log.read_text().splitlines()
        self.assertEqual(args[:4], ['terminal', 'send', '--terminal', 'term_manager'])
        self.assertEqual(args[5], f"Sếp trả lời {ask['id']} (Ai chốt?): khac — Khác — tự viết — Ghi chú: Phó đội cũng chốt")
        self.assertIn('--enter', args)
        self.assertNotEqual(self.events()[-1]['type'], 'forward_failed')

    def test_forward_failure_is_recorded_for_thu_ky(self):
        orca, _ = self.fake_orca(code=3)
        ask = self.resolved_ask('term_manager')
        self.assertFalse(SERVER.forward_answer(self.server.company, ask, orca)[0])
        event = self.events()[-1]
        self.assertEqual((event['type'], event['askId']), ('forward_failed', ask['id']))
        # Handle rỗng: Orca sẽ gõ nhầm vào terminal khác mà vẫn báo thành công ⇒ không được gọi Orca.
        orca, log = self.fake_orca()
        log.unlink(missing_ok=True)
        ask = self.resolved_ask('')
        self.assertFalse(SERVER.forward_answer(self.server.company, ask, orca)[0])
        self.assertFalse(log.exists())
        self.assertEqual(self.events()[-1]['type'], 'forward_failed')
        self.assertFalse(SERVER.forward_answer(self.server.company, ask, str(self.root / 'khong-co-orca'))[0])

    def task_ask(self):
        cli = [sys.executable, str(REPO / 'bin/company.py')]
        task = json.loads(subprocess.run(cli + ['task', 'add', '--title', 'Phòng truyền thống', '--json'], env=self.env,
                                         text=True, capture_output=True, check=True, timeout=10).stdout)
        return subprocess.run(cli + ['ask', 'add', '--task', task['id'], '--kind', 'quyet', '--title', 'Ai ghi kỷ niệm?',
                                     '--option', 'a=Đội trưởng', '--option', 'b=Mọi người'],
                              env=self.env, text=True, capture_output=True, check=True, timeout=10).stdout.strip()

    def test_task_question_answered_on_board_wakes_thu_ky_without_orca(self):
        # Câu của thẻ chưa có phòng: không có Manager ⇒ không gọi Orca, không forward_failed; ghi task_ask_answered.
        ask_id = self.task_ask()
        state = json.loads(self.request('GET', '/api/state')[2])
        self.assertIn(ask_id, [item['id'] for item in state['myQueue']])
        status, _, payload = self.answer({'askId': ask_id, 'choice': 'khac', 'note': ''})
        self.assertEqual(status, 400, payload)
        status, _, payload = self.answer({'askId': ask_id, 'choice': 'khac', 'note': 'Thủ quỹ ghi'})
        self.assertEqual(status, 200, payload)
        ask = json.loads(payload)['ask']
        self.assertEqual((ask['task'], ask['answeredVia'], ask['status']), (ask_id.split('-')[0], 'board', 'resolved'))
        orca, log = self.fake_orca()
        log.unlink(missing_ok=True)
        self.assertTrue(SERVER.forward_answer(self.server.company, ask, orca)[0])
        self.assertFalse(log.exists())
        event = self.events()[-1]
        self.assertEqual((event['type'], event['room'], event['task'], event['askId'], event['choice'], event['note']),
                         ('task_ask_answered', None, ask['task'], ask_id, 'khac', 'Thủ quỹ ghi'))
        self.assertNotIn(ask_id, [e.get('askId') for e in self.events() if e['type'] == 'forward_failed'])

    def test_invalid_body_and_choice(self):
        ask_id = self.ask()
        for value in [[], {}, {'askId': ask_id}, {'askId': ask_id, 'choice': []},
                      {'askId': [], 'choice': 'ok'}, {'askId': ask_id, 'choice': 'missing'},
                      {'askId': ask_id, 'choice': 'ok', 'note': {}}, {'askId': 'MISSING-a1', 'choice': 'ok'}]:
            with self.subTest(value=value):
                status, _, payload = self.answer(value)
                self.assertEqual(status, 400, payload)
                self.assertFalse(json.loads(payload)['ok'])
        self.assertEqual(self.request('POST', '/api/answer', '{bad',
                                     {'Content-Type': 'application/json', 'X-Company': '1'})[0], 400)
        self.assertEqual(self.request('POST', '/missing', '{}')[0], 404)

    def task(self, value, headers=None):
        status, _, payload = self.request('POST', '/api/task', json.dumps(value), headers if headers is not None else
                                          {'Content-Type': 'application/json', 'X-Company': '1'})
        return status, json.loads(payload)

    def test_task_buttons_add_move_edit_remove(self):
        status, value = self.task({'action': 'add', 'title': 'Giao lưu đội', 'note': 'Hai đội', 'column': 'todo'})
        self.assertEqual(status, 200, value)
        task = value['task']
        self.assertEqual((task['title'], task['note'], task['column'], task['room']), ('Giao lưu đội', 'Hai đội', 'todo', None))
        event = self.events()[-1]
        self.assertEqual((event['type'], event['taskId'], event['room']), ('task_added', task['id'], None))
        status, value = self.task({'action': 'move', 'id': task['id'], 'column': 'backlog'})
        self.assertEqual((status, value['task']['column']), (200, 'backlog'))
        status, value = self.task({'action': 'edit', 'id': task['id'], 'title': 'Giao lưu'})
        self.assertEqual((status, value['task']['title']), (200, 'Giao lưu'))
        state = json.loads(self.request('GET', '/api/state')[2])
        self.assertIn(value['task'], state['tasks'])
        status, value = self.task({'action': 'remove', 'id': task['id']})
        self.assertEqual(status, 200, value)
        self.assertEqual(self.events()[-1]['type'], 'task_removed')
        state = json.loads(self.request('GET', '/api/state')[2])
        self.assertNotIn(task['id'], [item['id'] for item in state['tasks']])
        # Thêm thẻ không có column ⇒ Backlog.
        status, value = self.task({'action': 'add', 'title': 'Ý tưởng'})
        self.assertEqual((status, value['task']['column']), (200, 'backlog'))

    def test_task_endpoint_rejects_csrf_and_bad_bodies(self):
        before = self.events()
        for headers in [{'Content-Type': 'application/json'},
                        {'Content-Type': 'text/plain', 'X-Company': '1'},
                        {'Content-Type': 'application/json', 'X-Company': '1', 'Origin': 'https://evil.test'}]:
            with self.subTest(headers=headers):
                status, value = self.task({'action': 'add', 'title': 'Lừa'}, headers)
                self.assertEqual((status, value['ok']), (403, False))
        for body in [[], {}, {'action': 'start', 'id': 'T1', 'room': 'ATTEND'}, {'action': 'add'},
                     {'action': 'add', 'title': ' '}, {'action': 'add', 'title': 'X', 'column': 'doing'},
                     {'action': 'add', 'title': 'X', 'note': {}}, {'action': 'move', 'id': 'T999', 'column': 'todo'},
                     {'action': 'move', 'id': [], 'column': 'todo'}, {'action': 'remove', 'id': '../x'}]:
            with self.subTest(body=body):
                status, value = self.task(body)
                self.assertEqual((status, value['ok']), (400, False), value)
        self.assertEqual(before, self.events())

    def test_retro_is_served_as_text(self):
        (self.root / 'state/retros').mkdir(parents=True, exist_ok=True)
        (self.root / 'state/retros/ATTEND.md').write_text('# Retro ATTEND\n<script>x</script>', encoding='utf-8')
        status, headers, payload = self.request('GET', '/retros/ATTEND.md')
        self.assertEqual(status, 200, payload)
        self.assertTrue(headers['Content-Type'].startswith('text/plain'))
        self.assertEqual(payload.decode('utf-8'), '# Retro ATTEND\n<script>x</script>')
        for path in ('/retros/MISSING.md', '/retros/attend.md', '/retros/../rooms/ATTEND.json', '/retros/ATTEND.json'):
            with self.subTest(path=path):
                self.assertEqual(self.request('GET', path)[0], 404)
        self.assertIn('ATTEND', json.loads(self.request('GET', '/api/state')[2])['retros'])


class LiveServerTests(ServerTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.process = subprocess.Popen([sys.executable, str(REPO / 'bin/board-server.py'), '--port', '0'],
                                       env=cls.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def cleanup():
            cls.process.terminate()
            try:
                cls.process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                cls.process.kill()
                cls.process.communicate()
        cls.addClassCleanup(cleanup)
        with selectors.DefaultSelector() as selector:
            selector.register(cls.process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout=5):
                raise RuntimeError('Server không thông báo địa chỉ sau 5 giây.')
            line = cls.process.stdout.readline().strip()
        if not line.startswith('Board: http://127.0.0.1:'):
            error = cls.process.stderr.read()
            if 'Operation not permitted' in error or 'Permission denied' in error:
                raise unittest.SkipTest('Sandbox chặn bind TCP localhost; các test handler vẫn chạy đầy đủ.')
            raise RuntimeError('Server không khởi động: ' + error)
        cls.port = int(line.rsplit(':', 1)[1])

    def test_board_answer_is_handed_to_forwarder(self):
        # Server thật dùng ORCA=/usr/bin/false ⇒ chuyển thất bại ⇒ phải để lại forward_failed cho Thư ký.
        path = self.root / 'state/rooms/ATTEND.json'
        room = json.loads(path.read_text())
        room['managerTerminal'] = 'term_test'
        path.write_text(json.dumps(room))
        ask_id = self.ask()
        self.assertEqual(self.answer({'askId': ask_id, 'choice': 'ok'})[0], 200)
        for _ in range(50):
            failed = [e for e in self.events() if e['type'] == 'forward_failed' and e['askId'] == ask_id]
            if failed:
                break
            time.sleep(0.1)
        self.assertTrue(failed)

    def test_task_question_answered_on_board_wakes_thu_ky_without_orca(self):
        # Server thật (ORCA=/usr/bin/false): câu của thẻ vẫn phải ra task_ask_answered, không forward_failed.
        ask_id = self.task_ask()
        self.assertEqual(self.answer({'askId': ask_id, 'choice': 'a'})[0], 200)
        for _ in range(50):
            answered = [e for e in self.events() if e['type'] == 'task_ask_answered' and e['askId'] == ask_id]
            if answered:
                break
            time.sleep(0.1)
        self.assertEqual(len(answered), 1)
        self.assertNotIn(ask_id, [e.get('askId') for e in self.events() if e['type'] == 'forward_failed'])

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()


if __name__ == '__main__':
    unittest.main()
