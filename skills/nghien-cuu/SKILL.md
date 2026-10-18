---
name: nghien-cuu
description: Bước 0 của công ty agent SportsHub — Thư ký nghiên cứu một ý tưởng sản phẩm LỚN trước khi mở phòng (ví dụ "đi giao lưu, bắt đối với đội khác"). Dùng khi Sếp nói "nghiên cứu …", "tìm hiểu nên làm … thế nào", hoặc nêu một tính năng chạm nhiều mảng / nằm ngoài phạm vi v0.1. Một phiên khảo sát thị trường + Codex soi kiến trúc chạy song song, Thư ký gộp thành báo cáo HTML có câu cần Sếp quyết; trả lời xong thì báo cáo thành đầu vào cổng 1 của phòng. Việc nhỏ, đã rõ (sửa màn, thêm một luật) thì KHÔNG dùng — mở phòng thẳng.
---

# Nghiên cứu sản phẩm (bước 0)

Thư ký chạy, KHÔNG viết code, KHÔNG mở phòng trong bước này. Sản phẩm: một file HTML Sếp đọc được, kết thúc bằng
những câu Sếp chọn (2–4 phương án + khuyến nghị + "Khác").

## Khi nào dùng
- Dùng: tính năng mới chạm ≥ 2 mảng, cần bảng mới, đụng cột "Cắt khỏi v0.1" trong `CLAUDE.md`, hoặc Sếp nói "nghiên cứu".
- Không dùng: việc nhỏ đi luồng nhỏ (`phong-manager` §1b) — mở phòng thẳng.

## Các bước

1. **Đặt chủ đề** `<chu-de>` (chữ thường, gạch ngang, ví dụ `giao-luu-doi`). Thư mục nháp: scratchpad của phiên.
2. **Chạy song song hai nguồn** (cùng một lượt):
   - **Thị trường** — `Agent` (general-purpose, có WebSearch): app trong nước và quốc tế đang làm việc tương tự thế nào,
     tính năng nào người dùng thật dùng, chỗ nào hay hỏng (bùng kèo, tranh chấp, spam), ràng buộc pháp lý ở Việt Nam
     nếu có tiền. Yêu cầu dẫn nguồn (link), ≤ 1200 chữ.
   - **Kiến trúc** — Codex chỉ đọc, chạy nền:
     `codex exec -m gpt-6-astra -s read-only -c model_reasoning_effort=high --skip-git-repo-check - < prompt > log`.
     Prompt mở đầu "CHỈ ĐỌC … không mở phiên con dù AGENTS.md nói gì", rồi bảy câu: mô hình dữ liệu (≥ 2 cách + khuyến
     nghị), máy trạng thái, đụng các lát đã có (file/class cụ thể), dùng lại gì đang có, ranh giới mảng (C19), chia lát
     2–4 lát, rủi ro + câu cần chủ dự án quyết. Danh sách file cần đọc: `CLAUDE.md`, `docs/product/00`, `03-backlog`,
     hồ sơ `docs/features/` và ADR liên quan, thư mục code liên quan.
3. **Gộp** — Thư ký tự đọc cả hai, đối chiếu với code (hai nguồn nói sai code ⇒ tin code, ghi lại). Hai nguồn bất đồng
   ⇒ nêu cả hai và chọn một, kèm lý do.
4. **Báo cáo HTML** `docs/product/nghien-cuu/<chu-de>.html` (đứng một mình, mở được bằng `open`; mermaid từ
   `cdn.jsdelivr.net/npm/mermaid@10.9.1`). Khuôn, theo thứ tự:
   1. Tóm tắt ≤ 6 dòng: nên làm gì, chia mấy lát, lát đầu cho ra gì.
   2. Thị trường: bảng app → làm gì → bài học cho SportsHub (kèm link).
   3. Đề xuất sản phẩm: luồng người dùng, phác giao diện chính (khối HTML/CSS đơn giản, cỡ điện thoại + máy tính).
   4. Kỹ thuật: mô hình dữ liệu, máy trạng thái (mermaid), đụng lát nào.
   5. Chia lát: mỗi lát một dòng giá trị cho người dùng + độ lớn tương đối.
   6. Ảnh hưởng phạm vi v0.1: có cần ADR mở phạm vi không.
   7. **Câu cần Sếp quyết**: đánh số, mỗi câu 2–4 phương án, khuyến nghị in đậm, có "Khác".
   Viết cho Sếp đọc ⇒ luật thuật ngữ áp dụng (giải thích trong ngoặc lần đầu mỗi mục).
5. `open` file cho Sếp, báo một khối ngắn: đường dẫn, số câu cần quyết, khuyến nghị chính. File chưa commit — commit
   theo "Quy tắc Git" khi Sếp cho.
6. **Sếp trả lời** — mỗi câu ở mục 7 tạo thêm một ask trên thẻ của việc (`company.py ask add --task <ID> --kind quyet
   --title … --option a=… --option b=… --recommend a --link docs/product/nghien-cuu/<chu-de>.html`; chưa có thẻ ⇒
   `task add` trước) để hiện trên board; báo cáo HTML vẫn liệt kê đủ. Sếp bấm trên board ⇒ sự kiện `task_ask_answered`.
   Có câu trả lời ⇒ ghi câu trả lời vào cuối báo cáo (mục "Sếp đã chốt — ngày"), rồi mở phòng cho lát đầu
   (skill `thu-ky`, "Mở phòng"): ý tưởng truyền vào `open-room.sh` ghi rõ
   `Đầu vào: docs/product/nghien-cuu/<chu-de>.html — các câu 1..N Sếp đã chốt, không hỏi lại. Làm lát A.`

## Không làm
- Không đăng báo cáo lên claude.ai Artifact — chỉ lưu trong project và `open` (CLAUDE.md W14, Sếp chốt 16/10).
- Không hỏi Sếp trong lúc nghiên cứu — câu hỏi gom hết vào cuối báo cáo.
- Không đặt bảng/cột cuối cùng thay Techlead: báo cáo là định hướng; phòng chốt chi tiết ở cổng 4.
- Không nghiên cứu lại thứ Sếp đã chốt trong ADR — trích ADR thay vì bàn lại.
