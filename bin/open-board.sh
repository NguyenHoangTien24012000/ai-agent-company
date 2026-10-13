#!/usr/bin/env bash
# Bật server board (nếu chưa chạy) rồi mở board trên trình duyệt. Sếp chạy lệnh này.
# Server chạy nền, ghi log vào state/board-server.log; tắt bằng: pkill -f board-server.py
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-8765}"
if ! curl -fs "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
  mkdir -p "$ROOT/state"
  nohup python3 "$ROOT/bin/board-server.py" --port "$PORT" >>"$ROOT/state/board-server.log" 2>&1 &
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    curl -fs "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1 && break
    sleep 0.3
  done
fi
curl -fs "http://127.0.0.1:$PORT/api/health" >/dev/null || { echo "Server không lên — xem $ROOT/state/board-server.log" >&2; exit 1; }
echo "Board: http://127.0.0.1:$PORT"
open "http://127.0.0.1:$PORT"
