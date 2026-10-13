#!/usr/bin/env bash
# Bật server board (nếu chưa chạy) rồi mở board trên trình duyệt. Sếp chạy lệnh này.
# Server chạy nền, ghi log vào state/board-server.log; tắt bằng: pkill -f board-server.py
# Kèm nhịp kiểm bin/heartbeat.py chạy nền (state/heartbeat.pid, state/heartbeat.log).
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

# Nhịp kiểm (bin/heartbeat.py, không dùng AI): báo lane đứng yên và Thư ký ngủ quên bằng sự kiện.
# Chạy nền một bản duy nhất; pid file + kiểm đúng tiến trình (pid cũ có thể đã bị tiến trình khác dùng lại).
# Tắt: kill "$(cat state/heartbeat.pid)"
mkdir -p "$ROOT/state"   # server có thể đã chạy sẵn, nên không dựa vào mkdir ở trên
PIDFILE="$ROOT/state/heartbeat.pid"
HB_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
if [ -n "$HB_PID" ] && ps -p "$HB_PID" -o command= 2>/dev/null | grep -q 'heartbeat\.py'; then
  echo "Nhịp kiểm: đang chạy (pid $HB_PID)"
else
  nohup python3 "$ROOT/bin/heartbeat.py" >>"$ROOT/state/heartbeat.log" 2>&1 &
  echo $! > "$PIDFILE"
  echo "Nhịp kiểm: đã bật (pid $!, log state/heartbeat.log)"
fi
echo "Board: http://127.0.0.1:$PORT"
open "http://127.0.0.1:$PORT"
