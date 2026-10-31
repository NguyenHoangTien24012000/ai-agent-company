# Lane dev-server — phòng <KEY>: <tên tính năng>

Worktree: `<đường dẫn worktree>` · nhánh `phong/<key>` · hồ sơ phòng `.scratch/<key>/`
Model: codex. Bạn KHÔNG đọc được skill Claude — mọi luật cần thiết nằm trong file này.

**Bạn LÀ lane, không phải phiên điều phối.** Tự triển khai mọi việc trong brief này; KHÔNG mở phiên con, KHÔNG tách việc
sang lane cmux/Orca, kể cả khi file luật chung (`AGENTS.md`, `CLAUDE.md` toàn máy) bảo hãy tách việc nhiều file.

## Files You May Edit
- `server/src/main/java/com/sportshub/<mảng>/**`, `server/src/test/java/com/sportshub/<mảng>/**`
- `server/src/main/resources/db/migration/V<n>__<desc>.sql` (chỉ file mới, đúng tên Manager ghi: <…>)
- `docs/features/<tên>.md`, `docs/data/00-erd-hien-trang.md`, `docs/data/01-tu-dien-du-lieu.md`, `docs/reference/*` (chỉ qua script)
- `.scratch/<key>/reports/dev-server.md`
- <file khác Manager cho phép, ví dụ `SecurityConfig.java`>
Cần file khác ⇒ `## Blocked On`, không tự sửa.

## Đọc trước khi code (Codex: mở các file này như tài liệu)
- `.claude/skills/server-khuon/SKILL.md` — BẮT BUỘC: khuôn server thật của repo, thắng mọi tài liệu khác khi lệch.
- `.claude/skills/jpa-patterns/SKILL.md` — entity, N+1, giao dịch (đọc khối "⛔ ĐỌC KHỐI NÀY TRƯỚC" trước).
- Có migration: `.claude/skills/flyway-migrations/SKILL.md`. Đụng vị trí: `.claude/skills/postgis/SKILL.md`.
- Đường gọi mới, quyền, đăng nhập, tiền, tải file: `.claude/skills/springboot-security/SKILL.md` (đọc khối đầu trước), `docs/agents/bao-mat.md` mục "Soi kỹ".

## Quyết định của Sếp (chép NGUYÊN VĂN, kèm id — không tóm tắt)
<mỗi dòng: `<KEY>-aN: <nguyên văn>`>

## Problem
<việc lượt này: theo techlead.md mục …, hoặc "sửa lỗi <ID>: bước tái hiện …">
Đầu vào: `.scratch/<key>/techlead.md` (đã qua cổng 4 — làm ĐÚNG nó), `docs/features/<tên>.md`, `.scratch/<key>/qa-plan.md`.

## Hard rules (chép từ CLAUDE.md)
- **KHÔNG `git add`, KHÔNG `git commit`, KHÔNG push.** Lý do: Sếp duyệt mọi lần gộp; Manager gom đúng file bạn báo.
- **MUST write tests**: unit Service (Mockito) + integration Controller/Repository (Testcontainers) — C9. Không test = chưa xong.
- Thứ tự: Entity → Repository → Service → Controller → Test (W7). Sửa lỗi: test tái hiện ĐỎ trước, rồi sửa cho xanh.
- C1 không trả Entity từ Controller · C2/C20 Service không nhận/trả DTO, dùng `<Động từ><Danh từ>Command` trong `service/`
- C3 validation ở DTO request · C4 exception trong `<mảng>/exception/`, kế thừa `BusinessException`
- C5 `/api/v1/…` kebab-case số nhiều · C7 `@Transactional` ở Service · C8 SLF4J · C11 tiền là `BigDecimal`
- C10 không sửa `V*.sql` đã có trên `main` · C12 code tiếng Anh, comment tiếng Việt · C14 trả mã lỗi + `params`, không trả câu chữ
- C19 mảng chỉ giữ ID của mảng khác, gọi service công khai của nó, không gọi repository của nó; `ModularityTest` phải xanh.
- W8: không thêm dependency, cột, bảng ngoài `techlead.md`. Thiếu thì `## Blocked On`. Chỉ dùng thư viện khai trong
  `server/pom.xml` — thư viện chỉ có mặt vì gói khác kéo theo KHÔNG tính.
- Sửa code thì sửa docs cùng lượt: luật mới ⇒ "Luật luôn đúng" (chặn ở mấy chỗ, mã lỗi); migration/endpoint ⇒
  `python3 scripts/docs-gen.py`. KHÔNG sửa tay `docs/reference/*`.

## Acceptance Criteria
- [ ] `cd server && ./mvnw -B verify` xanh; hành vi mới/đổi có test ở tầng bắt được lỗi (không chạy theo chỉ tiêu số test)
- [ ] `python3 scripts/docs-check.py` xanh
- [ ] Mỗi "Luật luôn đúng" của lượt này có test chứng minh (ghi tên test)
Testcontainers cần Docker; sandbox chặn Docker ⇒ chạy phần test không cần DB, ghi rõ trong báo cáo để Manager chạy đủ.

## Before You Report Done
Viết `.scratch/<key>/reports/dev-server.md` (ghi đè bản cũ): danh sách ĐẦY ĐỦ file tạo/sửa, lệnh test + số tóm tắt,
chỗ còn nghi ngờ, `## Blocked On`. Dán `git status --porcelain`. Dòng CUỐI CÙNG đúng là:

LANE-DONE dev-server
