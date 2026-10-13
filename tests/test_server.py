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
        cls.env = dict(os.environ, SPORTSHUB_CO=str(cls.root), PYTHONDONTWRITEBYTECODE='1')
        (cls.root / 'board.html').write_text('<!doctype html><h1>Board thử</h1>')
        subprocess.run([sys.executable, str(REPO / 'bin/company.py'), 'room', 'new', 'ATTEND', '--title', 'Thử'],
                       env=cls.env, capture_output=True, check=True, timeout=10)
        cls.port = 8765
        cls.server = SimpleNamespace(company=SERVER.Company(cls.root), server_address=('127.0.0.1', cls.port))

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
            event = state['events'][0]
            self.assertEqual((event['type'], event['via'], event['choice'], event['note']),
                             ('ask_resolved', 'board', 'ok', 'Đồng ý'))
            self.assertEqual(self.answer({'askId': ask_id, 'choice': 'ok'})[0], 400)

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
