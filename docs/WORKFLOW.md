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

## Luồng một phòng

| # | Bước (`step` trên board) | Ai | Anh chạm? |
|---|---|---|---|
| 1 | Anh chat Thư ký **"mở phòng: <ý tưởng>"** ⇒ worktree `phong/<key>` từ `main`, chép `.env.local`, mở Manager, ghi board | Thư ký | |
| 2 | **Hỏi đáp** (`hoi-dap`): Manager hỏi để hiểu ý, rồi `grilling` chỗ chưa rõ ⇒ `.scratch/<key>/spec.md` + `docs/features/<tên>.md` | Manager ↔ anh | trả lời câu hỏi |
| 3 | **Gói phòng** (`cho-goi`): phạm vi, vai cần dùng, có cần chìa khoá app | Manager | ✅ **Cổng 1** |
| 4 | **Thiết kế** (`thiet-ke`) ‖ **Kiến trúc** (`kien-truc`) chạy song song | Designer, Techlead | ✅ **Cổng 2, 3, 4** |
| 5 | **Kế hoạch test** (`ke-hoach-test`) từ "Luật luôn đúng"; Manager duyệt | QA | |
| 6 | **Code** (`code`): dev server + dev web, test trong code | Dev | |
| 7 | **Test** (`test`): QA test app thật (giữ chìa khoá app) ⇒ vòng lỗi | QA ↔ Dev | chỉ lỗi cần quyết hành vi |
| 8 | **Review** (`review`): lane mới, sửa hết 🔴 | Review ↔ Dev | |
| 9 | **Check cuối** (`cho-check`): báo cáo QA + kết luận review nguyên văn | Manager | ✅ **Cổng 5** |
| 10 | **Chuẩn bị gộp** (`chuan-bi-gop`): rebase `main`, đổi số migration nếu trùng, `make check` | Manager | |
| 11 | **Chờ gộp** (`cho-gop`): Thư ký chạy lại `make check`, so số | Thư ký | ✅ **Cổng 6** |
| 12 | **Xong** (`xong`): `merge --ff-only` vào `main`, push, `room done`, dọn worktree | Manager | |

## Sáu cổng duyệt

| Cổng | Anh duyệt | Manager trình |
|---|---|---|
| 1 | Gói phòng + hồ sơ tính năng | phạm vi, vai, chìa khoá app, `docs/features/<tên>.md` |
| 2 | Bản ý tưởng thiết kế | 3 ý tưởng, Manager đã chọn trước 1 + lý do; anh đồng ý hoặc chọn bản khác |
| 3 | Giao diện mẫu | `nghiem-thu.html` |
| 4 | Thiết kế Techlead | cột/bảng cụ thể (W8), ADR, thư viện mới |
| 5 | Check cuối | báo cáo QA + kết luận review |
| 6 | Cho gộp + push | `make check` của Manager + số Thư ký chạy lại |

Duyệt (`ok`) ghi vào `gates` của phòng. Chọn khác (`sua` + ghi chú) ⇒ Manager sửa rồi trình lại; cổng chưa ghi.

## Cách anh trả lời — ở đâu cũng được

Manager hỏi **trong terminal của nó** rồi dừng lượt (Orca báo anh), đồng thời ghi câu hỏi lên board (`ask`).
Anh chọn một trong ba:

1. **Gõ thẳng trong terminal Manager.** Manager ghi câu trả lời lên board (`ask resolve --via terminal`) rồi làm tiếp.
2. **Bấm nút trên board** (cần board server): server ghi `via=board` ⇒ Thư ký thức ⇒ gửi
   `Sếp trả lời <ID> (<tiêu đề>): <lựa chọn> — <ghi chú>` vào terminal Manager. Không có server ⇒ nút chép câu
   `company.py ask resolve <ID> --choice <k> --via board`; anh dán vào terminal Manager.
3. **Nói với Thư ký** trong chat (ví dụ "ATTEND-a3 ok, nhớ thêm cột ghi chú"): Thư ký ghi `--via thu-ky` rồi chuyển.

Ai nhận câu trả lời thì ghi vào state trước, để board luôn khớp. Manager nhận trùng (board + Thư ký) thì tự bỏ qua.

## Vòng lỗi

QA `bug add` (bước tái hiện, ảnh, console) ⇒ thẻ lỗi trên board ⇒ Manager giao dev đúng mảng (`server`/`web`),
`fixing` ⇒ dev sửa, chuyển `retest` ⇒ QA chạy lại đúng tình huống ⇒ **chỉ QA được đóng** (`closed`); còn lỗi ⇒ `fixing`.
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
2. `make check` xanh ⇒ `room set --step cho-gop`, báo SHA + số test.
3. Thư ký tự chạy lại `make check` trên đúng SHA đó, ghi `evidence` (khớp / lệch). Lệch ⇒ báo anh.
4. **Cổng 6** ⇒ `git merge --ff-only` vào `main`, push, `company.py room done KEY` (nhả chìa khoá, in lệnh dọn worktree).
5. Hai phòng cùng xong: phòng được bấm cổng 6 trước gộp trước, phòng sau rebase lại và qua cổng 6 lần nữa.

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
# Anh chạy (một lần mỗi phiên làm việc, trong terminal Orca riêng) rồi mở http://127.0.0.1:8765
python3 ~/sportshub-company/bin/board-server.py
open ~/sportshub-company/board.html              # không có server: board đọc data/board.js, reload để làm mới

# Thư ký / Manager
bin/open-room.sh KEY "Tiêu đề" ["ý tưởng"] [--dry-run]
bin/overlap.sh [--dry-run]
python3 bin/company.py room list [--all]          python3 bin/company.py room show KEY
python3 bin/company.py ask list --open            python3 bin/company.py ask resolve ID --choice ok --via thu-ky
python3 bin/company.py key status
python3 bin/company.py room done KEY              # in lệnh dọn worktree, không tự chạy
bin/wait-event.sh --timeout 14400                 # Thư ký chạy nền, không lọc
bin/wait-event.sh --room KEY                      # Manager chạy nền
```

## Giới hạn đã biết

- **Thư ký không có nhịp dự phòng.** Chỉ thức khi có sự kiện (Sếp bấm board, Manager/QA ghi state). Lane treo mà
  không ghi gì thì Thư ký không biết; lớp canh còn lại là Orca báo terminal đứng yên.
- Lane codex không đọc skill Claude: brief của lane phải chép sẵn khối luật cần (Git, W12, C-rule liên quan).
- `room done` chỉ in lệnh dọn worktree; kiểm `git status` và commit chưa push trước khi chạy.
- `open-room.sh` tạo worktree từ `main` ở máy: skill `phong-manager` và các skill `phong-*` phải đã nằm trên `main`.
- Board không server (file://) chỉ làm mới khi reload; nút trả lời thành chép-rồi-dán.
- Thư ký chạy `make check` mất vài phút mỗi lần; trong lúc đó vẫn canh sự kiện song song.
