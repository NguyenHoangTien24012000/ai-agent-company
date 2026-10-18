#!/usr/bin/env python3
"""Phục vụ board nội bộ và nhận câu trả lời qua localhost."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import threading
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from company import Company, UserError, effective_options

ORCA = os.environ.get('ORCA', '/Applications/Orca.app/Contents/Resources/bin/orca')


def answer_text(ask):
    label = next((option['label'] for option in effective_options(ask) if option['key'] == ask['choice']), '')
    text = f"Sếp trả lời {ask['id']} ({ask['title']}): {ask['choice']} — {label}"
    if (ask.get('note') or '').strip():
        text += ' — Ghi chú: ' + ask['note'].strip()
    return text


def forward_answer(company, ask, orca=None):
    """Gửi câu trả lời Sếp bấm trên board vào terminal Manager — việc Thư ký từng phải thức dậy làm tay.
    Không gửi được thì ghi sự kiện forward_failed để Thư ký xử lý; trả (ok, chi tiết)."""
    if ask.get('task'):
        # Câu của thẻ chưa mở phòng: không có Manager nào để gửi — không gọi Orca, không forward_failed;
        # ghi task_ask_answered để watcher của Thư ký thức dậy ghi câu trả lời vào thẻ / báo cáo nghiên cứu.
        company.task_ask_answered(ask)
        return True, 'task_ask_answered'
    handle = company.room(ask['room']).get('managerTerminal') or ''
    if not handle:
        # Handle rỗng: Orca gõ vào terminal KHÁC mà vẫn báo thành công — tuyệt đối không gọi.
        detail = 'phòng chưa có managerTerminal'
    else:
        try:
            result = subprocess.run([orca or ORCA, 'terminal', 'send', '--terminal', handle, '--text', answer_text(ask),
                                     '--enter', '--wait-submit', '15'], capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return True, result.stdout.strip()
            detail = (result.stderr or result.stdout).strip()[:500] or f'exit {result.returncode}'
        except (OSError, subprocess.TimeoutExpired) as exc:
            detail = str(exc)[:500]
    company.forward_failed(ask['id'], detail)
    return False, detail


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
        elif re.fullmatch(r'/retros/[A-Z0-9-]{2,24}\.md', path):
            # Bài rút kinh nghiệm của phòng đã xong (link ở tab Done); KEY lọc bằng regex nên không thoát được thư mục.
            try:
                payload = (self.server.company.state / 'retros' / path.rsplit('/', 1)[1]).read_bytes()
            except FileNotFoundError:
                self.send_json(404, {'ok': False, 'error': 'Không tìm thấy retro.'})
                return
            self.send_bytes(200, payload, 'text/plain; charset=utf-8')
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
        path = urlsplit(self.path).path
        if path not in ('/api/answer', '/api/task'):
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
            if path == '/api/task':
                result = {'ok': True, 'task': self.task_action(body)}
            else:
                ask = self.server.company.resolve_ask(body.get('askId'), body.get('choice'), body.get('note'),
                                                      via='board')
                result = {'ok': True, 'ask': ask}
        except (ValueError, UnicodeError, TimeoutError) as exc:
            self.send_json(400, {'ok': False, 'error': str(exc)})
            return
        except OSError:
            self.send_json(500, {'ok': False, 'error': 'Không ghi được trạng thái.'})
            return
        self.send_json(200, result)
        forward = getattr(self.server, 'forward', None)
        if path == '/api/answer' and forward:
            forward(result['ask'])

    def task_action(self, body):
        """Nút thẻ việc trên board. Ghi qua hàm của company.py (cùng khoá, cùng sổ sự kiện như CLI).
        Không có 'start': gắn thẻ với phòng là việc của open-room.sh, board không mở phòng."""
        company, action = self.server.company, body.get('action')
        if action == 'add':
            return company.add_task(body.get('title'), body.get('note'), body.get('column', 'backlog'))
        if action == 'move':
            return company.move_task(body.get('id'), body.get('column'))
        if action == 'edit':
            return company.edit_task(body.get('id'), body.get('title'), body.get('note'))
        if action == 'remove':
            return company.remove_task(body.get('id'))
        raise UserError('action phải là add, move, edit hoặc remove.')


def make_server(port=8765, root=None):
    server = ThreadingHTTPServer(('127.0.0.1', port), BoardHandler)
    server.company = Company(root)
    # Chạy ở luồng riêng: Orca chờ terminal nhận phím tới 15 giây, nút trên board không phải đợi theo.
    server.forward = lambda ask: threading.Thread(target=forward_answer, args=(server.company, ask), daemon=True).start()
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
