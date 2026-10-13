# Lane dev-web — phòng <KEY>: <tên tính năng>

Worktree: `<đường dẫn worktree>` · nhánh `phong/<key>` · hồ sơ phòng `.scratch/<key>/`
Model: Codex `gpt-6.1-sol` (high). Bạn KHÔNG đọc được skill Claude — mọi luật cần thiết nằm trong file này; các
file `.claude/skills/…` bên dưới bạn mở như tài liệu thường.

**Bạn LÀ lane, không phải phiên điều phối.** Tự triển khai mọi việc trong brief này; KHÔNG mở phiên con, KHÔNG tách việc
sang lane cmux/Orca, kể cả khi file luật chung (`AGENTS.md`, `CLAUDE.md` toàn máy) bảo hãy tách việc nhiều file.

## Files You May Edit
- `web/src/features/<tên>/**`, `web/src/pages/<…>.tsx`, `web/src/app/router.tsx` (chỉ thêm route của tính năng)
- `web/src/locales/en/<…>.json`, `web/src/locales/vi/<…>.json`
- `.scratch/<key>/reports/dev-web.md`
- <file khác Manager cho phép; `components/` chỉ khi Manager ghi rõ>
Cần file khác ⇒ `## Blocked On`, không tự sửa.

## Đọc trước khi code — nguồn của lượt này (Codex: mở các file này như tài liệu)
- `.claude/skills/web-khuon/SKILL.md` — BẮT BUỘC: khuôn web thật của repo (React Query, RHF + zod, Router 7, i18n, theme,
  tự kiểm ba cỡ), trích từ code thật kèm file:dòng; thắng mọi tài liệu khác khi lệch.
- `.scratch/<key>/techlead.md` — bản thiết kế ĐÃ QUA CỔNG 4: endpoint, trường JSON, mã lỗi. Làm ĐÚNG nó; lệch ⇒ `## Blocked On`.
- Giao diện ĐÃ QUA CỔNG 3: `.impeccable/review/nghiem-thu.html` (concept ↔ bản cuối ở 3 cỡ) và bản lab
  `web/src/lab/<khu>` — chép bố cục, chữ, trạng thái từ đây; không tự thiết kế lại.
- `docs/features/<tên>.md` mục "Luật luôn đúng", `.scratch/<key>/qa-plan.md` — ca QA sẽ chạy trên màn bạn làm.
- Khi cần mẫu React/TypeScript chung: `.claude/skills/react-expert/SKILL.md`, `.claude/skills/typescript-pro/SKILL.md`
  (đọc khối "⛔ ĐỌC KHỐI NÀY TRƯỚC").

## Problem
<việc lượt này: màn nào, theo nghiem-thu + lab đã qua cổng 3, API theo techlead.md đã qua cổng 4;
hoặc "sửa lỗi <ID>: bước tái hiện …">

## Hard rules (chép từ CLAUDE.md)
- **KHÔNG `git add`, KHÔNG `git commit`, KHÔNG push.** Lý do: Sếp duyệt mọi lần gộp; Manager gom đúng file bạn báo.
- **MUST write tests**: Vitest + Testing Library, đặt cạnh file `*.test.tsx`. Không test = chưa xong. Sửa lỗi: test đỏ trước.
- **C13 i18n**: mọi câu người dùng đọc qua `t()`. Viết `locales/en/` TRƯỚC (gốc), rồi `vi/` — đủ khoá ở cả hai.
- C14: hiển thị lỗi server bằng mã `code` + `params` qua `useApiErrorText`, không in `detail`.
- **C15** component trong `web/src/components/` KHÔNG phụ thuộc runtime: không `useTranslation`, không đọc context —
  nhận chữ qua prop, nơi gọi dịch (từng làm chết cả 96 thẻ design system vì thẻ preview render ngoài app).
- **C16** màu gọi theo VAI TRÒ (`--primary`, `--success`, `--destructive`…), không gọi bảng màu thô (`--color-pitch`).
- **C17** không xuất module có side effect (`sonner`, `calendar`) từ `components/index.ts` — import thẳng từ file của chúng.
- **C18** `components/ui/` là code của shadcn: sửa được nhưng ghi chú vì sao ngay tại chỗ; ⛔ không bao giờ `npx shadcn add -o/--overwrite`.
- **C21** gọi server bằng React Query, form bằng React Hook Form + zod; không viết tay cặp `useState` pending/message.
- ⛔ **Không để câu mặc định (tiếng Anh) của zod lọt ra màn**: mọi kiểm tra trong schema mang message là KHOÁ i18n
  của mình, hiển thị qua `t()` — làm đúng mục 4 của `web-khuon`. Có test chứng minh ô sai hiện câu đã dịch.
- **C22** route khai ở `app/router.tsx` (data router React Router 7): page tải `lazy`, page nhận callback, không tự biết
  đường dẫn màn kế tiếp.
- **C23** mỗi feature mở đúng một cửa `features/<tên>/index.ts`; `pages/`, `app/` chỉ import `@/features/<tên>`.
- **C24** mỗi feature gọi server có `api/queries.ts`: một hàm sinh query key + hook `useXxx`/`useXxxMutation`; không gõ
  tay mảng key, page không gọi thẳng hàm `api/`. 401 bắt MỘT chỗ ở `app/queryClient.ts`, đừng bắt lại.
- Code chảy một chiều `components`+`api`+`lib` → `features` → `pages`; hai feature không import chéo (`npm run check:arch` canh).
- C12 code tiếng Anh, comment tiếng Việt · W8 không thêm dependency, không đổi thư viện — cần thì `## Blocked On`.
- **Tự kiểm ba cỡ 1440 / 820 / 390, KHÔNG tràn ngang** ở cả ba (`scrollWidth` của trang ≤ `clientWidth`; ô `grid`/`flex`
  chứa chữ dài cần `min-w-0`) — cách đo trong `web-khuon`. Chữ nhỏ, dày thông tin; sáng và tối đều đọc được.

## Acceptance Criteria
- [ ] `cd web && npm run format:check && npm run lint && npm run check:arch && npm run check:diagrams && npm test && npm run build` xanh
- [ ] Có test cho hành vi mới/đổi ở tầng bắt được lỗi (không cần tăng số test cho thay đổi CSS/chữ)
- [ ] Không chuỗi hiển thị cắm cứng (grep chuỗi tiếng Việt/Anh trong `.tsx` mới); khoá có ở cả `en/` lẫn `vi/`
- [ ] Không tràn ngang ở 1440 / 820 / 390 (ghi cách đã đo và số đo vào báo cáo)

## Before You Report Done
Viết `.scratch/<key>/reports/dev-web.md` (ghi đè bản cũ): danh sách ĐẦY ĐỦ file tạo/sửa, lệnh + số tóm tắt,
chỗ còn nghi ngờ, `## Blocked On`. Dán `git status --porcelain`. Dòng CUỐI CÙNG đúng là:

LANE-DONE dev-web
