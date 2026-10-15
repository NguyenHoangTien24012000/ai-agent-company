# Luồng làm việc: công ty agent SportsHub

Chốt 12/10/2026 (spec: `/Users/tien/Claude/sportshub/.scratch/cong-ty-agent/spec.md`). Định dạng và lệnh chính xác:
`docs/CONTRACT.md`. Vòng làm việc của Thư ký: skill `skills/thu-ky/SKILL.md`.

**Nguyên tắc:** mỗi tính năng là một **phòng** (worktree + nhánh riêng), nhiều phòng chạy song song. Anh chỉ chạm
vào phòng ở **6 cổng duyệt** và những câu Manager cần anh quyết. Mọi chỗ anh cần chạm đều ở mục "Việc của anh"
trên board. **Im lặng không bao giờ là đồng ý.**

## Vai

| Ai | Làm gì | Model | Ở đâu |
|---|---|---|---|
| **Anh (Sếp)** | Quyết phạm vi, duyệt thiết kế, check cuối, cho gộp | — | Board + terminal Orca |
| **Thư ký** | Mở phòng, chuyển câu trả lời từ board, chạy lại test kiểm số, báo đụng file | Opus | Phiên Claude ở `~/sportshub-company` |
| **Manager** | Hỏi đáp anh, viết hồ sơ, chia lane, quản lỗi, gộp sau cổng 6 | Opus | Terminal chính của phòng, skill `phong-manager` |
| **Designer** | 3 ý tưởng → giao diện mẫu (`web/src/lab`) → `nghiem-thu.html` | Codex `image_gen` → Claude | Lane Orca, skill `thiet-ke-man` |
| **Techlead** | Cột/bảng, API, ADR, thư viện | Opus | Lane Orca, `phong-techlead` |
| **Dev server / Dev web** | Code + test trong code | Codex / Sonnet | Lane Orca |
| **QA** | Kế hoạch test trước, test app thật, báo lỗi (không sửa) | Sonnet | Lane Orca, `phong-qa` |
| **Review** | Review cuối bằng lane MỚI (không dùng lại Techlead) | Opus | Lane Orca, `phong-review` |

Manager quyết phòng cần vai nào (việc chỉ server thì không có Designer) và trình trong gói phòng (cổng 1).

## Luồng nhỏ

Việc nhỏ = MỘT hành vi rõ, trong một mảng, dùng mẫu sẵn, dễ hoàn tác; KHÔNG đụng tiền/quyền/bảo mật, hợp đồng giữa
phòng, thư viện mới hay bảng/cột. Manager tự phân loại; giữa chừng thấy vượt tiêu chí ⇒ chuyển luồng đầy đủ.
- Yêu cầu Sếp đã rõ = đã chốt phạm vi; chỉ hỏi phần thiếu ảnh hưởng kết quả.
- Vai: Manager kiêm Techlead, một dev, một lane kiểm độc lập (QA + Review gộp). Không Designer, không gói phòng.
- Hồ sơ: một file `.scratch/<key>/spec.md` ngắn — phạm vi, điều kiện đạt, quyết định, kết quả kiểm. Luật đổi thì sửa
  hồ sơ tính năng đang có.
- Bỏ cổng 1–4. `make check` một lần trên bản cuối; Sếp duyệt MỘT lần: cổng 5 + 6 (gộp + push).
- Luồng đầy đủ giữ cho: màn mới cần định hướng, nghiệp vụ mới, hoặc việc vượt tiêu chí trên.

## Luồng một phòng

| # | Bước (`step` trên board) | Ai | Anh chạm? |
|---|---|---|---|
| 1 | Anh chat Thư ký **"mở phòng: <ý tưởng>"** ⇒ worktree `phong/<key>` từ `main`, chép `.env.local`, mở Manager, ghi board | Thư ký | |
| 2 | **Hỏi đáp** (`hoi-dap`): Manager hỏi để hiểu ý, chỉ hỏi chỗ mơ hồ ảnh hưởng kết quả ⇒ `.scratch/<key>/spec.md` + `docs/features/<tên>.md` | Manager ↔ anh | trả lời câu hỏi |
| 3 | **Gói phòng** (`cho-goi`): phạm vi, vai cần dùng, có cần chìa khoá app | Manager | ✅ **Cổng 1** |
| 4 | **Thiết kế** (`thiet-ke`) ‖ **Kiến trúc** (`kien-truc`) chạy song song | Designer, Techlead | ✅ **Cổng 2, 3, 4** |
| 5 | **Kế hoạch test** (`ke-hoach-test`) từ "Luật luôn đúng"; Manager duyệt | QA | |
| 6 | **Code** (`code`): dev server + dev web, test trong code. Phòng có Designer: lane dev web chỉ mở sau cổng 3 (`lane add` chặn; `--force-gate` khi anh đồng ý ngoại lệ) | Dev | |
| 7 | **Test** (`test`): QA test app thật (giữ chìa khoá app) ⇒ vòng lỗi | QA ↔ Dev | chỉ lỗi cần quyết hành vi |
| 8 | **Review** (`review`): lane mới, sửa hết 🔴 | Review ↔ Dev | |
| 9 | (Check cuối không còn là bước riêng — gộp vào bước 11, cổng 5 + 6 một lần duyệt) | | |
| 10 | **Chuẩn bị gộp** (`chuan-bi-gop`): rebase `main`, đổi số migration nếu trùng, `make check` | Manager | |
| 11 | **Check cuối + cho gộp** (`cho-gop`): báo cáo QA + kết luận review + số test; Thư ký đọc log `check-<sha>.log` của Manager, chỉ chạy lại khi SHA lệch/log bất thường | Manager, Thư ký | ✅ **Cổng 5 + 6 gộp** (một lần duyệt). Rebase có xung đột lớn ⇒ tách lại hai cổng |
| 12 | **Xong** (`xong`): `merge --ff-only` vào `main`, push, `room done`, dọn worktree | Manager | |

## Sáu cổng duyệt

| Cổng | Anh duyệt | Manager trình |
|---|---|---|
| 1 | Gói phòng + hồ sơ tính năng | phạm vi, vai, chìa khoá app, `docs/features/<tên>.md` |
| 2 | Bản ý tưởng thiết kế | 3 ý tưởng, Manager đã chọn trước 1 + lý do; anh đồng ý hoặc chọn bản khác |
| 3 | Giao diện mẫu | `nghiem-thu.html` |
| 4 | Thiết kế Techlead | cột/bảng cụ thể (W8), ADR, thư viện mới |
| 5 | Check cuối | báo cáo QA + kết luận review |
| 6 | Cho gộp + push | log `make check` của Manager trên SHA cuối + Thư ký đối chiếu |

Duyệt (`ok`) ghi vào `gates` của phòng. Chọn khác (`sua` + ghi chú) ⇒ Manager sửa rồi trình lại; cổng chưa ghi.

## Cách anh trả lời — ở đâu cũng được

Manager hỏi **trong terminal của nó** rồi dừng lượt (Orca báo anh), đồng thời ghi câu hỏi lên board (`ask`).
Anh chọn một trong ba:

1. **Gõ thẳng trong terminal Manager.** Manager ghi câu trả lời lên board (`ask resolve --via terminal`) rồi làm tiếp.
2. **Bấm nút trên board** (cần board server): server ghi `via=board` rồi **tự gửi** ngay
   `Sếp trả lời <ID> (<tiêu đề>): <lựa chọn> — <ghi chú>` vào terminal Manager (gửi lỗi ⇒ sự kiện `forward_failed`, Thư ký chuyển tay). Không có server ⇒ nút chép câu
   `company.py ask resolve <ID> --choice <k> --via board`; anh dán vào terminal Manager.
3. **Nói với Thư ký** trong chat (ví dụ "ATTEND-a3 ok, nhớ thêm cột ghi chú"): Thư ký ghi `--via thu-ky` rồi chuyển.

Ai nhận câu trả lời thì ghi vào state trước, để board luôn khớp. Manager nhận trùng (board + Thư ký) thì tự bỏ qua.

## Vòng lỗi

QA `bug add` (bước tái hiện, ảnh, console) ⇒ thẻ lỗi trên board ⇒ Manager giao dev đúng mảng (`server`/`web`),
`fixing` ⇒ dev sửa, chuyển `retest` ⇒ QA chạy lại đúng tình huống ⇒ **chỉ QA được đóng** (`closed`); còn lỗi ⇒ `fixing`.
Lỗi cố ý không sửa trong phòng ⇒ Manager ghi backlog rồi đặt `deferred` ("Dời backlog", bắt buộc ghi chú trỏ tới dòng
backlog / commit) — thẻ thôi tính "chưa đóng" và rời "Việc của anh".
Lỗi cần quyết hành vi sản phẩm ⇒ `needsBoss` ⇒ lên "Việc của anh" kèm một câu hỏi `quyet`.

## Chìa khoá app

Mỗi lúc chỉ **một phòng** được chạy app thật (DB 5432, server 8080, web 5173). Board hiện ai giữ.
`company.py key request KEY` trước khi chạy, `key release KEY` ngay khi xong.
Phòng khác đang giữ ⇒ phòng xin **xếp hàng**; **Thư ký điều phối**: nhắn phòng đang giữ, phòng đó không cần nữa thì
nhả, và chìa khoá **tự chuyển** cho phòng đầu hàng, Thư ký báo phòng được nhận. Phòng giữ không trả lời ⇒ Thư ký báo
Sếp; chỉ Sếp quyết thu hồi.
Thiết kế, giao diện mẫu (`make lab`, 5174) và test (`make check`, Testcontainers) **không** cần chìa khoá.
⚠️ `make stop` giết theo port: phòng không giữ chìa khoá không được chạy nó.

## Gộp (sau cổng 5)

1. Manager rebase lên `main` mới nhất; migration trùng số ⇒ đổi file sang số kế tiếp (file chưa vào `main`, không phạm C10).
2. `make check > .scratch/<key>/check-<sha>.log` xanh ⇒ `room set --step cho-gop`, báo SHA + số test.
3. Thư ký đọc log đó, đối chiếu SHA với HEAD + worktree sạch, ghi `evidence`. Chỉ chạy lại khi lệch hoặc log bất thường; lệch ⇒ báo anh.
4. **Cổng 6** ⇒ `git merge --ff-only` vào `main`, push, `company.py room done KEY` (nhả chìa khoá, in lệnh dọn worktree).
5. Hai phòng cùng xong: phòng được bấm cổng 6 trước gộp trước. Phòng sau rebase lại; rebase cơ học (chỉ số
   migration/ADR, file máy sinh, hai phía cùng thêm dòng) + `make check` xanh ⇒ gộp luôn, không qua cổng 6 lần nữa
   (Sếp chốt 15/10). Xung đột đổi logic hoặc check đỏ ⇒ qua cổng 6 lại.

Trong nhánh phòng, Manager commit tự do. Gộp `main` và push luôn cần cổng 6.

## Đụng file giữa các phòng

Mỗi lần thức, Thư ký chạy `bin/overlap.sh`: so file đổi (`git diff main...<nhánh>`) giữa các phòng active, và
`git merge-tree` để biết gộp có xung đột thật không. Trùng file ⇒ ⚠️ trên cả hai thẻ. Xung đột thật ⇒ Thư ký báo
anh: phòng nào gộp trước, phòng kia rebase.

## Thư ký báo anh khi nào

Chỉ khi: có việc mới cho anh (câu hỏi, lỗi cần quyết), số Manager báo lệch số Thư ký chạy lại, xung đột gộp thật,
hoặc phòng xong. Báo bằng tiếng Việt: vấn đề → phương án → đề xuất. Không có gì đáng nói ⇒ một dòng.

## Lệnh hay dùng

```bash
# Anh chạy: bật board server + nhịp kiểm (heartbeat) nền nếu chưa chạy, rồi mở board
~/sportshub-company/bin/open-board.sh
open ~/sportshub-company/board.html              # không có server: board đọc data/board.js, reload để làm mới

# Thư ký / Manager
bin/open-room.sh KEY "Tiêu đề" ["ý tưởng"] [--dry-run]
bin/overlap.sh [--dry-run]
python3 bin/company.py room list [--all]          python3 bin/company.py room show KEY
python3 bin/company.py ask list --open            python3 bin/company.py ask resolve ID --choice ok --via thu-ky
python3 bin/company.py key status
python3 bin/company.py room done KEY              # in lệnh dọn worktree, không tự chạy
bin/wait-event.sh --timeout 14400 --types ask_opened,forward_failed,bug_opened,bug_changed,room_changed,room_done,key_requested,key_released,note,lane_stale,thu_ky_silent   # Thư ký chạy nền
bin/wait-event.sh --room KEY                      # Manager chạy nền
```

## Giới hạn đã biết

- **Nhịp dự phòng là `bin/heartbeat.py`** — script thường, không dùng AI, `open-board.sh` bật nền mỗi 15 phút
  (`state/heartbeat.pid`, log `state/heartbeat.log`). Lane `running` đứng yên quá 45 phút trong một phòng không ghi
  sự kiện nào ⇒ sự kiện `lane_stale`; không còn tiến trình watcher của Thư ký
  (`wait-event.sh` không lọc `--room`) quá 30 phút ⇒ `thu_ky_silent`. Không báo lặp (chỉ báo lại sau thêm một ngưỡng). Watcher của Thư ký thức vì hai loại này: đọc màn
  hình lane, kẹt thì nhắn Manager; im lặng thì xử lý sự kiện dồn. Giới hạn còn lại: nhịp kiểm chỉ thấy *dấu hiệu*
  (đứng yên, file cũ), không biết lane đang nghĩ lâu hay kẹt thật; Thư ký chết hẳn thì `thu_ky_silent` chỉ hiện trên
  board, không ai thức để xử lý tới khi anh mở lại phiên Thư ký. Nhịp kiểm chỉ chạy khi máy thức và đã chạy `open-board.sh`.
- Lane codex không đọc skill Claude: brief của lane phải chép sẵn khối luật cần (Git, W12, C-rule liên quan).
- `room done` chỉ in lệnh dọn worktree; kiểm `git status` và commit chưa push trước khi chạy.
- `open-room.sh` tạo worktree từ `main` ở máy: skill `phong-manager` và các skill `phong-*` phải đã nằm trên `main`.
- Board không server (file://) chỉ làm mới khi reload; nút trả lời thành chép-rồi-dán.
