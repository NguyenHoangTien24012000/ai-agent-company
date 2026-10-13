# Lane designer — phòng <KEY>: <tên màn/khu>

Worktree: `<đường dẫn worktree>` · nhánh `phong/<key>` · hồ sơ phòng `.scratch/<key>/`
Người giao việc: **Manager** của phòng (không phải Sếp). Lượt này: **<y-tuong | anh-tach-lop+code | sua-theo-feedback>**

**Bạn LÀ lane, không phải phiên điều phối.** Tự triển khai mọi việc trong brief này; KHÔNG mở phiên con, KHÔNG tách việc
sang lane cmux/Orca, kể cả khi file luật chung (`AGENTS.md`, `CLAUDE.md` toàn máy) bảo hãy tách việc nhiều file.

## Files You May Edit
- `.impeccable/mocks/<đợt>/**`, `.impeccable/review/**` (trong worktree này)
- `web/src/lab/<khu>/**`, `web/src/assets/<…>/**`, `web/src/locales/{en,vi}/<…>.json` (chỉ khi lượt có code)
- `.scratch/<key>/reports/designer.md`
Cần file khác ⇒ ghi vào báo cáo mục `## Blocked On`, không tự sửa.

## Skill dùng ở bước này
- `thiet-ke-man` — quy trình thiết kế màn (ý tưởng → lab → nghiệm thu), cùng plugin `impeccable`.
- `web-khuon` — giới hạn khi dựng lab: component dùng chung, màu theo vai trò, i18n.
- `web-design-guidelines` — tự soát a11y trước khi trình cổng 3.

## Problem
<2–4 câu: màn này giải nỗi đau gì, ai dùng — chép từ docs/features/<tên>.md mục "Việc nó giải">

## Direction
- Đọc `.claude/skills/thiet-ke-man/SKILL.md`, làm đúng quy trình, và mục **"Khi chạy trong phòng"** của nó.
- Nội dung thật của màn: <tên người Việt, số liệu giả, các trạng thái cần vẽ>
- Bố cục phải giữ: <…> · Ảnh/khu tham chiếu: <…>
- Ba môn (bóng đá, pickleball, cầu lông): chữ và hình trung lập, không chỉ bóng đá.
- Bước ảnh dùng lane codex `image_gen` như skill nói (tự mở bằng Orca trong CHÍNH worktree này, `cd <worktree>`).

## Hard rules (chép từ CLAUDE.md — lane không được bỏ)
- **KHÔNG `git add`, KHÔNG `git commit`, KHÔNG push.** Lý do: Sếp duyệt mọi lần gộp; nhiều lane chung một worktree,
  Manager gom đúng file từng lane báo — lane tự commit là trộn việc của người khác vào commit của mình.
- **Lượt y-tuong dừng sau bước 1 của thiet-ke-man**: báo cáo 3 hướng + khuyến nghị, KHÔNG làm tiếp. Manager chọn rồi giao lượt sau.
- Code lab: chữ qua `t()`, viết `locales/en/` trước rồi `vi/` (C13); `components/` không gọi `useTranslation` (C15);
  màu theo vai trò (`--primary`…, C16); `features/` không import chéo (`npm run check:arch`).
- MUST write tests cho component/hook có logic (Vitest, đặt cạnh file `*.test.tsx`).
- Thiết kế cả ba cỡ 1440 / 820 / 390; chữ nhỏ, dày thông tin (luật mật độ trong thiet-ke-man).

## Acceptance Criteria
- [ ] Lượt y-tuong: 3 hướng × (desktop + mobile), `comparison.html` mở được, khuyến nghị có lý do
- [ ] Lượt code: `cd web && npm run format:check && npm run lint && npm run check:arch && npm test && npm run build` xanh
- [ ] Lượt cuối: `.impeccable/review/nghiem-thu.html` đủ concept ↔ bản cuối ở 3 cỡ

## Before You Report Done
Viết `.scratch/<key>/reports/designer.md` (ghi đè bản cũ): danh sách ĐẦY ĐỦ file tạo/sửa, lệnh đã chạy + số tóm tắt,
đường dẫn ảnh/trang cần Manager xem, chỗ còn nghi ngờ, `## Blocked On` nếu có.
Dán `git status --porcelain`. Dòng CUỐI CÙNG đúng là:

LANE-DONE designer
