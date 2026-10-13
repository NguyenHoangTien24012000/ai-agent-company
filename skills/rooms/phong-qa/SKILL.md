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

1. **Chìa khoá app** — chỉ chạy app khi phòng mình giữ (cổng 8080/5173 vẫn dùng chung):
   ```bash
   $C key status                       # phòng mình giữ ⇒ đi tiếp
   $C key request $KEY --reason "QA"   # phòng khác giữ ⇒ đã xếp hàng: lane set waiting, báo cáo, DỪNG (Thư ký báo Manager khi tới lượt)
   # DB riêng của phòng, trong container sportshub-db ĐANG chạy (không dựng container mới):
   DB=sportshub_${k//-/_}; P="docker exec sportshub-db psql -U sportshub -d postgres"
   $P -tAc "SELECT 1 FROM pg_database WHERE datname='$DB'" | grep -q 1 || $P -c "CREATE DATABASE $DB"
   export SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/$DB   # Flyway tự chạy V1→Vn trên DB này
   mkdir -p $R/qa; make server > $R/qa/server.log 2>&1 &   # chạy nền trong worktree phòng; mã OTP đọc ở log này
   make web > $R/qa/web.log 2>&1 &                         # chờ 8080 và 5173 lên
   ```
   ⛔ KHÔNG `make dev` trong worktree (nó gọi `make db` → `docker compose up` của worktree) và KHÔNG BAO GIỜ
   `make stop` (giết theo cổng mọi app, kể cả phòng khác, rồi tắt luôn container DB chung). Không đụng docker.
2. **Dựng dữ liệu bằng gọi API** (curl tới `http://localhost:8080/api/v1/…`), không bấm tay. Đăng ký ba bước theo
   `docs/runbook/00-chay-local.md` mục "Thử trọn luồng đăng ký": xin mã → mã OTP (mã dùng một lần, hết hạn sau ít
   phút) ghi ra log server khi chưa cấu hình gửi thư → đổi lấy vé → đăng ký → đăng nhập. Lưu script dựng vào
   `$R/qa/seed.sh` để chạy lại được; tài khoản đặt tên người Việt có dấu.
3. **Chạy bằng plugin Playwright** (công cụ `browser_*` của plugin `playwright`): đặt cỡ khung, đăng nhập từng tài
   khoản rồi tải lại trang (khỏi bấm form đăng nhập mỗi lần đổi tài khoản), đi từng ca. ⚠️ `scripts/dev-token.py`
   hiện chỉ đọc DB `sportshub`, không thấy tài khoản trong `$DB` của phòng (sắp có `--db`; có rồi thì dùng
   `dev-token.py <email> --db $DB --js`). Trước đó: `seed.sh` lưu thẻ trả về từ `POST /api/v1/auth/login` của từng
   tài khoản, rồi `browser_evaluate` câu `() => { localStorage.setItem('sportshub.token', '<thẻ>'); return 'ok' }`.
   Chụp ảnh mỗi ❌ vào `$R/qa/shots/<mã-ca>-<cỡ>.png`,
   đọc console (lỗi đỏ là lỗi). Mạng/console cũng soi bằng plugin này (`browser_network_requests`, `browser_console_messages`) — không dùng
   Claude in Chrome hay `chrome-devtools` (luật W13). Không thêm `@playwright/test` vào repo (đã vào backlog).
4. **Báo lỗi** — mỗi lỗi một thẻ:
   ```bash
   $C bug add $KEY --title "<ngắn, nói hành vi sai>" --area server|web --severity high|normal \
      --steps "<tài khoản · dữ liệu · bước 1..n · thấy gì · mong đợi gì · console>" --shot $R/qa/shots/<…>.png --by qa
   ```
   Lỗi mà "đúng" hay "sai" còn tuỳ cách hiểu luật ⇒ thêm `--needs-boss`, ghi rõ hai cách hiểu. Không tự quyết.
5. Hết lượt: tắt ĐÚNG app của worktree mình rồi trả chìa khoá (chỉ khi mình đang giữ), viết báo cáo HTML, `LANE-DONE qa`:
   ```bash
   for port in 8080 5173; do for pid in $(lsof -ti tcp:$port -sTCP:LISTEN); do
     lsof -a -p $pid -d cwd -Fn | grep -q "^n$PWD/" && kill $pid    # chỉ tiến trình chạy từ worktree này
   done; done
   $C key release $KEY       # giữ nguyên DB $DB và container sportshub-db — không docker stop/down
   ```

## Soát mỗi màn — ngoài các ca của kế hoạch

Ý lấy từ skill `browser-qa` của affaan-m/ECC (MIT), viết lại cho Playwright. Mỗi màn chính, ở 1440 / 820 / 390:

| Soát | Cách (plugin Playwright) | Lỗi khi |
|---|---|---|
| Console | `browser_console_messages` | có dòng đỏ (lọc tiếng ồn của tiện ích trình duyệt, ghi rõ đã lọc gì) |
| Mạng | `browser_network_requests` | 4xx/5xx ngoài ca cố ý; 4xx cố ý mà không có `code` C14 hoặc câu dịch không hiện |
| Tràn ngang | `browser_evaluate` `() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]` | số đầu > số sau; tìm thủ phạm: `[...document.querySelectorAll('*')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 5).map(e => e.tagName + '.' + e.className)` |
| Bàn phím | `browser_press_key` Tab / Shift+Tab / Enter / Escape qua form chính | không thấy viền focus, thứ tự nhảy lung tung, Enter không gửi, Escape không đóng hộp thoại |
| Nhãn form | `browser_evaluate` đếm `input, select, textarea` không có `labels`, `aria-label`, `aria-labelledby` | > 0 |
| Ảnh, nút icon | đếm `img:not([alt])` và `button` không chữ, không `aria-label` | > 0 |
| Mốc trang | có đúng một `main`, có `h1` | thiếu |
| Theme tối | lặp tràn ngang + chụp ảnh ở theme tối | chữ chìm vào nền, viền mất |

Quét a11y (khả năng tiếp cận cho người dùng khuyết tật) tự động bằng axe-core: **chưa làm, cần Sếp duyệt** —
`web/` chưa có `axe-core`, nạp nó (cài npm hay tải từ CDN vào trang) là thêm thư viện (W8). Bảng trên là phần làm
tay được; dù sạch cũng không ghi "đạt chuẩn tiếp cận", chỉ ghi "không thấy lỗi ở các mục đã soát".

Kết luận cuối báo cáo, đúng một dòng: **ĐẠT** (0 lỗi mở) · **ĐẠT KÈM LỖI** (chỉ còn lỗi `normal`, liệt kê id) ·
**KHÔNG ĐẠT** (còn lỗi `high` hoặc ca của "Luật luôn đúng" chưa qua) · **CHƯA KẾT LUẬN** (ca/ma trận chưa chạy đủ, ghi thiếu gì).

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
