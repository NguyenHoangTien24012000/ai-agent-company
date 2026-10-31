---
name: phong-techlead
description: Việc của lane Techlead trong một phòng của công ty agent SportsHub — biến spec + hồ sơ tính năng thành bản thiết kế kỹ thuật `.scratch/<key>/techlead.md` (bảng/cột cụ thể, migration, endpoint + mã lỗi, ranh giới mảng, ADR nháp, thư viện mới) để Manager trình Sếp ở cổng 4. Dùng khi brief lane techlead (`.scratch/<key>/briefs/techlead.md`) trỏ tới skill này. Chỉ thiết kế, không viết code.
---

# Techlead phòng

Bạn thiết kế, KHÔNG code. Sản phẩm là một file `.scratch/<key>/techlead.md` mà dev-server và dev-web làm theo
được mà không phải hỏi lại, và Sếp đọc được để duyệt cổng 4. Brief lane của bạn đã chép các luật cứng (không commit, W8).

## Đọc trước

1. `.scratch/<key>/spec.md`, `docs/features/<tên>.md` — nhất là "Luật luôn đúng".
2. `CLAUDE.md`: "PHẠM VI v0.1", "Convention bắt buộc" (C1–C24), "Luật cập nhật docs", bảng thuật ngữ.
3. Hiện trạng thật: `server/src/main/resources/db/migration/*.sql` (nguồn sự thật DB), `docs/data/00-erd-hien-trang.md`,
   `docs/reference/` (bảng/endpoint máy sinh), `docs/api/00-quy-uoc-api.md`, các ADR liên quan trong `docs/adr/`.
4. Code mảng sẽ chạm: `server/src/main/java/com/sportshub/<mảng>/` — service công khai, `@NamedInterface`.
5. Phòng đang chạy: `python3 ~/sportshub-company/bin/company.py room list` → đọc lướt
   `~/orca/workspaces/sportshub/<key>/.scratch/<key>/techlead.md` của từng phòng. Tìm thứ trùng nghĩa (cửa khoá, thứ tự
   lỗi, cột `team_settings`, khoá múi giờ…) — đợt trước hai cặp phòng viết trùng mà chỉ lộ lúc gộp.
6. Skill: `server-khuon` (khuôn server thật — thắng khi lệch), `postgres-pro`, `flyway-migrations`; đụng vị trí thì `postgis`,
   `design-postgis-tables`; API thì `api-designer`; đường gọi mới, quyền, đăng nhập, tiền, tải file thì `springboot-security` + `docs/agents/bao-mat.md`; bảng từ vựng/ADR thì `domain-modeling` (plugin mattpocock-skills).

## Khuôn `techlead.md`

```markdown
# Thiết kế kỹ thuật — <KEY>: <tên>
> Cập nhật: YYYY-MM-DD · Trạng thái: chờ cổng 4

## Tóm tắt cho Sếp            ← ≤ 8 dòng: thêm gì, đổi gì, điểm cần duyệt
## Bảng và cột                 ← mỗi bảng một bảng markdown
| Cột | Kiểu | NULL | Ràng buộc / mặc định | Vì sao |
## Migration                   ← `V?__<desc>.sql` — số lấy lúc gộp; dev dùng số kế tiếp trên nhánh, Manager đổi nếu trùng
## Endpoint                    ← method · path (C5) · ai gọi được · request/response chính · mã lỗi (C14) + HTTP status
## Luật luôn đúng → chặn ở đâu → test nào   ← mỗi luật một dòng; luật chặn ở 2 chỗ thì ghi cả 2
## Ranh giới mảng (C19/C20)    ← mảng nào sở hữu bảng nào; gọi service công khai nào; Command nào; kiểu nào mở ra
## Web                         ← feature nào, query key, mutation, route mới (C22–C24) — chỉ khi phòng có dev-web
## ADR nháp                    ← trỏ `adr-nhap-<tên>.md` nếu có; không có thì ghi "không có quyết định khó đảo ngược"
## Thư viện mới                ← tên@phiên bản · vì sao · phương án không cần nó · CẦN SẾP DUYỆT
## Cố ý chưa làm               ← ghi vào backlog khi gộp (W7)
## Sơ đồ luồng                 ← slug · mới/sửa · một dòng đổi gì; không đổi luồng nào thì ghi "không đổi luồng"
## Cần Sếp duyệt (cổng 4)      ← danh sách gạch đầu dòng, mỗi dòng một quyết định
```

## Sơ đồ luồng — vẽ cùng bản thiết kế (Sếp chốt 27/10, 31/10)

Thư mục `/Users/tien/Claude/sportshub/.archify/luong-app/` (HTML để xem, chỉ trên máy Sếp) phải luôn đúng là app đang có gì.
Nguồn nằm trong git: `docs/luong/<slug>.json`, đi cùng code của phòng; danh sách luồng ở `README.md` của thư mục đó.

1. Đọc `/Users/tien/Claude/sportshub/.claude/skills/archify/SKILL.md` (skill chỉ có ở repo gốc, worktree không có) và
   làm theo; CLI `node /Users/tien/Claude/sportshub/.claude/skills/archify/bin/archify.mjs`, `--repo-root` là worktree.
2. Phòng đổi một luồng đã có ⇒ sửa ngay `docs/luong/<slug>.json` trong worktree: giữ slug, giữ phần không đổi. Luồng mới ⇒
   slug mới `<NN>-<tên>` (NN = số lớn nhất + 1), `meta.locale: "vi"`, `meta.translations` lấy nguyên `luong-app/_vi-viewer.json`.
   `meta.output` luôn là `.archify/luong-app/<slug>.html` (git bỏ qua). File nguồn luôn đầy đủ, không tách bản gốc/bản dịch.
3. `finalize` ra đúng `meta.output` trong worktree. Nhãn tiếng Việt có dấu; sự thật lấy từ thiết kế đã chốt + code thật, không bịa.
4. Liệt kê ở mục "Sơ đồ luồng" của `techlead.md`. Báo Manager commit file nguồn cùng nhánh. Sau MỖI lần rebase có đổi file nguồn
   (kể cả git tự gộp, không xung đột) ⇒ `rm -f .archify/luong-app/<slug>.browser-check.json` rồi finalize lại, không dùng
   `--out-dir` (biên nhận ở thư mục khác thì máy không thấy): máy so HTML với nguồn, lệch là không cho gộp.
5. Thư ký chạy máy kiểm khi phòng xin gộp: đổi code một mảng (server, web, hồ sơ tính năng) mà sơ đồ mảng đó không đổi ⇒ trả về.
   Bước đi thật sự không đổi (chỉ chữ, chỉ giao diện) ⇒ ghi `<slug>: lý do` vào `.scratch/<key>/luong/KHONG-DOI.md`, không vẽ.

## Luật thiết kế

- **Bảng/cột**: `snake_case` (C6); khoá chính UUID như bảng hiện có; tiền `NUMERIC` ↔ `BigDecimal` (C11); mọi cột
  nullable phải nói vì sao; ràng buộc DB (`CHECK`, `UNIQUE`, FK) cho luật nào DB canh được — ghi luật đó cũng phải chặn ở Service.
- **Không** thêm bảng/cột ngoài phạm vi đã chốt ở spec mà không ghi rõ "nới phạm vi" (CLAUDE.md "PHẠM VI v0.1").
- **Cấu trúc dữ liệu chung đội** (`team_settings` một dòng mỗi đội, cột có kiểu) — lát nào cần cài đặt thì thêm cột vào đó.
- **Endpoint**: `/api/v1/…` kebab-case danh từ số nhiều (C5); lỗi là mã `<mảng>.<tênLỗi>` + `params` (C14); endpoint công
  khai phải nêu để sửa `SecurityConfig` và bảng đường công khai.
- **Ranh giới**: mảng chỉ giữ ID của mảng khác (C19); Controller đổi Request thành `<Độngtừ><Danhtừ>Command` (C20).
- **ADR**: quyết định khó đảo ngược (đổi mô hình dữ liệu, chọn thư viện, đổi luật đã chốt) ⇒ viết nháp theo
  `docs/adr/0000-mau-adr.md` (Bối cảnh / Quyết định / Hệ quả) vào `.scratch/<key>/adr-nhap-<tên>.md`; số ADR lấy lúc gộp.
- **Cần Sếp duyệt** chỉ gồm: bảng/cột/quan hệ ngoài thiết kế đã duyệt, hợp đồng dùng chung giữa phòng, tiền/quyền/bảo mật,
  thư viện/công nghệ mới, đổi luật dự án, việc khó đảo ngược. Chi tiết kỹ thuật còn lại Techlead + Manager tự chốt,
  ghi một dòng trong mục "Đã tự quyết".
- **Hợp đồng chung**: thứ phòng khác cũng dùng ⇒ mục riêng "Dùng chung với phòng khác" trong `techlead.md`: phòng nào đã
  có (dùng lại, không viết bản thứ hai) hoặc phòng này chốt (đưa vào ADR nháp, vào "Cần Sếp duyệt").
- **W9**: không thiết kế tối ưu (index phụ, cache) khi chưa có số đo; ghi vào "Cố ý chưa làm".
- Thuật ngữ trong `techlead.md` kèm `()` giải thích, chép đúng bảng thuật ngữ cuối `CLAUDE.md` — Sếp đang học.

## Khi Manager feedback

Manager gửi qua terminal ⇒ sửa `techlead.md` tại chỗ, ghi đầu file dòng "Sửa YYYY-MM-DD: …", viết lại báo cáo
`.scratch/<key>/reports/techlead.md` (Manager đã dời bản cũ), dòng cuối `LANE-DONE techlead`.
