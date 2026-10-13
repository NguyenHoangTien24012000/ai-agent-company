# Hợp đồng chung — công ty agent SportsHub

Nguồn sự thật cho MỌI lane. Spec đầy đủ (vì sao): `/Users/tien/Claude/sportshub/.scratch/cong-ty-agent/spec.md`.
Không sửa file này trong lane; thấy thiếu thì ghi vào báo cáo mục "Blocked On".

## Thư mục `~/sportshub-company/` (gọi tắt `$CO`)

```
bin/company.py        CLI duy nhất ghi state (lane L1)
bin/board-server.py   server localhost: phục vụ board + nhận nút bấm (lane L1)
bin/wait-event.sh     chờ sự kiện mới, có lọc theo phòng/loại (lane L1)
bin/open-room.sh      mở phòng: worktree + env + terminal Manager (lane L4)
board.html            board (lane L2)
state/rooms/<KEY>.json   một file mỗi phòng
state/company.json       trạng thái chung (chìa khoá app)
state/events.jsonl       sổ sự kiện, mỗi dòng một JSON
data/board.js            `window.BOARD = <snapshot>;` — company.py sinh lại sau MỖI lần ghi (cho board mở bằng file://)
skills/thu-ky/SKILL.md   vòng làm việc của Thư ký (lane L4)
CLAUDE.md                ngữ cảnh cho phiên Thư ký (lane L4)
```

Python 3 thư viện chuẩn, không cài thêm gì. Giờ: ISO 8601 có múi `+07:00`.
Mọi lần ghi: khoá `fcntl` trên `state/.lock`, ghi file tạm rồi `os.replace`, nối 1 dòng vào `events.jsonl`,
sinh lại `data/board.js`. `$SPORTSHUB_CO` (env) đổi gốc thư mục — test dùng cái này.

## KEY phòng

Chữ hoa, số, gạch ngang, 2–24 ký tự, ví dụ `ATTEND`, `TEAM-STATS`. Nhánh mặc định `phong/<key-thường>`,
worktree mặc định `/Users/tien/orca/workspaces/sportshub/<key-thường>`.

## `state/rooms/<KEY>.json`

```json
{
  "key": "ATTEND",
  "title": "Lát 2 — có mặt + đi muộn",
  "status": "active",                 // active | done | cancelled
  "step": "hoi-dap",                  // xem STEPS
  "branch": "phong/attend",
  "worktree": "/Users/tien/orca/workspaces/sportshub/attend",
  "managerTerminal": "term_…",        // handle Orca của Manager, có thể null
  "roles": ["designer","techlead","dev-server","dev-web","qa","review"],
  "needsAppKey": true,
  "lanes": [ {"role":"techlead","handle":"term_…","model":"opus","status":"running","note":"","updatedAt":"…"} ],
  "asks":  [ ASK ],
  "bugs":  [ BUG ],
  "gates": { "1": null, "2": null, "3": null, "4": null, "5": null, "6": null },   // khi duyệt: {"at":"…","choice":"ok","askId":"…"}
  "links": { "spec": ".scratch/attend/spec.md", "featureDoc": "docs/features/attend.md", "nghiemThu": "…", "qaReport": "…", "review": "…" },
  "overlaps": [ {"with":"TEAM-STATS","files":["web/src/app/router.tsx"],"conflict":false,"at":"…"} ],
  "evidence": [ {"claim":"…","manager":"…","thuKy":"…","cmd":"…","ok":true,"at":"…"} ],
  "createdAt": "…", "updatedAt": "…"
}
```

Đường dẫn trong `links` tương đối với `worktree` (hoặc tuyệt đối).

### STEPS (thứ tự hiển thị trên board)

`hoi-dap` · `cho-goi` (nút 1) · `thiet-ke` · `kien-truc` · `ke-hoach-test` · `code` · `test` · `review` ·
`cho-check` (nút 5) · `chuan-bi-gop` · `cho-gop` (nút 6) · `xong`

Designer và Techlead chạy song song nên nút 2–4 KHÔNG là bước riêng: chúng hiện bằng `gates` + ask đang mở.

### Sáu cổng (gate) duyệt — im lặng không bao giờ là đồng ý

| gate | Tên |
|---|---|
| 1 | Gói phòng + hồ sơ tính năng |
| 2 | Bản ý tưởng thiết kế |
| 3 | Giao diện mẫu |
| 4 | Thiết kế Techlead (DB, API, ADR, thư viện) |
| 5 | Check cuối (QA + review) |
| 6 | Cho gộp + push |

### ASK

```json
{ "id": "ATTEND-a3", "room": "ATTEND", "kind": "duyet",   // duyet (có gate) | quyet (chọn phương án) | thaotac (Sếp phải tự làm)
  "gate": 1,                                              // 1–6 hoặc null
  "title": "Duyệt gói phòng + hồ sơ tính năng",
  "context": "markdown ngắn",
  "options": [ {"key":"ok","label":"Duyệt"}, {"key":"sua","label":"Cần sửa (ghi chú)"} ],
  "recommend": "ok",
  "links": ["docs/features/attend.md"],
  "status": "open",                                       // open | resolved
  "choice": null, "note": null,
  "answeredVia": null,                                    // terminal | board | thu-ky
  "createdAt": "…", "resolvedAt": null }
```

id = `<KEY>-a<n>`, n tăng dần trong phòng. Resolve một ask có `gate` với choice `ok` ⇒ ghi `gates[gate]`.
Choice khác `ok` không ghi gate. Ask kind `duyet` luôn có option `ok`.

### BUG

```json
{ "id": "ATTEND-b2", "room": "ATTEND", "title": "…", "area": "server",   // server | web
  "steps": "markdown", "shots": ["…png"], "severity": "high",            // high | normal
  "status": "open",                    // open → fixing → retest → closed (retest → fixing nếu còn lỗi)
  "assignee": null,                    // vai, ví dụ dev-web
  "needsBoss": false,                  // true = cần Sếp quyết hành vi → hiện ở "Việc của anh"
  "history": [ {"at":"…","by":"qa","status":"open","note":"…"} ],
  "createdAt": "…", "updatedAt": "…" }
```

Chỉ `--by qa` được đặt `closed` (CLI từ chối nếu khác).

## `state/company.json`

```json
{ "appKey": {"room":"ATTEND","since":"…"},          // hoặc null
  "keyQueue": [ {"room":"FUND","since":"…","reason":"QA test quỹ"} ] }
```

Chìa khoá app: chỉ một phòng được chạy app thật (DB 5432, server 8080, web 5173).
- `key request KEY` — cách xin CHUẨN: trống ⇒ nhận luôn (`key_taken`); phòng khác giữ ⇒ xếp hàng, sự kiện
  `key_requested` (`holder`, `position`, `reason`). Thư ký thấy sự kiện thì nhắn Manager phòng đang giữ.
- `key release KEY` — còn phòng active xếp hàng ⇒ chìa khoá **chuyển ngay** cho phòng đầu hàng; sự kiện
  `key_released` có `handedTo`. Thư ký nhắn Manager phòng được nhận. `room done` / `room set --status done|cancelled`
  cũng nhả + chuyển (`keyHandedTo`) và rút phòng khỏi hàng.
- `key take KEY` khi phòng khác giữ ⇒ exit 3 (giữ cho script cũ).

## `state/events.jsonl`

Mỗi dòng: `{"ts":"…","type":"…","room":"ATTEND", ...trường riêng}`. Loại:

`room_opened` · `room_changed` (step/links/roles…) · `room_done` · `lane_changed` · `ask_opened` · `ask_resolved`
(có `via`, `choice`, `note`) · `bug_opened` · `bug_changed` (có `status`, `assignee`) · `key_requested` · `key_taken` · `key_released` (có `handedTo`) ·
`overlap` · `evidence` · `note`

## CLI `bin/company.py`

In kết quả ngắn ra stdout; `--json` in JSON. Lỗi người dùng: exit 2 + thông báo stderr.

```
room new KEY --title T [--branch B] [--worktree W] [--manager-terminal H]
room set KEY [--step S] [--title T] [--manager-terminal H] [--roles a,b] [--needs-app-key yes|no]
             [--link name=path]... [--status active|done|cancelled]
room show KEY            room list [--all]
room done KEY            # status=done, step=xong, nhả chìa khoá nếu giữ; IN lệnh dọn worktree, KHÔNG tự chạy
lane add KEY --role R --handle H [--model M]
lane set KEY --handle H --status running|waiting|done|closed [--note N]
ask add KEY --kind duyet|quyet|thaotac [--gate N] --title T [--context C] [--option k=label]... [--recommend k] [--link L]...
            # in ra id. kind=duyet mà không có --option ⇒ mặc định ok=Duyệt, sua=Cần sửa
ask resolve ID --choice k [--note N] [--via terminal|board|thu-ky]
ask list [--open] [--room KEY]
bug add KEY --title T --area server|web [--steps S] [--shot P]... [--severity high|normal] [--needs-boss] --by ROLE
bug set ID [--status S] [--assignee R] [--note N] --by ROLE
key request KEY [--reason R]   key take KEY   key release KEY [--note N]   key status
overlap KEY --with OTHER --files a,b [--conflict]   # Thư ký ghi; --clear để xoá
evidence KEY --claim C --manager M --thu-ky S --cmd CMD --ok|--mismatch
note KEY "text"          # sự kiện tự do
snapshot                 # in JSON snapshot (giống data/board.js)
```

### Snapshot (`data/board.js` và `GET /api/state`)

```json
{ "generatedAt": "…", "appKey": {…}|null, "keyQueue": [ … ],
  "rooms": [ ROOM, … ],                 // active trước, rồi done 7 ngày gần nhất
  "myQueue": [ ASK|BUG(needsBoss), … ], // mọi ask open + bug needsBoss chưa closed, cũ nhất trước
  "events": [ … 50 sự kiện mới nhất, mới nhất trước … ] }
```

## `bin/board-server.py`

`python3 bin/board-server.py [--port 8765]`, chỉ bind `127.0.0.1`.

- `GET /` → `board.html` · `GET /data/board.js` → file · `GET /api/state` → snapshot JSON (no-cache)
- `POST /api/answer` body `{"askId","choice","note"}` → resolve với `via=board`. Chặn CSRF (kiểu tấn công lừa trình
  duyệt gửi lệnh thay bạn): bắt buộc `Content-Type: application/json` và header `X-Company: 1`; Origin nếu có phải là
  `http://127.0.0.1:<port>` hoặc `http://localhost:<port>`. Trả `{ok:true, ask}` hoặc `{ok:false, error}` + 4xx.
- `GET /api/health` → `{ok:true}`

## `bin/wait-event.sh`

`wait-event.sh [--room KEY] [--types a,b] [--timeout 14400] [--interval 5]`
Chặn tới khi `events.jsonl` có dòng mới KHỚP bộ lọc (tính từ lúc gọi), in các dòng khớp, exit 0. Hết giờ exit 2.
Thư ký: không lọc. Manager: `--room KEY`.

## Board (`board.html`)

Một file HTML tĩnh, không CDN, không build. Nguồn dữ liệu: thử `fetch('/api/state')` (khi mở qua server, tự làm
mới mỗi 5 s); thất bại ⇒ dùng `window.BOARD` từ `<script src="data/board.js">` (file://, làm mới bằng reload).
Nút trả lời: có server ⇒ `POST /api/answer`; không ⇒ chép câu `company.py ask resolve <ID> --choice <k> --via board`
vào clipboard và báo "đã chép, dán vào terminal Manager".

## Vai trong phòng (để các skill viết khớp nhau)

Manager (phiên chính, Opus) · designer · techlead · dev-server · dev-web · qa · review. Lane mở bằng Orca;
mọi lane ghi trạng thái qua `company.py lane set`. Hồ sơ phòng: `<worktree>/.scratch/<key-thường>/`
(spec, `briefs/`, `reports/`, kế hoạch test, báo cáo QA). Thư ký là phiên Claude ở `$CO`.
