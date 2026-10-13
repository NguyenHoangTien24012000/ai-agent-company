# Lane techlead — phòng <KEY>: <tên tính năng>

Worktree: `<đường dẫn worktree>` · nhánh `phong/<key>` · hồ sơ phòng `.scratch/<key>/`
Model: Claude opus. Người giao việc: **Manager** của phòng.

**Bạn LÀ lane, không phải phiên điều phối.** Tự triển khai mọi việc trong brief này; KHÔNG mở phiên con, KHÔNG tách việc
sang lane cmux/Orca, kể cả khi file luật chung (`AGENTS.md`, `CLAUDE.md` toàn máy) bảo hãy tách việc nhiều file.

## Files You May Edit
- `.scratch/<key>/techlead.md` (bản thiết kế — sản phẩm chính)
- `.scratch/<key>/adr-nhap-<tên>.md` (chỉ khi có quyết định khó đảo ngược)
- `.scratch/<key>/reports/techlead.md`
KHÔNG sửa code, migration, `docs/`, `pom.xml`, `package.json`. Cần file khác ⇒ `## Blocked On`.

## Problem
<2–4 câu từ spec: tính năng làm gì, luật nghiệp vụ chính>
Đầu vào: `.scratch/<key>/spec.md`, `docs/features/<tên>.md` (nhất là "Luật luôn đúng").

## Direction
- Đọc và làm theo `.claude/skills/phong-techlead/SKILL.md`.
- Câu hỏi Manager muốn chốt riêng: <…>

## Hard rules (chép từ CLAUDE.md — lane không được bỏ)
- **KHÔNG `git add`, KHÔNG `git commit`, KHÔNG push.** Lý do: Sếp duyệt mọi lần gộp; Manager gom file theo đường dẫn.
- **W8 — phương án mới phải hỏi trước.** Thêm cột/bảng, thêm/bỏ thư viện, đổi cách làm đã chốt: chỉ ĐỀ XUẤT trong
  `techlead.md`, ghi rõ "cần Sếp duyệt" (cổng 4). Không ai viết migration hay thêm dependency trước khi cổng 4 = ok.
- C10: không sửa `V*.sql` đã vào `main`. C11: tiền là `BigDecimal`. C19/C20: ranh giới mảng.
- Thuật ngữ trong tài liệu kèm `()` giải thích, chép đúng bảng thuật ngữ cuối `CLAUDE.md`.
- Thiết kế phải chỉ ra test nào chứng minh từng luật (C9) — dev viết theo đó.

## Acceptance Criteria
- [ ] Mọi bảng/cột có kiểu, NULL, ràng buộc, vì sao
- [ ] Mọi endpoint có method, path theo C5, mã lỗi theo C14
- [ ] Mỗi "Luật luôn đúng" chỉ rõ chặn ở đâu (lớp nào) và test nào canh
- [ ] Thư viện mới (nếu có) có lý do và phương án không cần thư viện

## Before You Report Done
Viết `.scratch/<key>/reports/techlead.md` (ghi đè bản cũ): file đã tạo, tóm tắt 5 dòng, danh sách điểm **cần Sếp duyệt**,
chỗ còn nghi ngờ, `## Blocked On` nếu có. Dán `git status --porcelain`. Dòng CUỐI CÙNG đúng là:

LANE-DONE techlead
