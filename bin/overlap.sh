#!/usr/bin/env bash
# So file đổi giữa các phòng đang active và báo đụng file / xung đột gộp thật.
#
#   overlap.sh [--dry-run]
#
# Với mỗi cặp phòng active (có nhánh):
#   - file đổi của phòng = git diff --name-only main...<nhánh>
#   - giao hai tập khác rỗng ⇒ đụng file; git merge-tree --write-tree <A> <B> exit 1 ⇒ xung đột thật
#   - ghi cho CẢ HAI phòng: company.py overlap KEY --with OTHER --files a,b [--conflict]
#   - cặp hết đụng mà board còn ghi ⇒ company.py overlap KEY --with OTHER --clear
# Chỉ ghi khi khác điều board đang có (tránh rác sự kiện mỗi lần Thư ký thức).
# --dry-run: in kết quả + lệnh sẽ chạy, KHÔNG gọi company.py để ghi (chỉ đọc snapshot).
# Biến môi trường: SPORTSHUB_CO, SPORTSHUB_REPO, COMPANY_PY (như open-room.sh).
set -euo pipefail

CO="${SPORTSHUB_CO:-$HOME/sportshub-company}"
REPO="${SPORTSHUB_REPO:-/Users/tien/Claude/sportshub}"
COMPANY_PY="${COMPANY_PY:-$CO/bin/company.py}"

DRY_RUN=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY_RUN=1 ;;
    *) echo "Dùng: overlap.sh [--dry-run]" >&2; exit 2 ;;
  esac
done
[ -f "$COMPANY_PY" ] || { echo "overlap: không thấy company.py: $COMPANY_PY" >&2; exit 2; }

SNAPSHOT="$(python3 "$COMPANY_PY" snapshot)"

python3 - "$REPO" "$COMPANY_PY" "$DRY_RUN" "$SNAPSHOT" <<'PY'
import itertools, json, shlex, subprocess, sys

repo, company_py, dry_run, snapshot = sys.argv[1], sys.argv[2], sys.argv[3] == "1", sys.argv[4]
BASE = "main"
rooms = [r for r in json.loads(snapshot).get("rooms", [])
         if r.get("status") == "active" and r.get("branch")]


def git(*args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def changed_files(branch):
    res = git("diff", "--name-only", f"{BASE}...{branch}")
    if res.returncode:
        print(f"⚠️  bỏ qua {branch}: {res.stderr.strip()}", file=sys.stderr)
        return None
    return {line for line in res.stdout.splitlines() if line}


def real_conflict(a, b):
    # exit 0 = gộp sạch, 1 = có xung đột, khác = lỗi git.
    res = git("merge-tree", "--write-tree", "--name-only", "--no-messages", a, b)
    if res.returncode not in (0, 1):
        print(f"⚠️  merge-tree {a} {b} lỗi: {res.stderr.strip()}", file=sys.stderr)
        return False, []
    lines = res.stdout.splitlines()[1:]  # dòng đầu là OID của tree
    return res.returncode == 1, [l for l in lines if l]


def recorded(room, other):
    for o in room.get("overlaps") or []:
        if o.get("with") == other:
            return sorted(o.get("files") or []), bool(o.get("conflict"))
    return None


files = {r["key"]: changed_files(r["branch"]) for r in rooms}
by_key = {r["key"]: r for r in rooms}
commands, lines = [], []

for a, b in itertools.combinations(sorted(by_key), 2):
    fa, fb = files[a], files[b]
    if fa is None or fb is None:
        continue
    common = sorted(fa & fb)
    if common:
        conflict, conflict_files = real_conflict(by_key[a]["branch"], by_key[b]["branch"])
        tag = "🔴 XUNG ĐỘT THẬT" if conflict else "⚠️ đụng file, gộp sạch"
        lines.append(f"{tag}: {a} ↔ {b}: {', '.join(common)}"
                     + (f" (xung đột ở: {', '.join(conflict_files)})" if conflict else ""))
        for me, other in ((a, b), (b, a)):
            if recorded(by_key[me], other) != (common, conflict):
                cmd = ["overlap", me, "--with", other, "--files", ",".join(common)]
                commands.append(cmd + (["--conflict"] if conflict else []))
    else:
        for me, other in ((a, b), (b, a)):
            if recorded(by_key[me], other) is not None:
                lines.append(f"✓ hết đụng: {me} ↔ {other} (xoá dấu trên board)")
                commands.append(["overlap", me, "--with", other, "--clear"])

# Dấu cũ trỏ tới phòng không còn active ⇒ xoá.
for key, room in by_key.items():
    for o in room.get("overlaps") or []:
        if o.get("with") not in by_key:
            lines.append(f"✓ {key}: phòng {o.get('with')} không còn active (xoá dấu)")
            commands.append(["overlap", key, "--with", o.get("with"), "--clear"])

print(f"overlap: {len(rooms)} phòng active — "
      + (", ".join(f"{k}({len(v) if v is not None else '?'} file)" for k, v in sorted(files.items())) or "không có"))
for line in lines:
    print(line)
if not lines:
    print("không phòng nào đụng file nhau")

for cmd in commands:
    full = ["python3", company_py, *cmd]
    if dry_run:
        print("[dry-run] " + shlex.join(full))
    else:
        res = subprocess.run(full)
        if res.returncode:
            print("❌ lỗi: " + shlex.join(full), file=sys.stderr)
            sys.exit(res.returncode)
if not commands:
    print("board đã khớp, không ghi gì")
PY
