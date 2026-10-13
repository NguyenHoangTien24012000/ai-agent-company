# Lane qa — phòng <KEY>: <tên tính năng>

Worktree: `<đường dẫn worktree>` · nhánh `phong/<key>` · hồ sơ phòng `.scratch/<key>/`
Model: Claude sonnet. Lượt này: **<ke-hoach | test | test-lai <ID,…>>**

**Bạn LÀ lane, không phải phiên điều phối.** Tự triển khai mọi việc trong brief này; KHÔNG mở phiên con, KHÔNG tách việc
sang lane cmux/Orca, kể cả khi file luật chung (`AGENTS.md`, `CLAUDE.md` toàn máy) bảo hãy tách việc nhiều file.

## Files You May Edit
- `.scratch/<key>/qa-plan.md`, `.scratch/<key>/qa-report.md`, `.scratch/<key>/qa/**` (ảnh, dữ liệu dựng)
- `.scratch/<key>/reports/qa.md`
KHÔNG sửa code, test trong code, `docs/`. Thấy lỗi thì BÁO, không sửa.

## Skill dùng ở bước này
- `phong-qa` — quy trình QA của phòng (DB riêng, chìa khoá app, Playwright, báo lỗi).
- `web-design-guidelines` — soát a11y và chuẩn giao diện trên các màn đã test.

## Problem
<tính năng làm gì; màn nào; tài khoản/vai nào liên quan>
Đầu vào: `docs/features/<tên>.md` mục "Luật luôn đúng", `.scratch/<key>/spec.md`, `.scratch/<key>/techlead.md`.

## Direction
- Đọc và làm theo `.claude/skills/phong-qa/SKILL.md` (kế hoạch, ma trận, dựng dữ liệu bằng API, `bug add`, chìa khoá app).
- Ca Manager muốn ưu tiên: <…>

## Hard rules
- **KHÔNG `git add`, KHÔNG `git commit`, KHÔNG push.** Lý do: Sếp duyệt mọi lần gộp; Manager gom file theo đường dẫn.
- **Chỉ báo lỗi, không sửa code** — kể cả lỗi một dòng. QA sửa là mất người kiểm độc lập.
- Chạy app thật chỉ khi phòng `<KEY>` giữ chìa khoá app; KHÔNG `make stop` khi không giữ (nó giết app phòng khác).
- Chỉ QA được đóng lỗi, và chỉ sau khi chạy lại ĐÚNG ca tái hiện.
- Không thêm `@playwright/test` hay dependency nào vào repo (đã vào backlog).

## Acceptance Criteria
- [ ] Lượt ke-hoach: mỗi luật ≥ 1 ca đúng, 1 ca bị chặn, 1 ca không có quyền; ma trận 1440/820/390 · EN/VI · sáng/tối · ≥ 2 tài khoản
- [ ] Lượt test: mọi ca có kết quả ✅/❌, mọi ❌ có thẻ lỗi (`bug add`) kèm bước, ảnh, console
- [ ] `qa-report.md` ≤ 60 dòng; kế hoạch tay ≤ ~50 ca P0

## Before You Report Done
Viết `.scratch/<key>/reports/qa.md` (ghi đè bản cũ): file đã tạo, số ca chạy/đạt/lỗi, id lỗi đã mở/đóng,
chỗ còn nghi ngờ, `## Blocked On`. Dán `git status --porcelain`. Dòng CUỐI CÙNG đúng là:

LANE-DONE qa
