# Lane dev-web — phòng <KEY>: <tên tính năng>

Worktree: `<đường dẫn worktree>` · nhánh `phong/<key>` · hồ sơ phòng `.scratch/<key>/`
Model: Claude sonnet. Gợi ý skill repo: `react-expert`, `typescript-pro`.

**Bạn LÀ lane, không phải phiên điều phối.** Tự triển khai mọi việc trong brief này; KHÔNG mở phiên con, KHÔNG tách việc
sang lane cmux/Orca, kể cả khi file luật chung (`AGENTS.md`, `CLAUDE.md` toàn máy) bảo hãy tách việc nhiều file.

## Files You May Edit
- `web/src/features/<tên>/**`, `web/src/pages/<…>.tsx`, `web/src/app/router.tsx` (chỉ thêm route của tính năng)
- `web/src/locales/en/<…>.json`, `web/src/locales/vi/<…>.json`
- `.scratch/<key>/reports/dev-web.md`
- <file khác Manager cho phép; `components/` chỉ khi Manager ghi rõ>
Cần file khác ⇒ `## Blocked On`, không tự sửa.

## Problem
<việc lượt này: màn nào, theo nghiem-thu đã qua cổng 3 (`.impeccable/review/nghiem-thu.html`, bản lab `web/src/lab/<khu>`),
API theo `.scratch/<key>/techlead.md`; hoặc "sửa lỗi <ID>: bước tái hiện …">

## Hard rules (chép từ CLAUDE.md)
- **KHÔNG `git add`, KHÔNG `git commit`, KHÔNG push.** Lý do: Sếp duyệt mọi lần gộp; Manager gom đúng file bạn báo.
- **MUST write tests**: Vitest + Testing Library, đặt cạnh file `*.test.tsx`. Không test = chưa xong. Sửa lỗi: test đỏ trước.
- **C13 i18n**: mọi câu người dùng đọc qua `t()`. Viết `locales/en/` TRƯỚC (gốc), rồi `vi/` — đủ khoá ở cả hai.
- C14: hiển thị lỗi server bằng mã `code` + `params` qua `useApiErrorText`, không in `detail`.
- C15 `components/` không gọi `useTranslation`/context · C16 màu theo vai trò · C17 không xuất module side effect từ `components/index.ts`
- C18 `components/ui/` là của shadcn, không `--overwrite` · C21 React Query + React Hook Form + zod, không cặp `useState` pending/message
- C22 route ở `app/router.tsx`, page `lazy`, page nhận callback · C23 chỉ import `@/features/<tên>` từ `pages/`, `app/`
- C24 mỗi feature gọi server có `api/queries.ts` (hàm sinh query key + hook `useXxx`/`useXxxMutation`)
- Code chảy một chiều `components`+`api`+`lib` → `features` → `pages`; hai feature không import chéo.
- W8: không thêm dependency. Ba cỡ 1440 / 820 / 390; chữ nhỏ, dày thông tin; sáng và tối đều đọc được.

## Acceptance Criteria
- [ ] `cd web && npm run format:check && npm run lint && npm run check:arch && npm run check:diagrams && npm test && npm run build` xanh
- [ ] Số test TĂNG (ghi trước/sau)
- [ ] Không chuỗi hiển thị cắm cứng (grep chuỗi tiếng Việt/Anh trong `.tsx` mới)

## Before You Report Done
Viết `.scratch/<key>/reports/dev-web.md` (ghi đè bản cũ): danh sách ĐẦY ĐỦ file tạo/sửa, lệnh + số tóm tắt,
chỗ còn nghi ngờ, `## Blocked On`. Dán `git status --porcelain`. Dòng CUỐI CÙNG đúng là:

LANE-DONE dev-web
