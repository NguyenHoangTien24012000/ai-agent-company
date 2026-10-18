#!/usr/bin/env bash
# Test open-room.sh và overlap.sh bằng Orca giả + company.py giả + repo git tạm. Không chạm Orca/state thật.
#   bash tests/test_open_room.sh
set -uo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok()   { PASS=$((PASS + 1)); echo "  ✓ $1"; }
bad()  { FAIL=$((FAIL + 1)); echo "  ✗ $1"; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

# ---------- dựng đồ giả ----------
REPO="$TMP/repo"
git init -q -b main "$REPO"
git -C "$REPO" config user.email t@t; git -C "$REPO" config user.name t
mkdir -p "$REPO/server" "$REPO/web"
echo base > "$REPO/a.txt"; echo base > "$REPO/b.txt"
echo "SECRET=1" > "$REPO/server/.env.local"   # web/.env.local cố ý không có
git -C "$REPO" add a.txt b.txt; git -C "$REPO" commit -qm base

LOG="$TMP/calls.log"; : > "$LOG"
WTROOT="$TMP/workspaces"
export ORCA_WORKSPACES="$WTROOT"   # không đụng worktree của phòng thật đang chạy

# company.py giả: ghi lại mọi lệnh; room show lỗi nếu chưa room new; snapshot đọc $TMP/snapshot.json.
FAKE_CO="$TMP/company.py"
cat > "$FAKE_CO" <<PY
import json, os, sys
log = open("$LOG", "a"); log.write("company " + json.dumps(sys.argv[1:], ensure_ascii=False) + "\n"); log.close()
a = sys.argv[1:]
if a[:2] == ["room", "show"]:
    sys.exit(0 if os.path.exists("$TMP/room-" + a[2]) else 2)
if a[:2] == ["room", "new"]:
    open("$TMP/room-" + a[2], "w").close()
if a[:2] == ["task", "show"]:
    path = "$TMP/task-" + a[2] + ".json"
    if not os.path.exists(path):
        print("Không tìm thấy thẻ: " + a[2], file=sys.stderr); sys.exit(2)
    print(open(path).read())
if a[:1] == ["snapshot"]:
    print(open("$TMP/snapshot.json").read())
PY

# Orca giả: worktree create làm git worktree thật (nhánh = --name như Orca), terminal create trả JSON không có handle.
FAKE_ORCA="$TMP/orca"
cat > "$FAKE_ORCA" <<SH
#!/usr/bin/env bash
echo "orca \$*" >> "$LOG"
case "\$1 \$2" in
  "worktree create")
    name=""; while [ \$# -gt 0 ]; do [ "\$1" = --name ] && name="\$2"; shift; done
    mkdir -p "$WTROOT"; git -C "$REPO" worktree add -q -b "\$name" "$WTROOT/\$name" main >&2
    printf '{"ok":true,"result":{"worktree":{"path":"%s"}}}\n' "$WTROOT/\$name" ;;
  "terminal list")
    if [ -f "$TMP/term-created" ]; then
      printf '{"result":{"terminals":[{"handle":"term_old","worktreePath":"/x"},{"handle":"term_mgr","worktreePath":"%s"}]}}\n' "\$(cat "$TMP/term-created")"
    else
      echo '{"result":{"terminals":[{"handle":"term_old","worktreePath":"/x"}]}}'
    fi ;;
  "terminal create")
    wt=""; while [ \$# -gt 0 ]; do [ "\$1" = --worktree ] && wt="\${2#path:}"; shift; done
    echo "\$wt" > "$TMP/term-created"; echo '{"ok":true,"result":{}}' ;;
  "terminal read") echo "Claude Code ... Launching skill: phong-manager" ;;
  *) echo "orca giả: lệnh lạ \$*" >&2; exit 9 ;;
esac
SH
chmod +x "$FAKE_ORCA"

export SPORTSHUB_REPO="$REPO" ORCA="$FAKE_ORCA" COMPANY_PY="$FAKE_CO" MANAGER_WAIT=3 SPORTSHUB_CO="$TMP"

echo "bash -n"
for f in "$HERE"/bin/*.sh "$HERE"/tests/*.sh; do check "bash -n $(basename "$f")" "bash -n '$f'"; done

echo "open-room: tham số"
check "thiếu tiêu đề ⇒ exit 2" 'bash "$HERE/bin/open-room.sh" TEST >/dev/null 2>&1; [ $? -eq 2 ]'
check "KEY chữ thường ⇒ exit 2" 'bash "$HERE/bin/open-room.sh" test "x" --dry-run >/dev/null 2>&1; [ $? -eq 2 ]'
check "KEY 1 ký tự ⇒ exit 2" 'bash "$HERE/bin/open-room.sh" T "x" --dry-run >/dev/null 2>&1; [ $? -eq 2 ]'
check "cờ lạ ⇒ exit 2" 'bash "$HERE/bin/open-room.sh" TEST "x" --oops >/dev/null 2>&1; [ $? -eq 2 ]'

echo "open-room: --dry-run"
: > "$LOG"
OUT="$(bash "$HERE/bin/open-room.sh" TEST "x" "ý tưởng có 'nháy'" --dry-run)"; RC=$?
check "exit 0" '[ $RC -eq 0 ]'
check "không gọi orca/company.py" '[ ! -s "$LOG" ]'
check "không tạo worktree" '[ ! -e "$WTROOT" ]'
for want in "worktree create" "--base-branch main" "branch -m" ".env.local" "room new TEST" \
            "terminal create" "claude --model opus --effort medium --permission-mode bypassPermissions" \
            "/phong-manager TEST" "room set TEST --manager-terminal" "terminal read"; do
  check "in: $want" 'printf "%s" "$OUT" | grep -qF -- "$want"'
done

echo "open-room: chạy với Orca giả"
: > "$LOG"
RUN="$(bash "$HERE/bin/open-room.sh" ATTEND "Lát 2 — có mặt" "đi muộn bị trừ điểm" 2>&1)"; RC=$?
WT="$WTROOT/attend"
check "exit 0" '[ $RC -eq 0 ] || { echo "$RUN"; false; }'
check "nhánh phong/attend" '[ "$(git -C "$WT" branch --show-current)" = phong/attend ]'
check "chép server/.env.local" '[ "$(cat "$WT/server/.env.local")" = SECRET=1 ]'
check "không bịa web/.env.local" '[ ! -e "$WT/web/.env.local" ]'
check "room new đúng cờ" 'grep -qF "company [\"room\", \"new\", \"ATTEND\", \"--title\", \"Lát 2 — có mặt\", \"--branch\", \"phong/attend\", \"--worktree\", \"$WT\"]" "$LOG"'
check "room set handle mới (không lấy term_old)" 'grep -qF "[\"room\", \"set\", \"ATTEND\", \"--manager-terminal\", \"term_mgr\"]" "$LOG"'
check "room new trước terminal create" '[ "$(grep -n "\"room\", \"new\"" "$LOG" | cut -d: -f1)" -lt "$(grep -n "terminal create" "$LOG" | cut -d: -f1)" ]'
check "lệnh Manager đúng" 'grep -qF -- "--command claude --model opus --effort medium --permission-mode bypassPermissions" "$LOG"'
check "phòng trùng ⇒ exit 2" 'bash "$HERE/bin/open-room.sh" ATTEND "x" >/dev/null 2>&1; [ $? -eq 2 ]'
check "không --task ⇒ không gọi task" '! grep -qF "[\"task\"" "$LOG"'

echo "open-room: --task"
check "ID thẻ sai ⇒ exit 2" 'bash "$HERE/bin/open-room.sh" LINK "x" --task 3 --dry-run >/dev/null 2>&1; [ $? -eq 2 ]'
check "--task thiếu ID ⇒ exit 2" 'bash "$HERE/bin/open-room.sh" LINK "x" --task >/dev/null 2>&1; [ $? -eq 2 ]'
DRY="$(bash "$HERE/bin/open-room.sh" LINK "x" --task T1 --dry-run)"
check "dry-run in task start" 'printf "%s" "$DRY" | grep -qF "task start T1 --room LINK"'
: > "$LOG"
check "thẻ không có ⇒ exit 2, chưa gọi Orca" 'bash "$HERE/bin/open-room.sh" LINK "x" --task T9 >/dev/null 2>&1; [ $? -eq 2 ] && ! grep -q "^orca" "$LOG"'
echo '{"id":"T2","room":"ATTEND"}' > "$TMP/task-T2.json"
check "thẻ đã gắn phòng ⇒ exit 2, chưa gọi Orca" 'bash "$HERE/bin/open-room.sh" LINK "x" --task T2 >/dev/null 2>&1; [ $? -eq 2 ] && ! grep -q "^orca" "$LOG"'
echo '{"id":"T3","room":null,"asks":[{"id":"T3-q1","status":"resolved"},{"id":"T3-q2","status":"open"}]}' > "$TMP/task-T3.json"
OUT="$(bash "$HERE/bin/open-room.sh" LINK "x" --task T3 2>&1)"; RC=$?
check "thẻ còn câu chờ Sếp ⇒ exit 2, chưa gọi Orca" '[ $RC -eq 2 ] && ! grep -q "^orca" "$LOG"'
check "báo đúng câu còn mở" 'printf "%s" "$OUT" | grep -qF "T3-q2" && ! printf "%s" "$OUT" | grep -qF "T3-q1"'
echo '{"id":"T1","room":null}' > "$TMP/task-T1.json"
: > "$LOG"; rm -f "$TMP/term-created"
RUN="$(bash "$HERE/bin/open-room.sh" LINK "Mở từ thẻ" --task T1 2>&1)"; RC=$?
check "mở từ thẻ exit 0" '[ $RC -eq 0 ] || { echo "$RUN"; false; }'
check "gọi task start T1 --room LINK" 'grep -qF "[\"task\", \"start\", \"T1\", \"--room\", \"LINK\"]" "$LOG"'
check "task start sau room set" '[ "$(grep -n "\"room\", \"set\"" "$LOG" | cut -d: -f1)" -lt "$(grep -n "\"task\", \"start\"" "$LOG" | cut -d: -f1)" ]'

echo "overlap.sh"
# ATTEND (worktree trên) sửa a.txt; STATS sửa a.txt khác cách (xung đột) ; DOC chỉ sửa b.txt.
echo attend > "$WT/a.txt"; git -C "$WT" commit -qam attend
git -C "$REPO" branch phong/stats main; git -C "$REPO" branch phong/doc main
git -C "$REPO" worktree add -q "$TMP/stats" phong/stats; echo stats > "$TMP/stats/a.txt"; git -C "$TMP/stats" commit -qam stats
git -C "$REPO" worktree add -q "$TMP/doc" phong/doc; echo doc > "$TMP/doc/b.txt"; git -C "$TMP/doc" commit -qam doc
cat > "$TMP/snapshot.json" <<'J'
{"rooms":[
 {"key":"ATTEND","status":"active","branch":"phong/attend","overlaps":[]},
 {"key":"STATS","status":"active","branch":"phong/stats","overlaps":[]},
 {"key":"DOC","status":"active","branch":"phong/doc","overlaps":[{"with":"STATS","files":["x"],"conflict":false}]},
 {"key":"OLD","status":"done","branch":"phong/old","overlaps":[]}]}
J
: > "$LOG"
OV="$(bash "$HERE/bin/overlap.sh" --dry-run)"; RC=$?
check "dry-run exit 0" '[ $RC -eq 0 ] || { echo "$OV"; false; }'
check "dry-run không ghi (chỉ snapshot)" '[ "$(grep -c company "$LOG")" = 1 ] && grep -qF "[\"snapshot\"]" "$LOG"'
check "báo xung đột thật ATTEND↔STATS" 'printf "%s" "$OV" | grep -qF "XUNG ĐỘT THẬT: ATTEND ↔ STATS: a.txt"'
check "lệnh overlap 2 chiều có --conflict" 'printf "%s" "$OV" | grep -qF "overlap ATTEND --with STATS --files a.txt --conflict" && printf "%s" "$OV" | grep -qF "overlap STATS --with ATTEND --files a.txt --conflict"'
check "xoá dấu cũ DOC↔STATS" 'printf "%s" "$OV" | grep -qF "overlap DOC --with STATS --clear"'
check "bỏ qua phòng done" '! printf "%s" "$OV" | grep -q OLD'
# Đụng file mà gộp sạch: DOC sửa thêm dòng cuối a.txt? dùng file mới c.txt giống hệt ⇒ không xung đột.
echo same > "$TMP/doc/c.txt"; git -C "$TMP/doc" add c.txt; git -C "$TMP/doc" commit -qm c
echo same > "$TMP/stats/c.txt"; git -C "$TMP/stats" add c.txt; git -C "$TMP/stats" commit -qm c
OV2="$(bash "$HERE/bin/overlap.sh" --dry-run)"
check "đụng file nhưng gộp sạch ⇒ không --conflict" 'printf "%s" "$OV2" | grep -qF "overlap DOC --with STATS --files c.txt" && ! printf "%s" "$OV2" | grep -qF "overlap DOC --with STATS --files c.txt --conflict"'
: > "$LOG"
bash "$HERE/bin/overlap.sh" >/dev/null
check "chạy thật gọi company.py overlap" 'grep -qF "[\"overlap\", \"ATTEND\", \"--with\", \"STATS\", \"--files\", \"a.txt\", \"--conflict\"]" "$LOG"'

# ---------- tích hợp với company.py thật (lane L1), state tạm qua SPORTSHUB_CO ----------
REAL_CO="$HERE/bin/company.py"
if [ -f "$REAL_CO" ]; then
  echo "tích hợp company.py thật"
  CO2="$TMP/co"; mkdir -p "$CO2"
  run_co() { SPORTSHUB_CO="$CO2" python3 "$REAL_CO" "$@"; }
  check "room show phòng chưa có ⇒ exit khác 0" '! run_co room show ATTEND >/dev/null 2>&1'
  run_co room new ATTEND --title "Lát 2" --branch phong/attend --worktree "$WT" >/dev/null
  run_co room new STATS --title "Thống kê" --branch phong/stats --worktree "$TMP/stats" >/dev/null
  run_co room new DOC --title "Tài liệu" --branch phong/doc --worktree "$TMP/doc" >/dev/null
  check "room set --manager-terminal" 'run_co room set ATTEND --manager-terminal term_x >/dev/null'
  OV3="$(SPORTSHUB_CO="$CO2" COMPANY_PY="$REAL_CO" bash "$HERE/bin/overlap.sh")"; RC=$?
  check "overlap.sh ghi thật exit 0" '[ $RC -eq 0 ] || { echo "$OV3"; false; }'
  SNAP="$(run_co snapshot)"
  check "board có overlap ATTEND↔STATS conflict" 'printf "%s" "$SNAP" | python3 -c "
import json,sys; s=json.load(sys.stdin); r={x[\"key\"]:x for x in s[\"rooms\"]}
o=[x for x in r[\"ATTEND\"][\"overlaps\"] if x[\"with\"]==\"STATS\"]
assert o and o[0][\"conflict\"] and o[0][\"files\"]==[\"a.txt\"], o"'
  OV4="$(SPORTSHUB_CO="$CO2" COMPANY_PY="$REAL_CO" bash "$HERE/bin/overlap.sh")"
  check "chạy lại không ghi gì (idempotent)" 'printf "%s" "$OV4" | grep -qF "board đã khớp"'
  git -C "$TMP/doc" reset -q --hard HEAD~1   # DOC bỏ c.txt ⇒ hết đụng STATS
  OV5="$(SPORTSHUB_CO="$CO2" COMPANY_PY="$REAL_CO" bash "$HERE/bin/overlap.sh")"
  check "hết đụng ⇒ --clear chạy được" 'printf "%s" "$OV5" | grep -qF "hết đụng: DOC ↔ STATS" && [ "$(run_co snapshot | python3 -c "
import json,sys; s=json.load(sys.stdin); print(len([r for r in s[\"rooms\"] if r[\"key\"]==\"DOC\"][0][\"overlaps\"]))")" = 0 ]'
else
  echo "(bỏ qua tích hợp: chưa có bin/company.py)"
fi

echo
echo "Kết quả: $PASS qua, $FAIL hỏng"
[ "$FAIL" -eq 0 ]
