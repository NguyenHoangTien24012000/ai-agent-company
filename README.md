# Công ty agent cho SportsHub

Một "công ty" gồm nhiều phiên AI (Claude Code và Codex) cùng làm một dự án phần mềm. Mỗi tính năng là một **phòng**:
một git worktree riêng, nhánh `phong/<key>`, có Manager và các nhân viên. Người dùng là **Sếp**: chỉ trả lời câu hỏi và
duyệt ở 6 cổng, không phải điều phối tay. Dự án thật đi kèm là SportsHub (Java Spring Boot + React).

Đây là bản tham khảo: đường dẫn máy (`/Users/tien/...`), tên container và cổng đang cắm theo máy của tác giả.

## Vai

| Vai | Model | Làm gì |
|---|---|---|
| Sếp | người | Quyết phạm vi, duyệt 6 cổng, trả lời trên board |
| Thư ký | Claude Opus | Mở phòng, điều phối chéo phòng, kiểm số Manager báo, báo đụng file, chia chìa khoá app |
| Manager | Claude Opus | Hỏi Sếp bằng câu có phương án, chia lane, quản lỗi, gộp vào `main` sau cổng 6 |
| Techlead | Claude Opus | Bảng, cột, API, ADR |
| Designer | Claude Opus (+ Codex vẽ ảnh) | 3 ý tưởng → giao diện mẫu → trang nghiệm thu |
| dev-server / dev-web | Codex | Code + test trong code |
| QA | Claude Sonnet + Playwright | Kế hoạch test trước khi code, test app thật, báo lỗi (không sửa) |
| Review | lane mới | Soi cả nhánh theo bộ luật review của dự án |

## Luồng một phòng — 6 cổng

`hỏi đáp → gói phòng (cổng 1) → thiết kế (cổng 2 ý tưởng, cổng 3 giao diện mẫu) ‖ kiến trúc (cổng 4)
→ kế hoạch test → code → test → review → check cuối (cổng 5) → chuẩn bị gộp → cho gộp + push (cổng 6)`

Im lặng không bao giờ là đồng ý. Chi tiết: [`docs/WORKFLOW.md`](docs/WORKFLOW.md). Định dạng state và CLI:
[`docs/CONTRACT.md`](docs/CONTRACT.md).

## Thành phần

| Đường dẫn | Là gì |
|---|---|
| `bin/company.py` | CLI duy nhất được ghi state: phòng, câu hỏi (`ask`), lỗi (`bug`), lane, chìa khoá app, bằng chứng |
| `bin/board-server.py` + `board.html` | Board trên localhost; Sếp bấm trả lời, server tự gửi câu trả lời vào terminal Manager |
| `bin/wait-event.sh` | Chờ sự kiện mới (lọc theo phòng/loại) — Thư ký và Manager chỉ thức khi có việc |
| `bin/open-room.sh` | Mở phòng: worktree + nhánh + terminal Manager (dùng Orca CLI) |
| `bin/overlap.sh` | So file đổi giữa các phòng, báo xung đột gộp thật bằng `git merge-tree` |
| `skills/thu-ky/` | Skill của Thư ký |
| `skills/nghien-cuu/` | Bước 0 do Thư ký chạy: nghiên cứu ý tưởng lớn → báo cáo HTML → đầu vào cổng 1 |
| `skills/rooms/` | Bản chép skill của Manager, Techlead, QA, Review và brief mẫu từng vai (gốc nằm trong repo SportsHub) |
| `tests/` | Test CLI, server, open-room (`python3 -m unittest`, `bash tests/test_open_room.sh`) |

## Bài học từ lần chạy thử 6 phòng cùng lúc

- Câu hỏi cho Sếp phải có 2–4 phương án + một ô "Khác"; câu hỏi mở bắt Sếp gõ dài làm chậm cả công ty.
- Chuyển câu trả lời bằng máy (board tự gửi) thay vì một phiên AI thức dậy chỉ để chuyển tin.
- Chạy app thật cho QA: mỗi phòng một cơ sở dữ liệu riêng, mỗi lúc một phòng giữ "chìa khoá app"; không dùng lệnh
  tắt theo cổng hay `docker compose` trong worktree (tắt nhầm app và DB của người khác).
- Lane Codex phải được nói rõ "bạn là lane, không phải phiên điều phối", nếu không nó làm theo luật tách việc toàn máy.
- Việc chung của nhiều phòng (một interface dùng chung, tên sự kiện) phải giao đúng một phòng làm, phòng gộp trước.
