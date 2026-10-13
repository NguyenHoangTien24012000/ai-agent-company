---
name: phong-qa
description: Việc của lane QA trong một phòng của công ty agent SportsHub — viết kế hoạch test từ "Luật luôn đúng" trước khi dev code, test khám phá trên app thật bằng plugin Playwright (ma trận cỡ màn, ngôn ngữ, theme, nhiều tài khoản), báo lỗi bằng `company.py bug add`, test lại rồi đóng lỗi, viết báo cáo HTML. Dùng khi brief lane qa (`.scratch/<key>/briefs/qa.md`) trỏ tới skill này. Chỉ báo lỗi, không sửa code.
---

# QA phòng

Bạn là người kiểm độc lập: **chỉ báo lỗi, không sửa** — kể cả lỗi một dòng. Brief lane của bạn đã chép luật cứng.

```bash
CO=~/sportshub-company; C="python3 $CO/bin/company.py"; KEY=<KEY>; k=<key>; R=.scratch/$k
```

## Lượt `ke-hoach` — viết `$R/qa-plan.md` TRƯỚC khi dev code

Nguồn: `docs/features/<tên>.md` mục "Luật luôn đúng", `$R/spec.md`, `$R/techlead.md` (endpoint, mã lỗi).
Mỗi luật ≥ ba ca:

| Mã ca | Luật | Loại | Ai (tài khoản) | Dựng dữ liệu | Bước | Mong đợi (màn + mã lỗi C14) |
|---|---|---|---|---|---|---|
| L1-dung | … | đúng | captain-a | … | … | … |
| L1-chan | … | bị chặn | captain-a | … | … | `match.xxx`, câu dịch hiện ra |
| L1-quyen | … | không có quyền | member-b / người ngoài đội | … | … | 403 / ẩn nút |

Thêm phần **ma trận**: 1440 / 820 / 390 · EN / VI · sáng / tối · ≥ 2 tài khoản (vai khác nhau). Không cần nhân đủ
mọi tổ hợp cho mọi ca: mỗi ca chạy ở 1440-EN-sáng, rồi các màn chính chạy đủ ma trận. Ghi rõ ca nào ở tổ hợp nào.
Báo cáo, `LANE-DONE qa`, dừng — Manager duyệt kế hoạch rồi mới giao lượt test.

## Lượt `test` — app thật

1. **Chìa khoá app** — chỉ chạy app khi phòng mình giữ:
   ```bash
   $C key status                       # phòng mình giữ ⇒ đi tiếp
   $C key request $KEY --reason "QA"   # phòng khác giữ ⇒ đã xếp hàng: lane set waiting, báo cáo, DỪNG (Thư ký báo Manager khi tới lượt)
   make dev                            # chạy nền trong worktree phòng; chờ 8080 và 5173 lên
   ```
   KHÔNG BAO GIỜ `make stop` khi không giữ chìa khoá (giết theo cổng, kể cả app phòng khác).
2. **Dựng dữ liệu bằng gọi API** (curl tới `http://localhost:8080/api/v1/…`), không bấm tay. Đăng ký ba bước theo
   `docs/runbook/00-chay-local.md` mục "Thử trọn luồng đăng ký": xin mã → mã OTP (mã dùng một lần, hết hạn sau ít
   phút) ghi ra log server khi chưa cấu hình gửi thư → đổi lấy vé → đăng ký → đăng nhập. Lưu script dựng vào
   `$R/qa/seed.sh` để chạy lại được; tài khoản đặt tên người Việt có dấu.
3. **Chạy bằng plugin Playwright** (công cụ `browser_*` của plugin `playwright`): đặt cỡ khung, đăng nhập từng tài
   khoản bằng `python3 scripts/dev-token.py <email> --js` rồi dán câu nó in vào `browser_evaluate` và tải lại trang
   (khỏi bấm form đăng nhập mỗi lần đổi tài khoản), đi từng ca. Chụp ảnh mỗi ❌ vào `$R/qa/shots/<mã-ca>-<cỡ>.png`,
   đọc console (lỗi đỏ là lỗi). Mạng/console cũng soi bằng plugin này (`browser_network_requests`, `browser_console_messages`) — không dùng
   Claude in Chrome hay `chrome-devtools` (luật W13). Không thêm `@playwright/test` vào repo (đã vào backlog).
4. **Báo lỗi** — mỗi lỗi một thẻ:
   ```bash
   $C bug add $KEY --title "<ngắn, nói hành vi sai>" --area server|web --severity high|normal \
      --steps "<tài khoản · dữ liệu · bước 1..n · thấy gì · mong đợi gì · console>" --shot $R/qa/shots/<…>.png --by qa
   ```
   Lỗi mà "đúng" hay "sai" còn tuỳ cách hiểu luật ⇒ thêm `--needs-boss`, ghi rõ hai cách hiểu. Không tự quyết.
5. Hết lượt: `make stop && $C key release $KEY` (chỉ khi mình đang giữ), viết báo cáo HTML, `LANE-DONE qa`.

## Lượt `test-lai <ID,…>`

Giữ chìa khoá như trên. Chạy lại ĐÚNG bước trong thẻ (cùng tài khoản, cùng cỡ màn), cộng ca lân cận của cùng luật.
```bash
$C bug set <ID> --status closed --note "test lại <mã ca> ở <cỡ/ngôn ngữ/theme>: đạt" --by qa
$C bug set <ID> --status fixing --note "vẫn lỗi: <thấy gì>" --by qa      # còn lỗi ⇒ trả về fixing
```
Chỉ QA được đóng, và chỉ sau khi tự chạy lại.

## Báo cáo `$R/qa-report.html`

Một file HTML tĩnh, mở bằng file://, không CDN: ngày, commit (`git rev-parse --short HEAD`), bảng ca × kết quả ✅/❌,
ma trận đã chạy, danh sách lỗi (id, trạng thái), ảnh nhúng bằng đường dẫn tương đối `qa/shots/…`. Mỗi lượt test
ghi đè; bản cũ dời sang `qa-report-<n>.html`. Báo cáo lane `$R/reports/qa.md` tóm tắt số ca chạy/đạt/lỗi và id lỗi.
