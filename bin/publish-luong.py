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


def check(key, worktree):
    """Máy chỉ biết mảng nào bị đụng, không biết luồng có đổi thật không ⇒ Techlead vẽ, hoặc ghi lý do một dòng ở KHONG-DOI.md."""
    files = git(worktree, 'diff', '--name-only', 'main...HEAD').split()
    room = worktree / '.scratch' / key.lower() / 'luong'
    drawn = {Path(name).stem for name in files if re.fullmatch(r'docs/luong/[^/]+\.json', name)}
    drawn |= {page.stem for page in room.glob('*.html')}
    try:
        waived = {line.split(':', 1)[0].strip() for line in (room / 'KHONG-DOI.md').read_text(encoding='utf-8').splitlines() if ':' in line}
    except OSError:
        waived = set()
    missing = {slug: names for slug, names in needed_diagrams(files).items() if slug not in drawn | waived}
    if not missing:
        print('Sơ đồ luồng: đủ.')
        return 0
    print('THIẾU sơ đồ luồng. Vẽ lại, hoặc ghi "<slug>: lý do" vào .scratch/<key>/luong/KHONG-DOI.md nếu bước đi không đổi:')
    for slug, names in sorted(missing.items()):
        print(f'- {slug}: đổi {", ".join(names[:3])}' + (f' và {len(names) - 3} file khác' if len(names) > 3 else ''))
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
    old = worktree / '.scratch' / key.lower() / 'luong'      # cách cũ, cho phòng mở trước khi nguồn vào git
    new = worktree / '.archify' / 'luong-app'
    if new.resolve() == DEST.resolve():
        return []
    sources = load_sources()
    today = dt.date.today().isoformat()
    commit = git(worktree, 'rev-parse', '--short', 'HEAD').strip()
    # `.goc.json` (cách cũ, Techlead ghi): slug → sha256 của luong-app/<slug>/candidate.json lúc chép về sửa. Hai phòng cùng
    # sửa một luồng ⇒ phòng gộp sau phải vẽ lại trên bản của phòng gộp trước, không đè mất nó. Nguồn trong git thì git lo.
    try:
        base = json.loads((old / '.goc.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        base = {}
    done, stale = [], []
    for page in sorted(list(old.glob('*.html')) + list(new.glob('*.html'))):
        slug, folder = page.stem, page.parent
        if not SLUG.match(slug):
            continue
        current = DEST / slug / 'candidate.json'
        if folder == old and current.exists() and base.get(slug) != hashlib.sha256(current.read_bytes()).hexdigest():
            stale.append(slug)
            continue
        DEST.mkdir(parents=True, exist_ok=True)
        (DEST / slug).mkdir(exist_ok=True)
        tracked = worktree / 'docs' / 'luong' / f'{slug}.json'
        origin = tracked if tracked.exists() else folder / slug / 'candidate.json'
        if origin.exists():
            data = json.loads(origin.read_text(encoding='utf-8'))
            # meta.output của phòng có thể trỏ vào .scratch — đưa về chỗ thật để lần sửa sau finalize đúng đích
            data.setdefault('meta', {})['output'] = f'.archify/luong-app/{slug}.html'
            current.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for extra in folder.glob(f'{slug}.*'):
            shutil.copy2(extra, DEST / extra.name)
        sources[slug] = {'room': key, 'date': today, 'commit': commit}
        done.append(slug)
    if done:
        SOURCES.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for slug in stale:
        print(f'CHƯA CHÉP {slug}: luong-app đã đổi sau khi phòng chép về (hoặc thiếu .goc.json) — Techlead vẽ lại '
              f'trên bản mới rồi chạy lại', file=sys.stderr)
    return done


def build_index() -> int:
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
        done = publish(args.key, Path(args.worktree))
        print(f"chép {len(done)} sơ đồ: {', '.join(done) or 'phòng không có .scratch/<key>/luong/'}")
    print(f'mục lục: {build_index()} luồng → {DEST / "index.html"}')


if __name__ == '__main__':
    main()
