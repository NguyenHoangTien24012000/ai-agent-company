---
name: phong-review
description: Việc của lane Review trong một phòng của công ty agent SportsHub — một phiên MỚI (không phải lane Techlead) soi toàn bộ thay đổi của nhánh phòng theo `docs/architecture/03-luat-review.md` như subagent `reviewer`, đối chiếu thêm với `techlead.md` và spec, kết luận theo 🔴/🟡/⚪ vào `.scratch/<key>/review.md` cho cổng 5. Dùng khi brief lane review (`.scratch/<key>/briefs/review.md`) trỏ tới skill này. Chỉ đọc, không sửa code.
---

# Review phòng

Bạn đọc như người lạ: không viết code này, không thiết kế nó. Vì vậy phòng mở lane MỚI cho bạn.
Kết luận của bạn được Manager dán **nguyên văn** lên cổng 5 cho Sếp.

## Bắt đầu — giống subagent `reviewer`

Làm đúng mục "Bắt đầu" và "Khi soi" của `.claude/agents/reviewer.md`, với phạm vi là cả nhánh phòng:

```bash
git log --oneline main..HEAD
git diff main...HEAD --stat        # đã commit trên nhánh phòng
git status --porcelain             # cộng file chưa commit
git diff HEAD --stat
```

1. Đọc TOÀN BỘ `docs/architecture/03-luat-review.md` — bộ luật duy nhất; H1–H7 đè mọi thói quen review chung.
2. `CLAUDE.md`: "Convention bắt buộc" (C1–C24) và bảng "sửa code thì sửa docs".
3. Mỗi mảng diff chạm tới ⇒ `docs/features/<tên>.md` mục "Luật luôn đúng".
4. **Thêm so với reviewer**: `.scratch/<key>/techlead.md` (thiết kế đã qua cổng 4) và `.scratch/<key>/spec.md`.
5. Số test: đọc `.scratch/<key>/reports/dev-*.md` và `qa.md`; không tự chạy `mvnw`/`npm`.

Bash chỉ để đọc (`git diff/log/show`, `grep`, `wc`). Không sửa file nào ngoài `review.md` và báo cáo lane.

## Đối chiếu techlead.md + spec

Mỗi mục sau lệch là một lỗi, xếp mức theo luật review (sai nghiệp vụ / mất dữ liệu ⇒ 🔴):
- Bảng/cột trong migration khớp `techlead.md` (kiểu, NULL, ràng buộc). Có cột/bảng/thư viện KHÔNG có trong
  `techlead.md` ⇒ 🔴 (vượt cổng 4, luật W8).
- Endpoint và mã lỗi khớp; endpoint công khai có trong `SecurityConfig` và bảng đường công khai.
- Mỗi luật ở mục "Luật luôn đúng → chặn ở đâu → test nào" thật sự chặn ở đúng chỗ đã ghi, và có đúng test đó.
- Việc spec ghi "cố ý không làm" mà code lại làm ⇒ lỗi phạm vi (W7).

## Soát bảo mật — phòng nào cũng làm (Sếp chốt 31/10)

Đọc `docs/agents/bao-mat.md` rồi `.claude/skills/security-audit/SKILL.md`, dùng **chế độ hướng dẫn** trên diff của phòng: không chạy
đủ sáu giai đoạn, không tạo thư mục báo cáo, không chạy code. Mở thêm tài liệu kèm theo đúng phần diff chạm: `ATTACK-CLASSES.md`
(luôn), `WEB-PROTOCOL-AND-AUTH.md` (đường gọi server, đăng nhập, quyền), `DATA-ISOLATION-AND-LIFECYCLE.md` (dữ liệu giữa các đội, xoá,
ảnh), `CLIENT-SIDE.md` (web). Phòng chỉ đổi giao diện ⇒ vẫn soi lộ dữ liệu trên màn, link ngoài, nội dung chèn HTML.
Mỗi nghi ngờ tự kiểm lại trên code (H2). Báo theo `BM1`; lỗi kèm: ai bị hại, mất gì, đường đi trong code.

## Trả về — `.scratch/<key>/review.md`

Đúng "Hình dạng báo cáo" của luật review, tiếng Việt:

```
KẾT LUẬN: 🔴 n · 🟡 n · ⚪ n → ĐƯỢC COMMIT | CHƯA ĐƯỢC COMMIT     (còn 🔴 là chưa)
Phạm vi: <commit đầu>..<HEAD> + <n> file chưa commit · vòng <n>

🔴 <mã luật>  <file:dòng>
   <lỗi gì>
   Hỏng khi: <tình huống cụ thể>
   Sửa: <thế nào>   · Giao: dev-server | dev-web
…
## Đối chiếu techlead.md + spec
<khớp / lệch từng mục ở trên>
## Bảo mật
<đã soi những ranh giới nào; phát hiện nằm ở danh sách lỗi trên, mã BM1>

ĐÃ SOI MÀ KHÔNG THẤY LỖI: <nhóm luật đã soi và sạch; nhóm bỏ qua vì diff không chạm>
LUẬT CẦN CHỦ NHÂN XEM LẠI: <chỉ khi luật mơ hồ hay đánh nhau — không tự quyết>
```

- Mỗi lỗi ghi `Giao:` vai dev để Manager chuyển thẳng.
- ⚪ tối đa 3 mục. Không báo "Nợ đã biết" trừ khi diff làm nó nặng thêm (H6).
- Thuật ngữ kèm `()` giải thích theo bảng thuật ngữ cuối `CLAUDE.md` — Sếp đọc bản này.
- Vòng ≥ 2: đầu file liệt kê từng 🔴 vòng trước ⇒ đã sửa đúng / chưa; rồi soi phần diff mới như bình thường.

Xong: báo cáo lane `.scratch/<key>/reports/review.md` (chép dòng KẾT LUẬN), dòng cuối `LANE-DONE review`.
