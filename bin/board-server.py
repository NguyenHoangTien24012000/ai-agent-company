#!/usr/bin/env python3
"""Phục vụ board nội bộ và nhận câu trả lời qua localhost."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from company import Company, UserError


class BoardHandler(BaseHTTPRequestHandler):
    def send_bytes(self, status, payload, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, status, value):
        self.send_bytes(status, json.dumps(value, ensure_ascii=False).encode('utf-8'),
                        'application/json; charset=utf-8')

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/health':
            self.send_json(200, {'ok': True})
        elif path == '/api/state':
            try:
                self.send_json(200, self.server.company.snapshot())
            except (OSError, ValueError):
                self.send_json(500, {'ok': False, 'error': 'Không đọc được trạng thái.'})
        elif path in ('/', '/board.html', '/data/board.js'):
            relative = 'data/board.js' if path == '/data/board.js' else 'board.html'
            try:
                payload = (self.server.company.root / relative).read_bytes()
            except FileNotFoundError:
                self.send_json(404, {'ok': False, 'error': 'Không tìm thấy file.'})
                return
            content_type = 'application/javascript' if relative.endswith('.js') else 'text/html'
            self.send_bytes(200, payload, content_type + '; charset=utf-8')
        else:
            self.send_json(404, {'ok': False, 'error': 'Không tìm thấy đường dẫn.'})

    def do_POST(self):
        if urlsplit(self.path).path != '/api/answer':
            self.send_json(404, {'ok': False, 'error': 'Không tìm thấy đường dẫn.'})
            return
        port = self.server.server_address[1]
        origins = {f'http://127.0.0.1:{port}', f'http://localhost:{port}'}
        origin = self.headers.get_all('Origin', [])
        if (self.headers.get_all('X-Company', []) != ['1'] or
                self.headers.get_content_type() != 'application/json' or
                len(self.headers.get_all('Content-Type', [])) != 1 or
                (origin and (len(origin) != 1 or origin[0] not in origins))):
            self.send_json(403, {'ok': False, 'error': 'Header hoặc Origin không hợp lệ.'})
            return
        try:
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
                raise UserError('Cần đúng một Content-Length.')
            length = int(self.headers['Content-Length'])
            if not 0 < length <= 65536:
                raise UserError('Body phải có từ 1 đến 65536 byte.')
            self.connection.settimeout(5)
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            if not isinstance(body, dict):
                raise UserError('Body phải là JSON object.')
            ask = self.server.company.resolve_ask(body.get('askId'), body.get('choice'), body.get('note'), via='board')
        except (ValueError, UnicodeError, TimeoutError) as exc:
            self.send_json(400, {'ok': False, 'error': str(exc)})
            return
        except OSError:
            self.send_json(500, {'ok': False, 'error': 'Không ghi được trạng thái.'})
            return
        self.send_json(200, {'ok': True, 'ask': ask})


def make_server(port=8765, root=None):
    server = ThreadingHTTPServer(('127.0.0.1', port), BoardHandler)
    server.company = Company(root)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('Port phải nằm trong khoảng 0–65535.')
    try:
        server = make_server(args.port)
    except OSError as exc:
        parser.error(str(exc))
    print(f'Board: http://127.0.0.1:{server.server_address[1]}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
