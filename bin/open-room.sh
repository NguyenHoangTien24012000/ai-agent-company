#!/usr/bin/env bash
# Mở một phòng: worktree Orca + nhánh phong/<key> + .env.local + terminal Manager (Claude Opus) + ghi board.
#
#   open-room.sh KEY "Tiêu đề" ["ý tưởng ban đầu"] [--dry-run]
#
# --dry-run: in toàn bộ chuỗi lệnh, KHÔNG chạy gì (kể cả kiểm tra), exit 0.
# Biến môi trường (test dùng để thay công cụ thật):
#   SPORTSHUB_CO    gốc ~/sportshub-company     SPORTSHUB_REPO  repo SportsHub
#   ORCA            đường dẫn Orca CLI          COMPANY_PY      đường dẫn company.py
#   MANAGER_WAIT    số giây chờ Manager hiện lên màn hình (mặc định 60)
# Exit: 0 xong · 2 sai tham số / điều kiện trước · 3 Orca/git lỗi · 4 Manager không xác nhận được.
set -euo pipefail

CO="${SPORTSHUB_CO:-$HOME/sportshub-company}"
REPO="${SPORTSHUB_REPO:-/Users/tien/Claude/sportshub}"
ORCA="${ORCA:-/Applications/Orca.app/Contents/Resources/bin/orca}"
COMPANY_PY="${COMPANY_PY:-$CO/bin/company.py}"
MANAGER_WAIT="${MANAGER_WAIT:-60}"
BASE_BRANCH=main

usage() { echo "Dùng: open-room.sh KEY \"Tiêu đề\" [\"ý tưởng ban đầu\"] [--dry-run]" >&2; exit 2; }
die() { echo "open-room: $1" >&2; exit "${2:-2}"; }

DRY_RUN=0
POS=()
for a in "$@"; do
  case "$a" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage ;;
    --*) die "cờ lạ: $a" ;;
    *) POS+=("$a") ;;
  esac
done
[ "${#POS[@]}" -ge 2 ] && [ "${#POS[@]}" -le 3 ] || usage
KEY="${POS[0]}"
TITLE="${POS[1]}"
IDEA="${POS[2]:-}"

# KEY theo CONTRACT: chữ hoa, số, gạch ngang, 2–24 ký tự.
[[ "$KEY" =~ ^[A-Z0-9-]{2,24}$ ]] || die "KEY '$KEY' sai: chỉ chữ hoa, số, gạch ngang, 2–24 ký tự"
[ -n "${TITLE// /}" ] || die "tiêu đề rỗng"

KEY_LOWER="$(printf '%s' "$KEY" | tr '[:upper:]' '[:lower:]')"
BRANCH="phong/$KEY_LOWER"
WT_EXPECTED="/Users/tien/orca/workspaces/sportshub/$KEY_LOWER"

# Bọc chuỗi trong nháy đơn cho shell (an toàn cả với tiếng Việt, ký tự đặc biệt).
sq() { local s=${1//\'/\'\\\'\'}; printf "'%s'" "$s"; }

# Lệnh khởi động Manager, gõ vào shell của terminal mới.
PROMPT="/phong-manager $KEY $TITLE"
[ -n "$IDEA" ] && PROMPT="$PROMPT — Ý tưởng ban đầu: $IDEA"
MANAGER_CMD="claude --model opus --effort high --permission-mode bypassPermissions $(sq "$PROMPT")"

if [ "$DRY_RUN" = 1 ]; then
  W="<WORKTREE>"; H="<HANDLE>"
  cat <<EOF
# open-room DRY-RUN — không chạy gì. KEY=$KEY  nhánh=$BRANCH  worktree dự kiến=$WT_EXPECTED
# 1. Kiểm tra trước (dừng nếu một cái không đạt)
python3 $(sq "$COMPANY_PY") room show $KEY              # PHẢI lỗi (phòng chưa tồn tại)
git -C $(sq "$REPO") rev-parse --verify --quiet refs/heads/$BRANCH   # PHẢI rỗng (nhánh chưa có)
git -C $(sq "$REPO") rev-parse --verify refs/heads/$BASE_BRANCH
test ! -e $(sq "$WT_EXPECTED")
# 2. Tạo worktree Orca từ $BASE_BRANCH (đọc result.worktree.path từ JSON)
$ORCA worktree create --repo $(sq "path:$REPO") --name $KEY_LOWER --no-parent --base-branch $BASE_BRANCH --setup skip --comment $(sq "Phòng $KEY: $TITLE") --json
# 3. Đặt tên nhánh phong/<key> (Orca đặt nhánh theo --name)
git -C $W branch --show-current        # nếu khác $BRANCH:
git -C $W branch -m <nhánh-Orca-tạo> $BRANCH     # (HEAD rời ⇒ git -C $W switch -c $BRANCH)
# 4. Chép .env.local (chỉ khi có, không ghi đè)
cp -n $(sq "$REPO/server/.env.local") $W/server/.env.local
cp -n $(sq "$REPO/web/.env.local") $W/web/.env.local
# 5. Ghi phòng lên board TRƯỚC khi Manager chạy (Manager đọc room show ngay khi khởi động)
python3 $(sq "$COMPANY_PY") room new $KEY --title $(sq "$TITLE") --branch $BRANCH --worktree $W
# 6. Mở terminal Manager (Claude Opus) trong worktree; handle lấy từ JSON hoặc terminal list
$ORCA terminal list --json             # chụp danh sách handle trước
$ORCA terminal create --worktree path:$W --title $(sq "Manager $KEY") --command $(sq "$MANAGER_CMD") --json
$ORCA terminal list --json             # handle mới thuộc worktreePath=$W
# 7. Gắn handle vào phòng (BẮT BUỘC handle khác rỗng)
python3 $(sq "$COMPANY_PY") room set $KEY --manager-terminal $H
# 8. Đọc màn hình xác nhận Manager đã chạy (chờ tối đa ${MANAGER_WAIT}s)
$ORCA terminal read --terminal $H --screen --limit 40
EOF
  exit 0
fi

# ---------- Chạy thật ----------
command -v python3 >/dev/null || die "thiếu python3"
[ -x "$ORCA" ] || die "không thấy Orca CLI: $ORCA"
[ -f "$COMPANY_PY" ] || die "không thấy company.py: $COMPANY_PY"
[ -d "$REPO/.git" ] || [ -f "$REPO/.git" ] || die "không thấy repo: $REPO"

if python3 "$COMPANY_PY" room show "$KEY" >/dev/null 2>&1; then
  die "phòng $KEY đã có (company.py room show $KEY)"
fi
git -C "$REPO" rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null && die "nhánh $BRANCH đã có trong $REPO"
git -C "$REPO" rev-parse --verify --quiet "refs/heads/$BASE_BRANCH" >/dev/null || die "không có nhánh $BASE_BRANCH trong $REPO"
[ ! -e "$WT_EXPECTED" ] || die "thư mục $WT_EXPECTED đã có"

# Đọc một trường từ JSON Orca ở stdin. $1 = danh sách đường dẫn thử lần lượt, cách nhau bởi dấu phẩy.
json_get() {
  python3 -c '
import json, sys
paths = sys.argv[1].split(",")
try:
    data = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
for p in paths:
    cur = data
    for part in p.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
    if isinstance(cur, str) and cur.strip():
        print(cur.strip()); break
' "$1"
}

# Danh sách handle terminal (có lọc theo worktreePath nếu truyền $2), từ JSON `terminal list` ở $1.
handles_of() {
  python3 -c '
import json, sys
try:
    data = json.loads(sys.argv[1])
except ValueError:
    sys.exit(0)
res = data.get("result", data) if isinstance(data, dict) else data
items = res.get("terminals", []) if isinstance(res, dict) else res
want = sys.argv[2] if len(sys.argv) > 2 else ""
for t in items or []:
    if isinstance(t, dict) and t.get("handle") and (not want or t.get("worktreePath") == want):
        print(t["handle"])
' "$@"
}

echo "▶ Tạo worktree Orca cho $KEY từ ${BASE_BRANCH}…"
# Không giấu stderr của Orca: lỗi phải hiện ra.
CREATE_OUT="$("$ORCA" worktree create --repo "path:$REPO" --name "$KEY_LOWER" --no-parent \
  --base-branch "$BASE_BRANCH" --setup skip --comment "Phòng $KEY: $TITLE" --json)" \
  || die "orca worktree create lỗi:
$CREATE_OUT" 3
WT="$(printf '%s' "$CREATE_OUT" | json_get "result.worktree.path,result.path")"
[ -n "$WT" ] && [ -d "$WT" ] || die "không đọc được đường dẫn worktree từ Orca:
$CREATE_OUT" 3
CLEANUP="$ORCA worktree rm --worktree $(sq "path:$WT") --json"
[ "$WT" = "$WT_EXPECTED" ] || echo "⚠️  worktree ở $WT (CONTRACT dự kiến $WT_EXPECTED) — vẫn ghi đường thật."

CUR="$(git -C "$WT" branch --show-current)"
if [ "$CUR" != "$BRANCH" ]; then
  if [ -n "$CUR" ]; then
    git -C "$WT" branch -m "$CUR" "$BRANCH" || die "đổi tên nhánh $CUR → $BRANCH lỗi. Dọn: $CLEANUP" 3
  else
    git -C "$WT" switch -c "$BRANCH" || die "tạo nhánh $BRANCH lỗi. Dọn: $CLEANUP" 3
  fi
fi
echo "✓ worktree $WT trên nhánh $BRANCH"

for f in server/.env.local web/.env.local; do
  if [ -f "$REPO/$f" ]; then
    mkdir -p "$(dirname "$WT/$f")"
    cp -n "$REPO/$f" "$WT/$f"
    echo "✓ chép $f"
  else
    echo "· không có $REPO/$f, bỏ qua"
  fi
done

python3 "$COMPANY_PY" room new "$KEY" --title "$TITLE" --branch "$BRANCH" --worktree "$WT" \
  || die "company.py room new lỗi. Worktree đã tạo; dọn: $CLEANUP" 3

echo "▶ Mở terminal Manager (Claude Opus)…"
BEFORE="$(handles_of "$("$ORCA" terminal list --json)")"
TERM_OUT="$("$ORCA" terminal create --worktree "path:$WT" --title "Manager $KEY" \
  --command "$MANAGER_CMD" --json)" || die "orca terminal create lỗi:
$TERM_OUT" 3
H="$(printf '%s' "$TERM_OUT" | json_get "result.terminal.handle,result.handle,result.terminalHandle")"
if [ -z "$H" ]; then
  # create không trả handle dùng được ⇒ lấy handle mới thuộc worktree này từ terminal list.
  for _ in 1 2 3 4 5; do
    for cand in $(handles_of "$("$ORCA" terminal list --json)" "$WT"); do
      printf '%s\n' "$BEFORE" | grep -qxF "$cand" || { H="$cand"; break; }
    done
    [ -n "$H" ] && break
    sleep 1
  done
fi
[ -n "$H" ] || die "không lấy được handle terminal Manager. Phòng đã ghi (managerTerminal=null); xem 'orca terminal list --json' rồi: python3 $COMPANY_PY room set $KEY --manager-terminal <handle>" 3

python3 "$COMPANY_PY" room set "$KEY" --manager-terminal "$H" || die "company.py room set lỗi (handle $H)" 3
echo "✓ Manager terminal $H"

echo "▶ Chờ Manager hiện lên (tối đa ${MANAGER_WAIT}s)…"
SCREEN=""; OK=0; waited=0
while [ "$waited" -le "$MANAGER_WAIT" ]; do
  SCREEN="$("$ORCA" terminal read --terminal "$H" --screen --limit 40 || true)"
  if printf '%s' "$SCREEN" | grep -qE 'phong-manager|Launching skill|Claude Code|bypass permissions'; then OK=1; break; fi
  sleep 3; waited=$((waited + 3))
done
printf '%s\n' "$SCREEN" | tail -n 15
if [ "$OK" = 1 ]; then
  echo "✓ Phòng $KEY đã mở: $WT · $BRANCH · Manager $H"
else
  die "chưa thấy Manager chạy trên màn hình $H sau ${MANAGER_WAIT}s — mở Orca xem tay." 4
fi
