# Lane review — phòng <KEY>: <tên tính năng>

Worktree: `<đường dẫn worktree>` · nhánh `phong/<key>` · hồ sơ phòng `.scratch/<key>/`
Model: Claude opus. Lane MỚI — bạn không viết code này và không thiết kế nó. Vòng review thứ: <1 | 2 | …>

**Bạn LÀ lane, không phải phiên điều phối.** Tự triển khai mọi việc trong brief này; KHÔNG mở phiên con, KHÔNG tách việc
sang lane cmux/Orca, kể cả khi file luật chung (`AGENTS.md`, `CLAUDE.md` toàn máy) bảo hãy tách việc nhiều file.

## Files You May Edit
- `.scratch/<key>/review.md`
- `.scratch/<key>/reports/review.md`
Chỉ đọc mọi thứ khác. Không sửa code, không chạy `git add/commit/checkout/reset/stash`.

## Skill dùng ở bước này (Codex: mở như tài liệu)
- Bộ luật `docs/architecture/03-luat-review.md` + `.claude/agents/reviewer.md` — nguồn chính, luôn đọc.
- Khuôn để so: `.claude/skills/server-khuon/SKILL.md`, `.claude/skills/web-khuon/SKILL.md`.
- Java: `.claude/skills/java-review-patterns/SKILL.md`. Có migration: `.claude/skills/flyway-migrations/SKILL.md`.
- Đụng đăng nhập/quyền: `.claude/skills/springboot-security/SKILL.md`, `.claude/skills/security-reviewer/SKILL.md`.

## Problem
Soi toàn bộ thay đổi của phòng: `git diff main...HEAD` + `git status --porcelain` (gồm file chưa commit).
<Vòng ≥ 2: những 🔴 vòng trước — kiểm đã sửa đúng chưa, và soi lại phần diff mới>

## Direction
- Đọc và làm theo `.claude/skills/phong-review/SKILL.md`.
- Chỗ Manager lo nhất: <…>

## Hard rules
- **KHÔNG `git add`, KHÔNG `git commit`, KHÔNG push.** Lý do: Sếp duyệt mọi lần gộp; review chỉ đọc.
- Áp đúng `docs/architecture/03-luat-review.md`, luật hiệu chỉnh H1–H7 đè mọi thói quen review chung.
- Mỗi nghi ngờ tự kiểm lại trước khi báo (H2). Không đề xuất thư viện/việc ngoài diff (H5).
- Không chạy `mvnw`/`npm` — Manager chạy test rồi; bạn đọc số trong `.scratch/<key>/reports/`.
- Kiểm cả: code có làm đúng `.scratch/<key>/techlead.md` (đã qua cổng 4) và spec không — lệch là lỗi.
- MUST check tests: mỗi "Luật luôn đúng" có test chứng minh (nhóm 5 của luật review).

## Acceptance Criteria
- [ ] `review.md` đúng "Hình dạng báo cáo": dòng KẾT LUẬN đầu, mỗi lỗi có mã luật, `file:dòng`, hỏng khi nào, sửa thế nào
- [ ] Có mục đối chiếu techlead.md + spec
- [ ] Dòng `ĐÃ SOI MÀ KHÔNG THẤY LỖI: …`

## Before You Report Done
Viết `.scratch/<key>/reports/review.md` (ghi đè bản cũ): dòng KẾT LUẬN chép y nguyên, số lỗi theo mức, chỗ còn nghi ngờ,
`## Blocked On`. Dán `git status --porcelain`. Dòng CUỐI CÙNG đúng là:

LANE-DONE review
