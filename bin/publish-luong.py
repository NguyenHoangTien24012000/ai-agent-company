#!/usr/bin/env python3
"""Giữ thư mục luồng app đúng với app (Sếp chốt 27/10, 31/10). Thư ký chạy, Sếp không phải chạy gì.

Nguồn sơ đồ nằm trong git ở docs/luong/<slug>.json, đi cùng code của phòng; HTML để xem chỉ ở <repo>/.archify/luong-app/.

  publish-luong.py --check KEY WORKTREE   lúc phòng xin gộp: phòng đổi mảng nào mà chưa cập nhật sơ đồ của mảng đó?
  publish-luong.py KEY WORKTREE           lúc phòng gộp xong, TRƯỚC khi xoá worktree: chép sơ đồ, dựng lại mục lục
  publish-luong.py --index-only           chỉ dựng lại mục lục
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import re
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(os.environ.get('SPORTSHUB_REPO', '/Users/tien/Claude/sportshub'))
DEST = REPO / '.archify' / 'luong-app'
SOURCES = DEST / '.nguon.json'
FIRST_DRAWN = 'df9b4ac'    # bản main lúc vẽ lần đầu 16 sơ đồ (27/10)
SLUG = re.compile(r'^\d{2}-[a-z0-9-]+$')
# Mảng code ↔ sơ đồ của nó. Tên mảng ở server, web và hồ sơ tính năng có khi khác nhau nên ghi cả ba.
AREA_DIAGRAMS = {
    'auth': '01-dang-nhap', 'user': '02-ho-so', 'profile': '03-trang-toi', 'trang-toi': '03-trang-toi', 'team': '04-doi',
    'match': '05-tran-dau', 'lineup': '06-doi-hinh', 'season': '07-mua-giai', 'expense': '08-quy', 'sanction': '09-an-phat',
    'an-phat': '09-an-phat', 'challenge': '10-giao-luu', 'giao-luu': '10-giao-luu', 'viec-cua-ban': '11-viec-cua-ban',
    'hall': '12-phong-truyen-thong', 'media': '13-anh', 'location': '14-vi-tri', 'linkpreview': '15-the-xem-truoc',
    'the-xem-truoc': '15-the-xem-truoc',
}
AREA_PATH = re.compile(r'^(?:server/src/main/java/com/sportshub/([a-z]+)/|web/src/features/([a-z]+)/|docs/features/([a-z-]+)\.md$)')
NOT_BEHAVIOUR = re.compile(r'(\.test\.[a-z]+$|/testing/|/locales/)')


class UserError(Exception):
    pass


def git(worktree, *args):
    return subprocess.run(['git', '-C', str(worktree), *args], check=True, capture_output=True, text=True).stdout


def needed_diagrams(files):
    """slug → các file của phòng khiến sơ đồ đó cần xem lại."""
    needed = {}
    for name in files:
        match = AREA_PATH.match(name)
        slug = AREA_DIAGRAMS.get(next(filter(None, match.groups()), '')) if match else None
        if slug and not NOT_BEHAVIOUR.search(name):
            needed.setdefault(slug, []).append(name)
    return needed


def rendered_problem(worktree, slug):
    """HTML của phòng phải sinh từ đúng nguồn đang có: git tự gộp hai phòng không xung đột thì HTML vẫn là bản trước gộp."""
    folder = worktree / '.archify' / 'luong-app'
    source = worktree / 'docs' / 'luong' / f'{slug}.json'
    try:
        json.loads(source.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 'thiếu file nguồn hoặc JSON hỏng'
    try:
        receipt = json.loads((folder / f'{slug}.finalize.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 'chưa finalize'
    if not (folder / f'{slug}.html').exists():
        return 'chưa finalize'
    if receipt.get('specification', {}).get('sha256') != hashlib.sha256(source.read_bytes()).hexdigest():
        return 'HTML cũ hơn nguồn, finalize lại'
    return None


def on_room_branch(worktree):
    return git(worktree, 'rev-parse', 'HEAD') != git(worktree, 'rev-parse', 'main')


def check(key, worktree):
    """Máy chỉ biết mảng nào bị đụng, không biết luồng có đổi thật không ⇒ Techlead vẽ, hoặc ghi lý do một dòng ở KHONG-DOI.md."""
    if not on_room_branch(worktree):
        print('WORKTREE phải là nhánh của phòng và chưa gộp; diff rỗng thì không kiểm được gì.')
        return 2
    # --no-renames: chuyển file sang mảng khác thì mảng cũ cũng bị tính là đổi
    files = git(worktree, 'diff', '--no-renames', '--name-only', 'main...HEAD').split()
    room = worktree / '.scratch' / key.lower() / 'luong'
    drawn = {Path(name).stem for name in files if re.fullmatch(r'docs/luong/[^/]+\.json', name) and (worktree / name).exists()}
    try:
        waived = {line.split(':', 1)[0].strip() for line in (room / 'KHONG-DOI.md').read_text(encoding='utf-8').splitlines() if ':' in line}
    except OSError:
        waived = set()
    problems = [f'- {slug}: {problem}' for slug in sorted(drawn) if (problem := rendered_problem(worktree, slug))]
    for slug, names in sorted(needed_diagrams(files).items()):
        if slug not in drawn | waived:
            problems.append(f'- {slug}: đổi {", ".join(names[:3])}' + (f' và {len(names) - 3} file khác' if len(names) > 3 else ''))
    if not problems:
        print('Sơ đồ luồng: đủ.')
        return 0
    print('THIẾU sơ đồ luồng. Sửa docs/luong/<slug>.json rồi finalize, hoặc ghi "<slug>: lý do" vào .scratch/<key>/luong/KHONG-DOI.md nếu bước đi không đổi:')
    print('\n'.join(problems))
    return 1


def title_of(page: Path) -> str:
    match = re.search(r'<title>(.*?)</title>', page.read_text(encoding='utf-8', errors='replace'), re.S)
    # archify gắn "Diagram" (bản tiếng Việt: "Sơ đồ") vào <title>; mục lục chỉ cần tên luồng
    name = html.unescape(match.group(1).strip()) if match else page.stem
    return re.sub(r'^Sơ đồ\s+|\s+Diagram$', '', name)


def load_sources() -> dict:
    try:
        return json.loads(SOURCES.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def publish(key: str, worktree: Path) -> list[str]:
    """Kiểm hết rồi mới chép: sai một sơ đồ thì không chép sơ đồ nào."""
    if worktree.resolve() == REPO.resolve():
        raise UserError('WORKTREE phải là thư mục của phòng, không phải repo gốc.')
    folder = worktree / '.archify' / 'luong-app'
    slugs = sorted(page.stem for page in folder.glob('*.html') if SLUG.match(page.stem))
    problems = [f'{slug}: {problem}' for slug in slugs if (problem := rendered_problem(worktree, slug))]
    if problems:
        raise UserError('CHƯA CHÉP GÌ. ' + '; '.join(problems))
    sources = load_sources()
    today = dt.date.today().isoformat()
    commit = git(worktree, 'rev-parse', '--short', 'HEAD').strip()
    for slug in slugs:
        (DEST / slug).mkdir(parents=True, exist_ok=True)
        shutil.copy2(worktree / 'docs' / 'luong' / f'{slug}.json', DEST / slug / 'candidate.json')
        for extra in folder.glob(f'{slug}.*'):
            shutil.copy2(extra, DEST / extra.name)
        sources[slug] = {'room': key, 'date': today, 'commit': commit}
        SOURCES.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return slugs


def build_index() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    pages = sorted(p for p in DEST.glob('*.html') if p.name != 'index.html' and SLUG.match(p.stem))
    rows = [(p.stem, title_of(p), sources.get(p.stem, {})) for p in pages]
    lines = ['# Luồng app SportsHub', '',
             'Máy sinh bằng `~/sportshub-company/bin/publish-luong.py` — không sửa tay. Mỗi luồng: `<slug>.html` để xem,',
             'nguồn trong git ở `docs/luong/<slug>.json`. Mở `index.html` để bấm xem.', '',
             '| Slug | Luồng | Cập nhật bởi | Ngày | Đúng với code bản |', '|---|---|---|---|---|']
    lines += [f"| `{slug}` | {name} | {meta.get('room', 'vẽ lần đầu')} | {meta.get('date', '2026-10-27')} | `{meta.get('commit', FIRST_DRAWN)}` |"
              for slug, name, meta in rows]
    (DEST / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    items = '\n'.join(
        f'<li><a href="{slug}.html"><span class="n">{slug[:2]}</span>{html.escape(name)}</a>'
        f'<small>{html.escape(meta.get("room", "vẽ lần đầu"))} · {meta.get("date", "2026-10-27")} · bản {meta.get("commit", FIRST_DRAWN)}</small></li>'
        for slug, name, meta in rows)
    (DEST / 'index.html').write_text(f'''<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Luồng app SportsHub</title>
<style>
:root{{--bg:#f7f7f5;--fg:#1c2721;--muted:#5d665f;--line:#dcdcd6;--card:#fff;--accent:#b8862b}}
@media (prefers-color-scheme:dark){{:root{{--bg:#121714;--fg:#e8e6df;--muted:#9aa39c;--line:#2a332d;--card:#1a211d}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:32px 16px}} h1{{font-size:22px;margin:0 0 4px}}
p{{color:var(--muted);margin:0 0 20px}} ul{{list-style:none;margin:0;padding:0;border:1px solid var(--line);border-radius:12px;background:var(--card)}}
li{{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 16px;border-top:1px solid var(--line)}}
li:first-child{{border-top:0}} a{{color:var(--fg);text-decoration:none;font-weight:600}} a:hover{{color:var(--accent)}}
.n{{display:inline-block;width:2.2em;color:var(--accent);font-variant-numeric:tabular-nums}} small{{color:var(--muted);white-space:nowrap}}
</style></head><body><main><h1>Luồng app SportsHub</h1>
<p>{len(rows)} luồng · đúng với code trên main — cập nhật mỗi khi một phòng gộp.</p><ul>
{items}
</ul></main></body></html>
''', encoding='utf-8')
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('key', nargs='?')
    parser.add_argument('worktree', nargs='?')
    parser.add_argument('--index-only', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        if not (args.key and args.worktree):
            parser.error('--check cần KEY và WORKTREE')
        sys.exit(check(args.key, Path(args.worktree)))
    if not args.index_only:
        if not (args.key and args.worktree):
            parser.error('cần KEY và WORKTREE, hoặc --index-only')
        try:
            done = publish(args.key, Path(args.worktree))
        except UserError as exc:
            print(exc, file=sys.stderr)
            sys.exit(1)
        print(f"chép {len(done)} sơ đồ: {', '.join(done) or 'phòng không đổi sơ đồ nào'}")
    print(f'mục lục: {build_index()} luồng → {DEST / "index.html"}')


if __name__ == '__main__':
    main()
