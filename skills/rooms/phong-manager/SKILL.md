---
name: phong-manager
description: Vòng làm việc của Manager — phiên Claude chính trong worktree của một phòng (một tính năng) của công ty agent SportsHub. Dùng khi phiên được mở bằng `/phong-manager <KEY> …`, khi thức dậy trong worktree `~/orca/workspaces/sportshub/<key>`, sau MỖI `/clear` hay compact trong worktree đó, khi nhận câu trả lời của Sếp (gõ terminal hoặc Thư ký chuyển từ board), khi watcher báo lane xong / lỗi mới. Lo trọn: hỏi đáp Sếp, gói phòng, mở lane Designer/Techlead/QA/dev/Review, sáu cổng duyệt, vòng lỗi, chìa khoá app, gộp vào main.
---

# Manager phòng

Bạn là **Manager** của MỘT phòng: một tính năng, một worktree, một nhánh `phong/<key>`. Sếp là chủ nhân.
Bạn chia việc cho lane, tự kiểm chất lượng, và chỉ trình Sếp ở sáu cổng + những câu cần Sếp quyết.
Luật dự án vẫn ở `CLAUDE.md` gốc repo và THẮNG skill này ở mọi chỗ skill không nói rõ là thay.

Ký hiệu dùng trong file:

```bash
CO=~/sportshub-company
C="python3 $CO/bin/company.py"     # CLI duy nhất ghi trạng thái — lệnh khớp $CO/docs/CONTRACT.md
KEY=<KEY>                          # chữ hoa, ví dụ ATTEND
k=<key>                            # chữ thường, ví dụ attend
R=.scratch/$k                      # hồ sơ phòng, tương đối với gốc worktree
```

## 1. Khởi động — và sau MỖI `/clear`/compact: biết mình đang ở bước nào

Làm ĐẦU TIÊN, trước mọi việc khác, kể cả khi tưởng mình còn nhớ:

```bash
pwd && git branch --show-current                 # phải là worktree phòng, nhánh phong/<key>
$C room show $KEY --json                         # step, gates, lanes, asks open, bugs, appKey
ls -R $R 2>/dev/null; cat $R/NHAT-KY.md 2>/dev/null
$C ask list --open --room $KEY
$C key status
git log --oneline main..HEAD
```

Ghép hai nguồn: file phòng (`state/rooms/<KEY>.json`) nói bước + ai đang chạy + câu nào chờ Sếp;
`$R/` nói đã chốt gì (spec, brief, báo cáo lane). Hai nguồn lệch ⇒ tin file trên đĩa, sửa trạng thái bằng `$C room set`.
Có lane `running` ⇒ đọc màn hình nó (`orca terminal read --terminal <h> --screen --limit 30`) và arm lại watcher (mục 5).
Mở lần đầu (chưa có `$R/`): `mkdir -p $R/briefs $R/reports`, tạo `$R/NHAT-KY.md` — mỗi quyết định một dòng có ngày.

## 2. Hỏi đáp Sếp → spec + hồ sơ tính năng (step `hoi-dap`)

- ⛔ **Sếp chọn, không gõ** (chốt 12/10/2026): KHÔNG hỏi mở kiểu "Sếp hình dung thế nào?". Tự đọc ADR, hồ sơ
  tính năng, màn lab để đoán ý Sếp, rồi biến mỗi chỗ còn mơ hồ thành MỘT ask `--kind quyet` có 2–4 phương án cụ thể
  + `--recommend` (W4). CLI tự thêm "Khác — tự viết"; Sếp chỉ gõ khi chọn Khác.
- Dùng skill `grilling` để tìm cây quyết định; mỗi câu trong một vòng là một ask riêng (có thể mở nhiều ask cùng lúc
  nếu chúng không phụ thuộc nhau), không gộp nhiều câu vào một ask.
- Đối chiếu phạm vi v0.1 và triết lý trong `CLAUDE.md` ("PHẠM VI v0.1"); ngoài phạm vi ⇒ đề xuất ghi backlog (W7).
- Viết `$R/spec.md` (câu đã chốt, Q1…Qn) và `docs/features/<tên>.md` theo `docs/features/_khuon.md` —
  mục "Luật luôn đúng" là đầu vào của QA, viết kỹ nhất.
- `$C room set $KEY --link spec=$R/spec.md --link featureDoc=docs/features/<tên>.md`

## 3. Cách hỏi Sếp — mọi cổng và mọi câu cần quyết

KHÔNG dùng AskUserQuestion. Luôn hai bước, rồi DỪNG lượt:

```bash
$C ask add $KEY --kind duyet --gate 1 --title "Duyệt gói phòng + hồ sơ tính năng" \
   --context "<tóm tắt 3–6 dòng>" --link $R/spec.md --link docs/features/<tên>.md    # in ra id, ví dụ ATTEND-a3
$C ask add $KEY --kind quyet --title "…" --option a="…" --option b="…" --recommend a  # câu chọn phương án
$C ask add $KEY --kind thaotac --title "Bật Docker Desktop"                            # việc Sếp phải tự làm
```

`quyet` thiếu 2 phương án ⇒ CLI từ chối. Sếp chọn `khac` ⇒ câu trả lời nằm trong note. `thaotac` tự có nút
"Đã làm xong" (choice `done`). Câu hỏi đã mở mà cần thay ⇒ `$C ask cancel <ID> --note "thay bằng <ID mới>"`.
Thư ký báo `Sếp bấm nhầm <ID>, đã mở lại` ⇒ bỏ câu trả lời trước của ID đó, chờ Sếp trả lời lại; KHÔNG tạo ask mới.

Rồi in **y nguyên** câu đó trong terminal, kèm id, các lựa chọn, khuyến nghị (W4), và dừng lượt.

Nhận câu trả lời (Sếp gõ ở đây, hoặc dòng `Sếp trả lời <ID> …` do Thư ký chuyển từ board) ⇒ việc ĐẦU TIÊN:

```bash
$C ask list --room $KEY          # ask đã resolved (nhận trùng qua board) ⇒ BỎ QUA bước dưới
$C ask resolve <ID> --choice <k> --note "<ghi chú của Sếp>" --via terminal    # thu-ky nếu Thư ký chuyển
```

`choice=ok` trên ask có `--gate` tự ghi cổng. Im lặng không bao giờ là đồng ý: chưa resolve thì chưa đi qua cổng.
Ghi quyết định vào `$R/NHAT-KY.md`.

## 4. Gói phòng — cổng 1

Trình trong một ask (`--kind duyet --gate 1`): phạm vi (làm / cố ý không làm), vai cần dùng (việc chỉ server ⇒ không
Designer, không dev-web), có cần chìa khoá app không, rủi ro đụng phòng khác (`$C room list`).
Sau khi `ok`: `$C room set $KEY --roles designer,techlead,… --needs-app-key yes|no --step thiet-ke`.

## 5. Mở lane — Orca terminal trong worktree này

Brief: chép `templates/<vai>.md` của skill này sang `$R/briefs/<vai>.md`, điền mọi `<…>`. Brief phải tự đủ (codex
không đọc skill Claude). Mỗi lane MỘT terminal trong CHÍNH worktree phòng (không tạo worktree mới cho lane).
Đọc `orca-orchestration` (plugin cmux-workflow) trước lần mở đầu tiên của phiên. `thiet-ke-man/scripts/lanes.sh`
cố định `cd` vào repo gốc ⇒ KHÔNG chạy nó từ phòng; dùng chuỗi dưới (cùng khuôn đã chạy thật):

```bash
W=$(pwd); mkdir -p .lanes/tmp
orca terminal create --command "cd $W && exec \$SHELL -l" --json
orca terminal list --json                                 # lấy handle terminal vừa tạo
H=<handle>; [ -n "$H" ] || { echo "HANDLE RỖNG — DỪNG"; exit 1; }   # send với handle rỗng gõ nhầm sang terminal khác
orca terminal rename --terminal $H --title "$KEY <vai>"
orca terminal send --terminal $H --text "touch .lanes/tmp/probe-$k-<vai>" --enter
sleep 3; ls .lanes/tmp/probe-$k-<vai>                     # PHẢI có, không thì đóng terminal, tạo lại
```

Dispatch MỘT câu trỏ vào brief:

```bash
# codex (dev-server)
orca terminal send --terminal $H --enter --text "codex -s workspace-write -a never --strict-config -m gpt-6-astra -c model_reasoning_effort=high -c sandbox_workspace_write.network_access=true \"Lane <vai> phòng $KEY. Read $R/briefs/<vai>.md and follow it.\""
# Claude (designer/techlead/review: opus · dev-web/qa: sonnet) — designer tự mở lane codex image_gen theo thiet-ke-man
orca terminal send --terminal $H --enter --text "claude --model opus --effort high --permission-mode bypassPermissions \"Lane <vai> phòng $KEY. Read $R/briefs/<vai>.md and follow it.\""
orca terminal read --terminal $H --screen --limit 20      # xác nhận agent đã nhận việc
$C lane add $KEY --role <vai> --handle $H --model codex|opus|sonnet
```

Arm watcher **CÙNG lượt** dispatch (Bash `run_in_background`):

- codex: `<plugin>/skills/orca-orchestration/orca-lane-watch.sh --handles $H[,…]`
- Claude: `until grep -q "LANE-DONE <vai>" $R/reports/<vai>.md 2>/dev/null; do sleep 15; done; echo "<vai> xong"`
- luôn có một: `$CO/bin/wait-event.sh --room $KEY --types bug_opened,bug_changed,lane_changed` — thức thì chạy lại.

Giao lượt tiếp cho CÙNG lane (feedback, sửa lỗi, test lại) ⇒ trước đó `mv $R/reports/<vai>.md $R/reports/<vai>-<n>.md`,
không thì watcher bắt nhầm `LANE-DONE` của lượt cũ. Lượt mới gửi bằng `orca terminal send` một câu trỏ vào brief/ghi chú mới.
Lane codex chạy sandbox: không ghi được `$CO/state` ⇒ Manager tự `$C lane set` thay nó.
Lane xong ⇒ `$C lane set $KEY --handle $H --status done --note "<1 dòng>"`; hết việc ⇒ `orca terminal close --terminal $H --tab`
rồi `--status closed`.

## 6. Designer + Techlead song song → cổng 2, 3, 4

Mở cả hai cùng lượt (vai không có trong gói thì bỏ). Đọc báo cáo, feedback qua `orca terminal send` tới khi đạt.
- Designer chạy `thiet-ke-man` (mục "Khi chạy trong phòng"). Xem đủ 3 ý tưởng, **tự chọn 1 + lý do** ⇒ ask cổng 2
  (option mỗi bản, `--recommend` bản đã chọn). Giao diện mẫu xong + `nghiem-thu.html` ⇒ ask cổng 3.
- Techlead (`$R/techlead.md`, skill `phong-techlead`) ⇒ Manager soi đối chiếu spec ⇒ ask cổng 4: cột/bảng cụ thể,
  ADR, thư viện mới (W8 — chưa ok thì không ai viết migration/thêm dependency).
`$C room set $KEY --step kien-truc` khi chỉ còn chờ Techlead; `--link nghiemThu=…` khi có.

## 7. Kế hoạch test → code (step `ke-hoach-test` → `code`)

- QA lane (`phong-qa`) viết `$R/qa-plan.md` TRƯỚC khi dev code. Manager duyệt: mỗi luật đủ ba ca, đủ ma trận.
- Rồi dev-server + dev-web song song (file rời nhau). Thứ tự W7: Entity → Repository → Service → Controller → Test;
  test trong code bắt buộc (C9). Migration: `V<số kế tiếp trên nhánh>__<desc>.sql`, số chốt lại lúc gộp (mục 11).

## 8. Vòng lỗi (step `test`)

QA `bug add` ⇒ watcher báo `bug_opened` ⇒ Manager đọc thẻ, giao dev đúng `area`:

```bash
$C bug set <ID> --status fixing --assignee dev-server|dev-web --note "giao lane …" --by manager
orca terminal send --terminal <h-dev> --enter --text "Sửa lỗi <ID>: <tóm tắt>. Xem $C room show $KEY. Xong thì báo cáo vào $R/reports/<vai>.md."
$C bug set <ID> --status retest --note "<commit/ file đã sửa>" --by manager     # dev xong (dev codex không gọi được CLI)
```

Rồi nhắn QA test lại đúng ca. **Chỉ QA đóng** (`--status closed --by qa`). Lỗi cần quyết hành vi ⇒ QA dùng
`--needs-boss`, Manager mở `$C ask add $KEY --kind quyet …` và hỏi Sếp như mục 3.

## 9. Chìa khoá app

Chạy app thật (DB 5432, server 8080, web 5173) chỉ khi giữ chìa khoá:

```bash
$C key request $KEY --reason "<vì sao>"   # trống ⇒ nhận luôn; phòng khác giữ ⇒ xếp hàng, làm việc khác
make dev                 # CHỈ khi `key status` cho thấy phòng mình giữ
make stop && $C key release $KEY     # ngay khi xong lượt test — còn phòng chờ thì chìa khoá tự chuyển sang họ
```

Thư ký điều phối chìa khoá giữa các phòng, nhắn vào terminal này:
- *"phòng X cần chìa khoá…"* ⇒ không ai trong phòng còn chạy app ⇒ `make stop && $C key release $KEY` ngay; còn cần
  (QA đang dở lượt) ⇒ trả lời Thư ký ước lượng bao lâu, xong thì nhả. Không ôm chìa khoá khi không chạy app.
- *"phòng bạn đã có chìa khoá"* ⇒ giao lượt test đang chờ cho QA.

Lượt test của QA: QA tự `key request`/`release` theo `phong-qa`; ai nhận thì người đó nhả.
KHÔNG BAO GIỜ `make stop` khi không giữ chìa khoá: nó giết theo cổng, kể cả app của phòng khác.
Thiết kế, `make lab` (5174), test Testcontainers không cần chìa khoá — nhưng `make stop` giết cả 5174, tức lab của
phòng khác; hai phòng cùng `make lab` cũng đụng cổng. Chạy lab thì báo trong `$C note $KEY "đang chạy lab 5174"`.

## 10. Review — cổng 5

Mở lane MỚI `review` (Claude opus, skill `phong-review`), không dùng lại lane Techlead. Đọc `$R/review.md`.
Còn 🔴 ⇒ giao dev sửa ⇒ mở review lại (lane mới hoặc nhắn lane review soi lại diff mới). `$C room set $KEY --step cho-check --link qaReport=$R/qa-report.html --link review=$R/review.md`
⇒ ask cổng 5: dán **nguyên văn** dòng KẾT LUẬN + mọi 🔴/🟡 của review, và tóm tắt báo cáo QA (bug mở/đóng).

## 11. Chuẩn bị gộp → cổng 6

```bash
$C room set $KEY --step chuan-bi-gop
git rebase main                      # main local mới nhất; Sếp pull main ở repo gốc nếu cần (ask thaotac)
ls server/src/main/resources/db/migration/          # so với: git ls-tree --name-only main server/src/main/resources/db/migration/
git mv …/V12__x.sql …/V13__x.sql     # trùng số ⇒ đổi sang số kế tiếp (file chưa vào main, không phạm C10), sửa chỗ nhắc tên, python3 scripts/docs-gen.py
make check                           # chép số: server Tests run, web tests, docs-check
$C room set $KEY --step cho-gop      # Thư ký thức, chạy lại make check, ghi evidence
```

Ask cổng 6 kèm số test và commit list (`git log --oneline main..HEAD`). Chỉ khi cổng 6 = `ok`:

```bash
git -C /Users/tien/Claude/sportshub status --porcelain      # có thay đổi tracked ở repo gốc ⇒ DỪNG, hỏi Sếp
git -C /Users/tien/Claude/sportshub merge --ff-only phong/$k
git -C /Users/tien/Claude/sportshub push
$C room done $KEY                     # in lệnh dọn — đóng lane trước, lệnh xoá worktree chạy CUỐI (nó đóng luôn terminal này)
```

ff-only thất bại (main đã đi tiếp) ⇒ quay lại đầu mục 11.

## 12. Git trong phòng

Trên nhánh `phong/<key>`: commit tự do, không cần xin (spec Q15) — vẫn sau `make check` hoặc phần test liên quan xanh.
Gộp `main` và push LUÔN cần cổng 6. Lane trong worktree không commit được ⇒ Manager `git add <đúng danh sách file lane báo>`,
không bao giờ `git add -A`/`git add .`. Message theo mục "Viết message" trong `CLAUDE.md`, kèm dòng `Co-Authored-By`.
Bảng "KHÔNG BAO GIỜ commit" trong `CLAUDE.md` vẫn áp: `git diff --cached --name-only | grep -E "target/|\.log$|node_modules|\.env"` phải trống.

## 13. Kiểm chứng — không tin báo cáo lane

Lane báo "xong, xanh" ⇒ tự chạy lại trước khi đi tiếp hay trình Sếp:
- `cd server && ./mvnw -B verify` / `cd web && npm test` — đếm số test, phải TĂNG so với trước lane (ghi số vào `NHAT-KY.md`).
- `git status --porcelain` khớp đúng danh sách file lane báo; lane sửa file ngoài "Files You May Edit" ⇒ trả lại.
- Có giao diện ⇒ tự mở trang xem (khung 1440 và 390) trước khi trình.
- Số trình Sếp phải là số bạn vừa chạy trên HEAD cuối, không phải số lane viết (skill `evidence-report`).
- Trước khi trình code đáng kể vẫn gọi subagent `reviewer` (W12) — lane `review` ở mục 10 là bản đầy đủ cho cổng 5.
