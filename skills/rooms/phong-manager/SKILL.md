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
C() { python3 $CO/bin/company.py "$@"; }   # CLI duy nhất ghi trạng thái — hàm, không biến: zsh không tách từ "C …"
KEY=<KEY>                          # chữ hoa, ví dụ ATTEND
k=<key>                            # chữ thường, ví dụ attend
R=.scratch/$k                      # hồ sơ phòng, tương đối với gốc worktree
```

## 1. Khởi động — và sau MỖI `/clear`/compact: biết mình đang ở bước nào

Làm ĐẦU TIÊN, trước mọi việc khác, kể cả khi tưởng mình còn nhớ:

```bash
pwd && git branch --show-current                 # phải là worktree phòng, nhánh phong/<key>
C room show $KEY --json                         # step, gates, lanes, asks open, bugs, appKey
ls -R $R 2>/dev/null; cat $R/NHAT-KY.md 2>/dev/null
C ask list --open --room $KEY
C key status
git log --oneline main..HEAD
```

Ghép hai nguồn: file phòng (`state/rooms/<KEY>.json`) nói bước + ai đang chạy + câu nào chờ Sếp;
`$R/` nói đã chốt gì (spec, brief, báo cáo lane). Hai nguồn lệch ⇒ tin file trên đĩa, sửa trạng thái bằng `C room set`.
Có lane `running` ⇒ đọc màn hình nó (`orca terminal read --terminal <h> --screen --limit 30`) và arm lại watcher (mục 5).
Mở lần đầu (chưa có `$R/`): `mkdir -p $R/briefs $R/reports`, tạo `$R/NHAT-KY.md` — mỗi quyết định một dòng có ngày.

## 1b. Luồng nhỏ — chọn trước khi hỏi đáp

Việc nhỏ = MỘT hành vi rõ, trong một mảng, dùng mẫu sẵn, dễ hoàn tác; KHÔNG đụng tiền/quyền/bảo mật, hợp đồng giữa
phòng, thư viện mới hay bảng/cột. Manager tự phân loại; giữa chừng thấy vượt tiêu chí ⇒ chuyển luồng đầy đủ.
- Yêu cầu Sếp đã rõ = đã chốt phạm vi; chỉ hỏi phần thiếu ảnh hưởng kết quả.
- Vai: Manager kiêm Techlead, một dev, một lane kiểm độc lập (QA + Review gộp). Không Designer, không gói phòng.
- Hồ sơ: một file `.scratch/<key>/spec.md` ngắn — phạm vi, điều kiện đạt, quyết định, kết quả kiểm. Luật đổi thì sửa
  hồ sơ tính năng đang có.
- Bỏ cổng 1–4. `make check` một lần trên bản cuối; Sếp duyệt MỘT lần: cổng 5 + 6 (gộp + push).
- Luồng đầy đủ giữ cho: màn mới cần định hướng, nghiệp vụ mới, hoặc việc vượt tiêu chí trên.

## 2. Hỏi đáp Sếp → spec + hồ sơ tính năng (step `hoi-dap`)

- Ý tưởng có dòng `Đầu vào: docs/product/nghien-cuu/<chu-de>.html` ⇒ đọc báo cáo TRƯỚC; mục "Sếp đã chốt" là
  quyết định, KHÔNG hỏi lại; phòng chỉ làm lát được giao, các lát sau ghi backlog.
- ⛔ **Sếp chọn, không gõ** (chốt 12/10/2026): KHÔNG hỏi mở kiểu "Sếp hình dung thế nào?". Tự đọc ADR, hồ sơ
  tính năng, màn lab để đoán ý Sếp, rồi biến mỗi chỗ còn mơ hồ thành MỘT ask `--kind quyet` có 2–4 phương án cụ thể
  + `--recommend` (W4). CLI tự thêm "Khác — tự viết"; Sếp chỉ gõ khi chọn Khác.
- Chỉ hỏi chỗ mơ hồ ẢNH HƯỞNG KẾT QUẢ (không mặc định `grilling` mọi chỗ); mỗi câu là một ask riêng (có thể mở nhiều ask cùng lúc
  nếu chúng không phụ thuộc nhau), không gộp nhiều câu vào một ask.
- Đối chiếu phạm vi v0.1 và triết lý trong `CLAUDE.md` ("PHẠM VI v0.1"); ngoài phạm vi ⇒ đề xuất ghi backlog (W7).
- Viết `$R/spec.md` (câu đã chốt, Q1…Qn) và `docs/features/<tên>.md` theo `docs/features/_khuon.md` —
  mục "Luật luôn đúng" là đầu vào của QA, viết kỹ nhất.

⛔ **Hồ sơ gọn** (Sếp duyệt 13/10 — một đợt từng viết 250–890 KB chữ mỗi phòng, nhiều chỗ chép lặp):
- `spec.md` CHỈ là nhật ký câu đã chốt (một dòng mỗi câu). Luật nghiệp vụ chỉ nằm ở `docs/features/<tên>.md` — không chép.
- Brief lane TRỎ tới file có sẵn (`techlead.md` mục…, `docs/features` mục…), không chép lại nội dung.
- Báo cáo lane ≤ 40 dòng: làm gì, số test, chỗ còn nghi ngờ. Báo cáo QA là markdown ngắn, không HTML.
- Không tạo file mới khi một mục trong file có sẵn đủ chỗ.
- `C room set $KEY --link spec=$R/spec.md --link featureDoc=docs/features/<tên>.md`

## 3. Cách hỏi Sếp — mọi cổng và mọi câu cần quyết

KHÔNG dùng AskUserQuestion. Luôn hai bước, rồi DỪNG lượt:

```bash
C ask add $KEY --kind duyet --gate 1 --title "Duyệt gói phòng + hồ sơ tính năng" \
   --context "<tóm tắt 3–6 dòng>" --link $R/spec.md --link docs/features/<tên>.md    # in ra id, ví dụ ATTEND-a3
C ask add $KEY --kind quyet --title "…" --option a="…" --option b="…" --recommend a  # câu chọn phương án
C ask add $KEY --kind thaotac --title "Bật Docker Desktop"                            # việc Sếp phải tự làm
```

Câu hỏi về lộ dữ liệu (ai thấy gì) ⇒ context liệt kê MỌI trường response sẽ hiện, không chỉ trường đang bàn (TEAM-SEARCH quên tên đội trưởng ⇒ phải hỏi thêm một câu). Context khẳng định code đang làm gì ⇒ đọc code trước.

`quyet` thiếu 2 phương án ⇒ CLI từ chối. Sếp chọn `khac` ⇒ câu trả lời nằm trong note. `thaotac` tự có nút
"Đã làm xong" (choice `done`). Câu hỏi đã mở mà cần thay ⇒ `C ask cancel <ID> --note "thay bằng <ID mới>"`.
Thư ký báo `Sếp bấm nhầm <ID>, đã mở lại` ⇒ bỏ câu trả lời trước của ID đó, chờ Sếp trả lời lại; KHÔNG tạo ask mới.

Rồi in **y nguyên** câu đó trong terminal, kèm id, các lựa chọn, khuyến nghị (W4), và dừng lượt.

Nhận câu trả lời (Sếp gõ ở đây, hoặc dòng `Sếp trả lời <ID> …` do Thư ký chuyển từ board) ⇒ việc ĐẦU TIÊN:

```bash
C ask list --room $KEY          # ask đã resolved (nhận trùng qua board) ⇒ BỎ QUA bước dưới
C ask resolve <ID> --choice <k> --note "<ghi chú của Sếp>" --via terminal    # thu-ky nếu Thư ký chuyển
```

`choice=ok` trên ask có `--gate` tự ghi cổng. Im lặng không bao giờ là đồng ý: chưa resolve thì chưa đi qua cổng.
Ghi quyết định vào `$R/NHAT-KY.md`.

## 4. Gói phòng — cổng 1

Trình trong một ask (`--kind duyet --gate 1`): phạm vi (làm / cố ý không làm), vai cần dùng (việc chỉ server ⇒ không
Designer, không dev-web), có cần chìa khoá app không, rủi ro đụng phòng khác (`C room list`).
Sau khi `ok`: `C room set $KEY --roles designer,techlead,… --needs-app-key yes|no --step thiet-ke`.

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

Mức suy nghĩ (`--effort` của Claude, `model_reasoning_effort` của Codex) — đặt theo việc, không mặc định high:

| Lượt | Mức |
|---|---|
| Techlead, Designer, Review, dev lượt đầu của một lát | `high` |
| QA chạy ca test theo kế hoạch đã duyệt, dev sửa lỗi nhỏ / sửa theo review, Designer sửa lab theo ghi chú | `medium` |

Dispatch MỘT câu trỏ vào brief. Model theo vai; mức suy nghĩ theo bảng trên — lệnh mẫu dưới là lượt đầu (`high`),
lượt `medium` thì đổi đúng số đó:

| Vai | Agent | Model |
|---|---|---|
| dev-server | codex | `-m gpt-6-astra` |
| dev-web | codex | `-m gpt-6.1-sol` |
| techlead, designer, review | Claude | `--model claude-opus-5-5` |
| qa | Claude | `--model claude-sonnet-5-5` |

```bash
# codex (dev-server; dev-web đổi -m gpt-6.1-sol). --add-dir mở thêm $CO cho sandbox ghi được, để lane tự gọi
# `company.py lane set`/`bug set` — ngoài worktree và $CO, sandbox workspace-write vẫn chặn ghi.
orca terminal send --terminal $H --enter --text "codex -s workspace-write -a never --strict-config -m gpt-6-astra -c model_reasoning_effort=high -c sandbox_workspace_write.network_access=true --add-dir /Users/tien/sportshub-company \"Lane <vai> phòng $KEY. Read $R/briefs/<vai>.md and follow it.\""
# Claude (techlead/designer/review: opus · qa: sonnet) — designer tự mở lane codex image_gen theo thiet-ke-man
orca terminal send --terminal $H --enter --text "claude --model claude-opus-5-5 --effort high --permission-mode bypassPermissions \"Lane <vai> phòng $KEY. Read $R/briefs/<vai>.md and follow it.\""
orca terminal send --terminal $H --enter --text "claude --model claude-sonnet-5-5 --effort high --permission-mode bypassPermissions \"Lane qa phòng $KEY. Read $R/briefs/qa.md and follow it.\""
orca terminal read --terminal $H --screen --limit 20      # xác nhận agent đã nhận việc
C lane add $KEY --role <vai> --handle $H --model codex|opus|sonnet
# dev-web ở phòng có Designer: CLI từ chối khi cổng 3 chưa duyệt. Sếp cho ngoại lệ ⇒ thêm --force-gate (được ghi lại).
```

Arm watcher **CÙNG lượt** dispatch (Bash `run_in_background`):

- codex: `<plugin>/skills/orca-orchestration/orca-lane-watch.sh --handles $H[,…]`
- Claude: `until grep -q "LANE-DONE <vai>" $R/reports/<vai>.md 2>/dev/null; do sleep 15; done; echo "<vai> xong"`
- luôn có một: `$CO/bin/wait-event.sh --room $KEY --types bug_opened,bug_changed,lane_changed` — thức thì chạy lại.

Giao lượt tiếp cho CÙNG lane (feedback, sửa lỗi, test lại) ⇒ trước đó `mv $R/reports/<vai>.md $R/reports/<vai>-<n>.md`,
không thì watcher bắt nhầm `LANE-DONE` của lượt cũ. Lượt mới gửi bằng `orca terminal send` một câu trỏ vào brief/ghi chú mới.
Lane codex mở bằng `--add-dir /Users/tien/sportshub-company` nên tự ghi được `C lane set`/`bug set`; Manager vẫn
`C room show $KEY` kiểm lại sau mỗi lượt — lane quên ghi (hay lệnh mở thiếu `--add-dir`) thì Manager tự `C lane set` thay.
Lane xong ⇒ `C lane set $KEY --handle $H --status done --note "<1 dòng>"`; hết việc ⇒ `orca terminal close --terminal $H --tab`
rồi `--status closed`.

**Vòng đời lane — Manager quyết đóng lane nào** (máy chỉ có chừng ấy RAM: một đợt 6 phòng từng để 65 phiên AI mở cùng
lúc, 7 GB, máy còn ~70 MB trống). Mỗi lần một lane báo xong, Manager tự hỏi: *lượt tới của phòng còn cần đúng phiên này
(nhớ ngữ cảnh) không?* Không ⇒ đóng ngay. Mặc định:

| Lane | Đóng khi |
|---|---|
| Techlead | qua cổng 4 và không còn câu kỹ thuật treo |
| Designer | qua cổng 3 (sửa lab sau này ⇒ mở lane mới, đọc lại `nghiem-thu.html`) |
| QA | sau lượt `ke-hoach`; mở lại cho lượt `test`/`test-lai` — trừ khi lượt test sắp tới ngay |
| dev-server / dev-web | lỗi QA đã đóng hết và review không còn 🔴 — giữ trong vòng sửa lỗi vì phiên còn nhớ code |
| Review | sau mỗi vòng có kết luận (vòng sau nên là phiên MỚI cho khách quan) |

Đóng = `orca terminal close --terminal $H --tab` rồi `C lane set $KEY --handle $H --status closed --note "<vì sao>"`.
⛔ **Phiên AI không dùng nữa thì đóng luôn** (Sếp chốt 14/10 — phiên treo làm cạn pin qua đêm). Lane `done` mà lượt tới
chưa tới NGAY ⇒ đóng, mở lại sau rẻ hơn để treo. Phòng chờ Sếp (`cho-gop`, ask cổng) ⇒ không còn lane nào mở. Xem màn bằng Playwright
xong (Manager hay lane) ⇒ gọi `browser_close` ngay, đừng để trình duyệt test mở chờ lượt sau. Đóng tab phiên là tắt luôn
server Playwright của phiên đó. Phiên Manager giữ tới `room done`; sau đó Thư ký đóng.

## 6. Designer + Techlead song song → cổng 2, 3, 4

Mở cả hai cùng lượt (vai không có trong gói thì bỏ). Đọc báo cáo, feedback qua `orca terminal send` tới khi đạt.
- Designer chạy `thiet-ke-man` (mục "Khi chạy trong phòng"). **Chỉ vẽ 3 ý tưởng khi làm màn MỚI hoàn toàn**: xem đủ 3,
  **tự chọn 1 + lý do** ⇒ ask cổng 2 (option mỗi bản, `--recommend` bản đã chọn). Sửa màn lab đã có ⇒ bỏ cổng 2, sửa
  thẳng rồi trình cổng 3. Giao diện mẫu xong + `nghiem-thu.html` ⇒ ask cổng 3.
- Techlead (`$R/techlead.md`, skill `phong-techlead`) ⇒ Manager soi đối chiếu spec ⇒ ask cổng 4: cột/bảng cụ thể,
  ADR, thư viện mới (W8 — chưa ok thì không ai viết migration/thêm dependency).
- **Hợp đồng chung giữa phòng** (cửa khoá, thứ tự lỗi, cài đặt/khái niệm nhiều phòng cùng cần): Techlead đã soi các
  phòng đang chạy (`C room list`). Phòng khác đã có ⇒ dùng lại, `C note` sang phòng đó; chưa ai có ⇒ phòng này chốt
  trong ADR nháp + note cho phòng liên quan TRƯỚC khi dev viết. Hai phòng chốt khác nhau ⇒ ask Sếp ngay, không đợi gộp.
`C room set $KEY --step kien-truc` khi chỉ còn chờ Techlead; `--link nghiemThu=…` khi có.

## 7. Kế hoạch test → code (step `ke-hoach-test` → `code`)

- QA lane (`phong-qa`) viết `$R/qa-plan.md` TRƯỚC khi dev code. Manager duyệt: mỗi luật đủ ba ca, đủ ma trận.
- Phòng ĐỔI một luật đã có ⇒ trước khi giao dev, `grep -rn` toàn `docs/` theo câu chữ của luật cũ; mọi chỗ còn tả luật
  cũ vào brief dev (TEAM-SEARCH sót 7 chỗ, review mới bắt).
- Rồi dev-server + dev-web song song (file rời nhau). Thứ tự W7: Entity → Repository → Service → Controller → Test;
  test trong code bắt buộc (C9). Migration: `V<số kế tiếp trên nhánh>__<desc>.sql`, số chốt lại lúc gộp (mục 11).

## 8. Vòng lỗi (step `test`)

Skill `triage` (plugin mattpocock-skills) để xếp lỗi: sửa trong phòng, dời backlog, hay hỏi Sếp.

QA `bug add` ⇒ watcher báo `bug_opened` ⇒ Manager đọc thẻ, giao dev đúng `area`:

```bash
C bug set <ID> --status fixing --assignee dev-server|dev-web --note "giao lane …" --by manager
orca terminal send --terminal <h-dev> --enter --text "Sửa lỗi <ID>: <tóm tắt>. Xem C room show $KEY. Xong thì báo cáo vào $R/reports/<vai>.md."
C bug set <ID> --status retest --note "<commit/ file đã sửa>" --by manager     # dev xong (dev codex không gọi được CLI)
C bug set <ID> --status deferred --note "<dòng backlog / commit ghi backlog>" --by manager   # dời backlog (lỗi có sẵn trên main, ngoài phạm vi lát)
```

Rồi nhắn QA test lại đúng ca. **Chỉ QA đóng** (`--status closed --by qa`). Lỗi cần quyết hành vi ⇒ QA dùng
`--needs-boss`, Manager mở `C ask add $KEY --kind quyet …` và hỏi Sếp như mục 3.

## 9. Chìa khoá app

Chạy app thật (server 8080, web 5173) chỉ khi giữ chìa khoá — trên DB RIÊNG của phòng, không đụng DB `sportshub` của Sếp:

```bash
C key request $KEY --reason "<vì sao>"   # trống ⇒ nhận luôn; phòng khác giữ ⇒ xếp hàng, làm việc khác
make qa-up KEY=$k        # CHỈ khi `key status` cho thấy phòng mình giữ: tạo DB sportshub_<k>, chạy server + web
make qa-down KEY=$k && C key release $KEY   # ngay khi xong lượt test — còn phòng chờ thì chìa khoá tự chuyển sang họ
```

⛔ KHÔNG BAO GIỜ `make dev` / `make stop` trong worktree phòng: `make dev` đụng tên container DB, `make stop` giết theo
cổng (cả lab 5174 của phòng khác) và tắt container DB dùng chung. `qa-down` chỉ tắt đúng PID phòng mình bật.

Thư ký điều phối chìa khoá giữa các phòng, nhắn vào terminal này:
- *"phòng X cần chìa khoá…"* ⇒ không ai trong phòng còn chạy app ⇒ `make qa-down KEY=$k && C key release $KEY` ngay;
  còn cần (QA đang dở lượt) ⇒ trả lời Thư ký ước lượng bao lâu, xong thì nhả. Không ôm chìa khoá khi không chạy app.
- *"phòng bạn đã có chìa khoá"* ⇒ giao lượt test đang chờ cho QA.

Lượt test của QA: QA tự `key request`/`qa-up`/`qa-down`/`release` theo `phong-qa`; ai nhận thì người đó nhả.
Thiết kế, lab, test Testcontainers không cần chìa khoá. Lab chạy cổng riêng của phòng và báo
`C note $KEY "đang chạy lab <cổng>"`; hai phòng không dùng chung một cổng lab.

## 10. Review

Mở lane MỚI `review` (Claude opus, skill `phong-review`), không dùng lại lane Techlead. Đọc `$R/review.md`.
Còn 🔴 ⇒ giao dev sửa ⇒ mở review lại (lane mới hoặc nhắn lane review soi lại diff mới). Hết 🔴 và QA xong ⇒
`C room set $KEY --link qaReport=$R/qa-report.md --link review=$R/review.md` rồi sang ngay mục 11 — KHÔNG trình
cổng 5 riêng (cổng 5 + 6 gộp một lần duyệt, Sếp duyệt 13/10).

## 11. Chuẩn bị gộp → cổng 5 + 6 (một lần duyệt)

Xung đột khi rebase ⇒ skill `resolving-merge-conflicts` (plugin mattpocock-skills); giữ luật của CẢ HAI phía.

```bash
C room set $KEY --step chuan-bi-gop
git rebase main                      # main local mới nhất; Sếp pull main ở repo gốc nếu cần (ask thaotac)
ls server/src/main/resources/db/migration/          # so với: git ls-tree --name-only main server/src/main/resources/db/migration/
git mv …/V12__x.sql …/V13__x.sql     # trùng số ⇒ đổi sang số kế tiếp (file chưa vào main, không phạm C10), sửa chỗ nhắc tên, python3 scripts/docs-gen.py
(cd server && ./mvnw -q clean)      # sau MỌI lần đổi số: target/classes còn bản cũ ⇒ Flyway "more than one migration with version N"
make check > $R/check-$(git rev-parse --short HEAD).log 2>&1   # MỘT lần; số trình Sếp lấy từ log này
C room set $KEY --step cho-gop      # Thư ký thức, chạy lại make check, ghi evidence
```

Ask MỘT lần: `C ask add $KEY --kind duyet --gate 6 --also-gate 5 --title "Check cuối + cho gộp lát …"` với context:
**nguyên văn** dòng KẾT LUẬN + mọi 🔴/🟡 của review, tóm tắt QA (ca đạt/lỗi, bug mở/đóng), số test sau rebase, commit
list (`git log --oneline main..HEAD`), danh sách "Đã tự quyết". Rebase phải sửa xung đột lớn (đổi logic, không chỉ số
migration/docs) ⇒ tách lại: ask cổng 5 trước rồi cổng 6. Chỉ khi ask đó = `ok`:

```bash
git -C /Users/tien/Claude/sportshub status --porcelain      # có thay đổi tracked ở repo gốc ⇒ DỪNG, hỏi Sếp
git -C /Users/tien/Claude/sportshub merge --ff-only phong/$k
git -C /Users/tien/Claude/sportshub push
make -C /Users/tien/Claude/sportshub qa-drop KEY=$k        # xoá DB QA riêng sportshub_<key> của phòng (Makefile của main đã có qa-drop)
C room done $KEY                     # in lệnh dọn — đóng lane trước, lệnh xoá worktree chạy CUỐI (nó đóng luôn terminal này)
```

ff-only thất bại (main đã đi tiếp) ⇒ rebase lại. **Rebase cơ học** — xung đột chỉ ở số migration/ADR, file máy sinh
(`docs/reference/`), hoặc hai phía cùng THÊM dòng (locales, bảng ADR, trường record/fixture) mà không đổi logic — thì
đổi số, `make check` lại trên SHA mới (log mới) và gộp luôn, KHÔNG xin lại cổng 6, không mở review lại; ghi
`C note $KEY "rebase cơ học sau <phòng>, check <sha> xanh"`. Xung đột đổi logic, hoặc check đỏ ⇒ ask cổng 6 lại.
Số migration/ADR chỉ chốt ở bước này: trong lúc làm dùng số kế tiếp của main, đổi bao nhiêu lần cũng là việc cơ học.

Sau `room done`: chạy skill `retro` (plugin mattpocock-skills) — cái gì chạy tốt, cái gì vướng, lỗ hổng quy trình nào lộ ra —
ghi vào `.scratch/<key>/retro.md` và `company.py note <KEY> "retro: …"` để Thư ký gom cho cả công ty.

## 12. Git trong phòng

Trên nhánh `phong/<key>`: commit tự do, không cần xin (spec Q15) — vẫn sau `make check` hoặc phần test liên quan xanh.
Gộp `main` và push LUÔN cần cổng 6. Lane trong worktree không commit được ⇒ Manager `git add <đúng danh sách file lane báo>`,
không bao giờ `git add -A`/`git add .`. Message theo mục "Viết message" trong `CLAUDE.md`, kèm dòng `Co-Authored-By`.
Bảng "KHÔNG BAO GIỜ commit" trong `CLAUDE.md` vẫn áp: `git diff --cached --name-only | grep -E "target/|\.log$|node_modules|\.env"` phải trống.

## 13. Kiểm chứng — một lần, trên bản cuối

- Lane tự chạy test phần mình đụng. Manager KHÔNG chạy lại toàn bộ sau mỗi lane — chỉ kiểm `git status --porcelain`
  khớp file lane báo (sửa ngoài "Files You May Edit" ⇒ trả lại) và xem màn (1440 + 390) khi có giao diện.
- `make check` toàn bộ chạy MỘT lần ở mục 11, sau rebase; lưu log `$R/check-<sha>.log` (Thư ký đọc log này + SHA,
  chỉ chạy lại khi SHA lệch hoặc log bất thường). Số trình Sếp lấy từ log đó.
- Review độc lập MỘT lần trước gộp (lane `review`, mục 10); vòng sửa lỗi chỉ soi phần sửa và nơi bị ảnh hưởng.

