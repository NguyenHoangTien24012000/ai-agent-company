# Hợp đồng chung — công ty agent SportsHub

Nguồn sự thật cho MỌI lane. Spec đầy đủ (vì sao): `/Users/tien/Claude/sportshub/.scratch/cong-ty-agent/spec.md`.
Không sửa file này trong lane; thấy thiếu thì ghi vào báo cáo mục "Blocked On".

## Thư mục `~/sportshub-company/` (gọi tắt `$CO`)

```
bin/company.py        CLI duy nhất ghi state (lane L1)
bin/board-server.py   server localhost: phục vụ board + nhận nút bấm (lane L1)
bin/wait-event.sh     chờ sự kiện mới, có lọc theo phòng/loại (lane L1)
bin/heartbeat.py      nhịp kiểm không dùng AI: lane đứng yên, lane dừng ở lỗi, Thư ký ngủ quên (open-board.sh bật nền)
bin/open-room.sh      mở phòng: worktree + env + terminal Manager (lane L4); `--task ID` gắn thẻ việc với phòng
board.html            board (lane L2)
state/rooms/<KEY>.json   một file mỗi phòng
state/company.json       trạng thái chung (chìa khoá app)
state/tasks.json         thẻ việc (task): Backlog / Todo trên board
state/retros/<KEY>.md    bài rút kinh nghiệm của phòng đã xong (board link ở tab Done)
state/events.jsonl       sổ sự kiện, mỗi dòng một JSON
state/heartbeat.json     dấu chống báo lặp của nhịp kiểm · heartbeat.pid · heartbeat.log
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
  "status": "open",                                       // open | resolved | cancelled
  "choice": null, "note": null,
  "answeredVia": null,                                    // terminal | board | thu-ky
  "createdAt": "…", "resolvedAt": null }
```

id = `<KEY>-a<n>`, n tăng dần trong phòng. Resolve một ask có `gate` với một phương án cụ thể (`ok`, hay hướng
`a`/`b`/… của cổng 2) ⇒ ghi `gates[gate]`. Choice `sua` hoặc `khac` không ghi gate (Manager trình lại). Ask kind `duyet` luôn có option `ok`.
`--also-gate N` (lặp được): duyệt một lần ghi kèm cổng N — dùng cho **cổng 5 + 6 gộp** (`--gate 6 --also-gate 5`) khi
rebase sạch; `ask reopen` gỡ cả các cổng kèm. Trường `alsoGates: [5]` trong ASK.

**Sếp chọn bằng một cú bấm, chỉ gõ khi không phương án nào ổn** (chốt 12/10/2026):
- `quyet` **bắt buộc ≥ 2 `--option`** (CLI từ chối nếu thiếu), nên kèm `--recommend`. Một ask = một câu hỏi.
  CLI tự thêm phương án `khac` ("Khác — tự viết").
- `duyet` không ghi `--option` ⇒ `ok`/`sua`. `thaotac` ⇒ `done` ("Đã làm xong").
- Choice `khac` (và `tra-loi` của ask cũ) **bắt buộc có note không trống** — CLI và server từ chối, board chặn trước.
- Ask cũ lưu `options: []`: `quyet` được hiểu là `tra-loi` ("Gửi câu trả lời"), để còn trả lời được.

**Câu của thẻ việc** (chốt 17/10/2026): câu Sếp phải chọn khi việc còn là thẻ Backlog/Todo, chưa có phòng (ví dụ câu
cuối báo cáo nghiên cứu). `ask add --task <ID>` thay cho KEY: thẻ phải tồn tại và `room` null. ASK lưu ngay trong thẻ
(`tasks.json`, trường `asks`) với `"room": null, "task": "T5"`, id = `<ID>-q<n>` (ví dụ `T5-q1`), n tăng theo thẻ.
Không có cổng: `--gate`/`--also-gate` và kind `duyet` bị từ chối; còn lại (kind `quyet`/`thaotac`, options, recommend,
context, link, resolve, cancel, reopen, `list --open`) y như ask của phòng. Sự kiện `ask_*` của câu thẻ có `room: null`
và trường `task`. `ask reopen` từ chối khi thẻ đã mở phòng (hỏi lại qua phòng).

`ask cancel ID [--note]`: Manager rút ask đang mở (ví dụ thay câu hỏi mở bằng câu có phương án) ⇒ `status: cancelled`,
khỏi "Việc của anh", sự kiện `ask_cancelled`.

`ask reopen ID` (Sếp bấm nhầm): ask `resolved` ⇒ `open`, xoá choice/note/answeredVia/resolvedAt; nếu `gates[gate]`
do chính ask này ghi thì gỡ về `null` (cổng do ask sau ghi thì giữ). Sự kiện `ask_reopened` mang `previousChoice`.

### BUG

```json
{ "id": "ATTEND-b2", "room": "ATTEND", "title": "…", "area": "server",   // server | web
  "steps": "markdown", "shots": ["…png"], "severity": "high",            // high | normal
  "status": "open",                    // open → fixing → retest → closed (retest → fixing nếu còn lỗi); open|fixing → deferred
  "assignee": null,                    // vai, ví dụ dev-web
  "needsBoss": false,                  // true = cần Sếp quyết hành vi → hiện ở "Việc của anh"
  "history": [ {"at":"…","by":"qa","status":"open","note":"…"} ],
  "createdAt": "…", "updatedAt": "…" }
```

Chỉ `--by qa` được đặt `closed` (CLI từ chối nếu khác).

`deferred` = **dời sang backlog** (lỗi có thật nhưng cố ý không sửa trong phòng, W7): chỉ từ `open` hoặc `fixing`,
bắt buộc `--note` không trống trỏ tới dòng backlog hoặc commit ghi nó. Là trạng thái cuối như `closed`: không còn tính
"chưa đóng" trên board (nhãn "Dời backlog"), không vào `myQueue` kể cả `needsBoss`.

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

## `state/tasks.json` — thẻ việc

Ý tưởng Sếp nêu nhưng chưa mở phòng (chốt 16/10/2026). Thẻ là state cấp công ty, không thuộc phòng nào.

```json
{ "nextId": 4,                          // chỉ tăng: thẻ đã xoá không nhường số
  "tasks": [ { "id": "T3", "title": "Giao lưu đội", "note": "…"|null,
               "column": "backlog",     // backlog (để đó) | todo (Sếp đã cho làm, chờ mở phòng)
               "room": null,            // KEY phòng khi đã mở phòng từ thẻ (task start)
               "asks": [ ASK ],         // câu của thẻ (ask add --task), có thể thiếu ở thẻ cũ
               "createdAt": "…", "updatedAt": "…" } ] }
```

`task start` bị từ chối (exit 2, liệt kê id) khi thẻ còn ask `open` — trả lời hoặc `ask cancel` trước; ask đã trả lời/huỷ
ở lại trong thẻ làm lịch sử. `open-room.sh --task` kiểm điều này trước khi tạo worktree.

Thẻ có `room` khác null không còn ở Backlog/Todo: board hiện phòng đó ở Doing/Done; `task move` bị từ chối.

## `state/events.jsonl`

Mỗi dòng: `{"ts":"…","type":"…","room":"ATTEND", ...trường riêng}`. Sự kiện cấp công ty có `"room": null`
(ghi bằng `Company.record`, không đổi state phòng). Loại:

`room_opened` · `room_changed` (step/links/roles…) · `room_done` · `lane_changed` · `ask_opened` · `ask_resolved` · `ask_reopened` · `ask_cancelled` · `forward_failed`
(có `via`, `choice`, `note`) · `bug_opened` · `bug_changed` (có `status`, `assignee`) · `key_requested` · `key_taken` · `key_released` (có `handedTo`) ·
`overlap` · `evidence` · `note` · `lane_stale` (`handle`, `role`, `minutes`) · `thu_ky_silent` (`room: null`, `minutes`) ·
`lane_error` (`handle`, `role` — `manager` nếu là terminal Manager — `line`: dòng lỗi khớp, ≤ 200 ký tự) ·
`db_down` (`room: null`, `container`) ·
`task_added` · `task_changed` (`change`: `move` | `edit` | `start`) · `task_removed`
— sự kiện thẻ việc luôn `room: null`, mang `taskId`, `title`, `column`, `linkedRoom` (KEY phòng hoặc null) ·
`task_ask_answered` (`room: null`, `task`, `askId`, `choice`, `note`) — board server ghi khi Sếp trả lời câu của thẻ trên
board (thay cho chuyển Orca); `ask resolve` từ CLI không ghi

`lane_changed` của `lane add --force-gate` (lane dev-web mở trước cổng 3) có thêm `forceGate: true` và `note`.

## CLI `bin/company.py`

In kết quả ngắn ra stdout; `--json` in JSON. Lỗi người dùng: exit 2 + thông báo stderr.

```
room new KEY --title T [--branch B] [--worktree W] [--manager-terminal H]
room set KEY [--step S] [--title T] [--manager-terminal H] [--roles a,b] [--needs-app-key yes|no]
             [--link name=path]... [--status active|done|cancelled]
room show KEY            room list [--all]
room done KEY            # status=done, step=xong, nhả chìa khoá nếu giữ; IN lệnh dọn worktree, KHÔNG tự chạy
lane add KEY --role R --handle H [--model M] [--force-gate]
             # role dev-web + phòng có designer + gates["3"] chưa ghi ⇒ exit 2. --force-gate: Sếp đồng ý ngoại lệ
lane set KEY --handle H --status running|waiting|done|closed [--note N]
ask add KEY --kind duyet|quyet|thaotac [--gate N] --title T [--context C] [--option k=label]... [--recommend k] [--link L]...
            # in ra id. kind=duyet mà không có --option ⇒ mặc định ok=Duyệt, sua=Cần sửa
ask add --task ID --kind quyet|thaotac --title T [...như trên, không --gate]   # câu của thẻ chưa mở phòng ⇒ ID-qN
            # đúng một trong KEY / --task, thiếu hoặc cả hai ⇒ exit 2
ask resolve ID --choice k [--note N] [--via terminal|board|thu-ky]
ask reopen ID [--note N]                                  # Sếp bấm nhầm; chỉ Thư ký chạy, theo lời Sếp
ask cancel ID [--note N]                                  # Manager rút ask chưa ai trả lời
ask list [--open] [--room KEY | --task ID]           # không lọc ⇒ câu của phòng rồi câu của thẻ
bug add KEY --title T --area server|web [--steps S] [--shot P]... [--severity high|normal] [--needs-boss] --by ROLE
bug set ID [--status S] [--assignee R] [--note N] --by ROLE    # S=deferred bắt buộc --note
key request KEY [--reason R]   key take KEY   key release KEY [--note N]   key status
overlap KEY --with OTHER --files a,b [--conflict]   # Thư ký ghi; --clear để xoá
evidence KEY --claim C --manager M --thu-ky S --cmd CMD --ok|--mismatch
note KEY "text"          # sự kiện tự do
task add --title T [--note N] [--column backlog|todo]     # in id (T1, T2…); mặc định backlog
task move ID --column backlog|todo                        # thẻ đã gắn phòng ⇒ exit 2
task edit ID [--title T] [--note N]                       # --note '' xoá ghi chú
task remove ID
task start ID --room KEY  # gắn thẻ với phòng vừa mở (open-room.sh --task gọi); thẻ đã gắn ⇒ exit 2
task show ID             task list [--column backlog|todo]   # --column: chỉ thẻ chưa gắn phòng của cột đó
snapshot                 # in JSON snapshot (giống data/board.js)
```

### Snapshot (`data/board.js` và `GET /api/state`)

```json
{ "generatedAt": "…", "appKey": {…}|null, "keyQueue": [ … ],
  "rooms": [ ROOM, … ],                 // active trước, rồi done 7 ngày gần nhất
  "myQueue": [ ASK|BUG(needsBoss), … ], // mọi ask open (cả câu của thẻ) + bug needsBoss chưa closed/deferred, cũ nhất trước
  "events": [ … 50 sự kiện mới nhất, mới nhất trước … ],
  "tasks": [ TASK, … ],                 // mọi thẻ (kể cả đã gắn phòng), cũ nhất trước
  "retros": [ "ATTEND", … ] }           // KEY có file state/retros/<KEY>.md
```

## `bin/board-server.py`

`python3 bin/board-server.py [--port 8765]`, chỉ bind `127.0.0.1`.

- `GET /` → `board.html` · `GET /data/board.js` → file · `GET /api/state` → snapshot JSON (no-cache)
- `POST /api/answer` body `{"askId","choice","note"}` → resolve với `via=board`. Chặn CSRF (kiểu tấn công lừa trình
  duyệt gửi lệnh thay bạn): bắt buộc `Content-Type: application/json` và header `X-Company: 1`; Origin nếu có phải là
  `http://127.0.0.1:<port>` hoặc `http://localhost:<port>`. Trả `{ok:true, ask}` hoặc `{ok:false, error}` + 4xx.
  Ghi xong, server **tự chuyển** vào terminal Manager (luồng riêng, không làm chậm nút): `orca terminal send` câu
  `Sếp trả lời <ID> (<title>): <choice> — <nhãn>[ — Ghi chú: <note>]`. Handle rỗng thì KHÔNG gọi Orca. Không chuyển được ⇒
  sự kiện `forward_failed` `{askId, detail}` để Thư ký chuyển tay. Câu của thẻ (`task` khác null) KHÔNG gọi Orca, KHÔNG
  `forward_failed`: server ghi `task_ask_answered` để Thư ký thức dậy. Biến môi trường `ORCA` đổi đường dẫn Orca (test dùng chương trình giả).
- `POST /api/task` (cùng luật CSRF và giới hạn body như `/api/answer`) body `{"action":"add","title","note","column"}` ·
  `{"action":"move","id","column"}` · `{"action":"edit","id","title","note"}` · `{"action":"remove","id"}` → gọi hàm
  thẻ việc của `company.py`; trả `{ok:true, task}` hoặc `{ok:false, error}` + 4xx. Không có `start` (gắn phòng là việc của `open-room.sh`).
- `GET /retros/<KEY>.md` → `state/retros/<KEY>.md` dạng `text/plain` (KEY theo luật KEY phòng, không có ⇒ 404)
- `GET /api/health` → `{ok:true}`

## `bin/wait-event.sh`

`wait-event.sh [--room KEY] [--types a,b] [--timeout 14400] [--interval 5]`
Chặn tới khi `events.jsonl` có dòng mới KHỚP bộ lọc (tính từ lúc gọi), in các dòng khớp, exit 0. Hết giờ exit 2.
Thư ký: lọc theo `--types` (skill `thu-ky`). Manager: `--room KEY` — sự kiện cấp công ty (`room: null`) không khớp.

## `bin/heartbeat.py`

`heartbeat.py [--interval 900] [--stale-minutes 45] [--thu-ky-minutes 30] [--once] [--now ISO]` — script thường,
không dùng AI. Mỗi lượt, với mỗi phòng active:
- lane `running` có `updatedAt` cũ hơn `--stale-minutes` **và** phòng không có sự kiện nào (trừ sự kiện của chính nhịp
  kiểm) trong cùng khoảng ⇒ `Company.record('lane_stale', {handle, role, minutes}, room)`;
- không có tiến trình `wait-event.sh` nào không lọc `--room` (watcher của Thư ký) liên tục quá `--thu-ky-minutes` ⇒
  `thu_ky_silent` cấp công ty (mốc bắt đầu lưu ở `heartbeat.json`; test thay `ps` bằng `HEARTBEAT_PS_FILE`);
- mỗi lane `running` và `managerTerminal` (handle rỗng ⇒ bỏ qua): `$ORCA terminal read --terminal <h> --screen --limit 30`
  (đọc lỗi ⇒ bỏ qua). 12 dòng cuối khác rỗng có dòng khớp `ERROR_PATTERNS` (không phân biệt hoa thường: `model is at
  capacity`, `API Error`, `Connection lost`, `response stopped arriving`, `stream disconnected`, `network error`,
  `ECONNRESET`, `fetch failed`, `rate limit`) **và** màn hình không có `esc to interrupt` / `Working (` ⇒
  `Company.record('lane_error', {handle, role, line}, room)` ngay lượt đó (không chờ ngưỡng). Chống lặp: dấu
  `errors["ROOM/handle"] = {line, screen}` (băm 12 dòng cuối) ở `heartbeat.json`; chỉ báo lại khi dòng lỗi hay đáy màn
  hình đổi; hết lỗi thì xoá dấu, đọc lỗi thì giữ dấu. Biến `ORCA` thay Orca CLI (test dùng orca giả);
- `$DOCKER inspect -f '{{.State.Running}}' sportshub-db` khác `true` (hay lỗi: Docker tắt, container mất) ⇒
  `Company.record('db_down', {container})` cấp công ty, MỘT lần mỗi đợt tắt (dấu `dbDownSince` ở `heartbeat.json`, xoá
  khi chạy lại). Không có Docker CLI ⇒ bỏ qua. Biến `DOCKER` thay Docker CLI (test dùng docker giả).

`lane_error`, `db_down` không tính là phòng còn hoạt động (như hai loại kia). Không báo lặp: cùng (room, handle) — hay Thư ký — chỉ báo lại khi đã qua thêm một ngưỡng kể từ lần báo trước;
dấu ở `state/heartbeat.json`. Lane hết `running` thì xoá dấu. `--now` (chỉ kèm `--once`) giả giờ cho test.
`bin/open-board.sh` bật nó nền (nohup, `state/heartbeat.log`) nếu `state/heartbeat.pid` không trỏ tới tiến trình đang chạy.
`bin/wait-event.sh` gọi KHÔNG `--room` (watcher Thư ký) cũng kiểm như vậy và bật lại nếu chết — fork trong subshell
(mồ côi, cha là launchd) và heartbeat tự `os.setsid()` khi không `--once`, để không chết theo tác vụ nền của phiên đã
bật nó. `HEARTBEAT_AUTOSTART=0` tắt, `HEARTBEAT_BIN` thay script (test).

## Board (`board.html`)

Một file HTML tĩnh, không CDN, không build. Nguồn dữ liệu: thử `fetch('/api/state')` (khi mở qua server, tự làm
mới mỗi 5 s); thất bại ⇒ dùng `window.BOARD` từ `<script src="data/board.js">` (file://, làm mới bằng reload).
Nút trả lời: có server ⇒ `POST /api/answer`; không ⇒ chép câu `company.py ask resolve <ID> --choice <k> --via board`
vào clipboard và báo "đã chép, dán vào terminal Manager".

Bố cục: "Việc của anh" trên cùng; dưới là hàng tab **Backlog · Todo · Doing · Done** có số đếm (mặc định Doing, nhớ tab
bằng `localStorage`); "Nhật ký" dưới cùng. Backlog/Todo = thẻ chưa gắn phòng của cột đó (cũ nhất trước), ô thêm nhanh,
nút chuyển cột và xoá (xác nhận trong trang) gọi `POST /api/task`; không có server ⇒ chép lệnh `company.py task …`.
Câu của thẻ hiện trong "Việc của anh" như câu phòng, nhãn nguồn `<ID> · <tiêu đề thẻ>`; thẻ Backlog/Todo còn câu mở
hiện huy hiệu "N câu chờ anh". Doing = phòng chưa `done`. Done = phòng `done` (trong snapshot), mới nhất trước, một dòng mỗi phòng + link retro.

## Vai trong phòng (để các skill viết khớp nhau)

Manager (phiên chính, Opus) · designer · techlead · dev-server · dev-web · qa · review. Lane mở bằng Orca;
mọi lane ghi trạng thái qua `company.py lane set`. Hồ sơ phòng: `<worktree>/.scratch/<key-thường>/`
(spec, `briefs/`, `reports/`, kế hoạch test, báo cáo QA). Thư ký là phiên Claude ở `$CO`.
