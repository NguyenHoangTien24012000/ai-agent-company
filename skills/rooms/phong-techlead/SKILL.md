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
5. Skill repo dùng khi cần: `java-architect`, `postgres-pro`, `api-designer`, `domain-modeling` (bảng từ vựng, ADR).

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
## Cần Sếp duyệt (cổng 4)      ← danh sách gạch đầu dòng, mỗi dòng một quyết định
```

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
- **W8**: mọi thứ mới (cột, bảng, thư viện, đổi cách làm) chỉ là ĐỀ XUẤT có khuyến nghị (W4), nằm trong mục "Cần Sếp duyệt".
- **W9**: không thiết kế tối ưu (index phụ, cache) khi chưa có số đo; ghi vào "Cố ý chưa làm".
- Thuật ngữ trong `techlead.md` kèm `()` giải thích, chép đúng bảng thuật ngữ cuối `CLAUDE.md` — Sếp đang học.

## Khi Manager feedback

Manager gửi qua terminal ⇒ sửa `techlead.md` tại chỗ, ghi đầu file dòng "Sửa YYYY-MM-DD: …", viết lại báo cáo
`.scratch/<key>/reports/techlead.md` (Manager đã dời bản cũ), dòng cuối `LANE-DONE techlead`.
