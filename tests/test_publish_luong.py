"""Kiểm thử bin/publish-luong.py bằng repo git tạm, không chạm thư mục luồng thật."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'bin/publish-luong.py'


def git(cwd, *args):
    return subprocess.run(['git', '-C', str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


class PublishLuongTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name) / 'repo'
        self.repo.mkdir()
        git(self.repo, 'init', '-q', '-b', 'main')
        git(self.repo, 'config', 'user.email', 't@example.test')
        git(self.repo, 'config', 'user.name', 't')
        self.write('README.md', 'x')
        self.commit('goc')
        git(self.repo, 'switch', '-q', '-c', 'phong/x')

    def write(self, relative, text):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def commit(self, message):
        git(self.repo, 'add', '-A')
        git(self.repo, 'commit', '-q', '-m', message)

    def draw(self, slug, rendered_from=None, content=None, ok=True):
        source = content or json.dumps({'meta': {'output': f'.archify/luong-app/{slug}.html'}})
        page = f'<title>Sơ đồ {slug}</title><!-- {source} -->'
        self.write(f'docs/luong/{slug}.json', source)
        self.write(f'.archify/luong-app/{slug}.html', page)
        self.write(f'.archify/luong-app/{slug}.finalize.json', json.dumps({
            'ok': ok,
            'specification': {'sha256': hashlib.sha256((rendered_from or source).encode()).hexdigest()},
            'artifact': {'sha256': hashlib.sha256(page.encode()).hexdigest()},
        }))

    def merge_to_main(self):
        branch = git(self.repo, 'rev-parse', 'HEAD')
        git(self.repo, 'switch', '-q', 'main')
        git(self.repo, 'merge', '-q', '--ff-only', branch)
        git(self.repo, 'switch', '-q', 'phong/x')

    def run_script(self, *args):
        env = dict(os.environ, SPORTSHUB_REPO=str(self.repo))
        return subprocess.run([sys.executable, str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=20)

    def check(self):
        return self.run_script('--check', 'X', str(self.repo))

    def test_check_passes_when_code_touched_nothing_about_flows(self):
        self.write('web/src/components/ui/button.tsx', 'x')
        self.commit('kieu nut')
        self.assertEqual(self.check().returncode, 0)

    def test_check_fails_when_a_feature_area_changed_without_its_diagram(self):
        self.write('server/src/main/java/com/sportshub/media/service/MediaService.java', 'x')
        self.write('web/src/features/expense/Fund.tsx', 'x')
        self.commit('doi')
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('13-anh', result.stdout)
        self.assertIn('08-quy', result.stdout)

    def test_tests_and_locales_do_not_count_as_flow_changes(self):
        self.write('web/src/features/expense/Fund.test.tsx', 'x')
        self.write('server/src/test/java/com/sportshub/media/MediaTest.java', 'x')
        self.commit('test')
        self.assertEqual(self.check().returncode, 0)

    def test_check_passes_when_diagram_source_changed_or_room_explains_why_not(self):
        self.write('web/src/features/expense/Fund.tsx', 'x')
        self.write('web/src/features/media/Crop.tsx', 'x')
        self.draw('08-quy')
        self.commit('doi')
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('08-quy', result.stdout)
        self.write('.scratch/x/luong/KHONG-DOI.md', '13-anh: chỉ đổi chữ nút, không đổi bước đi\n')
        self.assertEqual(self.check().returncode, 0)

    def test_check_fails_when_source_changed_but_html_missing_or_older(self):
        self.write('docs/luong/08-quy.json', '{}')
        self.commit('quen finalize')
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('chưa finalize', result.stdout)
        self.draw('08-quy', rendered_from='ban truoc khi gop')
        self.commit('html cu')
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('finalize lại', result.stdout)

    def test_check_counts_both_areas_when_a_file_moves(self):
        self.write('web/src/features/expense/Fund.tsx', 'x' * 200)
        self.commit('truoc')
        git(self.repo, 'switch', '-q', 'main')
        git(self.repo, 'merge', '-q', '--ff-only', 'phong/x')
        git(self.repo, 'switch', '-q', 'phong/x')
        (self.repo / 'web/src/features/media').mkdir()
        git(self.repo, 'mv', 'web/src/features/expense/Fund.tsx', 'web/src/features/media/Fund.tsx')
        self.commit('chuyen')
        result = self.check()
        self.assertIn('08-quy', result.stdout)
        self.assertIn('13-anh', result.stdout)

    def test_check_refuses_worktree_already_on_main(self):
        git(self.repo, 'switch', '-q', 'main')
        self.assertEqual(self.run_script('--check', 'X', str(self.repo)).returncode, 2)

    def worktree_with(self, *slugs, stale=()):
        for slug in slugs:
            self.draw(slug, rendered_from='cu' if slug in stale else None)
        self.commit('so do')
        self.merge_to_main()
        worktree = Path(self.repo.parent) / 'wt'
        git(self.repo, 'worktree', 'add', '-q', str(worktree), 'HEAD')
        shutil.rmtree(self.repo / '.archify')
        return worktree

    def test_publish_copies_room_diagram_and_records_code_version(self):
        worktree = self.worktree_with('08-quy')
        sha = git(self.repo, 'rev-parse', '--short', 'HEAD')
        result = self.run_script('X', str(worktree))
        self.assertEqual(result.returncode, 0, result.stderr)
        destination = self.repo / '.archify/luong-app'
        self.assertIn('08-quy', (destination / '08-quy.html').read_text(encoding='utf-8'))
        self.assertEqual(json.loads((destination / '08-quy/candidate.json').read_text())['meta']['output'],
                         '.archify/luong-app/08-quy.html')
        self.assertIn(sha, (destination / 'README.md').read_text(encoding='utf-8'))
        self.assertIn(sha, (destination / 'index.html').read_text(encoding='utf-8'))
        self.assertEqual(self.run_script('X', str(worktree)).returncode, 0, 'chạy lại vẫn phải đúng')

    def test_publish_copies_good_diagrams_and_fails_listing_the_rest(self):
        worktree = self.worktree_with('08-quy', '09-an-phat', stale=('09-an-phat',))
        result = self.run_script('X', str(worktree))
        self.assertEqual(result.returncode, 1)
        self.assertIn('09-an-phat', result.stderr)
        self.assertTrue((self.repo / '.archify/luong-app/08-quy.html').exists())
        self.assertFalse((self.repo / '.archify/luong-app/09-an-phat.html').exists())

    def test_finalize_that_failed_never_passes(self):
        self.draw('08-quy', ok=False)
        self.commit('finalize truot')
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('finalize', result.stdout)
        self.merge_to_main()
        worktree = self.repo.parent / 'wt'
        git(self.repo, 'worktree', 'add', '-q', str(worktree), 'HEAD')
        self.assertEqual(self.run_script('X', str(worktree)).returncode, 1)
        self.assertFalse((self.repo / '.archify/luong-app/08-quy/candidate.json').exists())

    def test_html_edited_after_finalize_does_not_pass(self):
        self.draw('08-quy')
        self.write('.archify/luong-app/08-quy.html', '<title>CU</title>')
        self.commit('sua tay')
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('08-quy', result.stdout)

    def test_receipt_with_wrong_shape_is_reported_not_a_crash(self):
        self.draw('08-quy')
        self.commit('so do')
        for bad in ('[]', '{"specification": null}', '{"ok": true, "specification": "x"}'):
            self.write('.archify/luong-app/08-quy.finalize.json', bad)
            result = self.check()
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_check_refuses_branch_already_merged_or_behind_main(self):
        self.write('web/src/features/expense/Fund.tsx', 'x')
        self.commit('doi')
        self.merge_to_main()
        git(self.repo, 'switch', '-q', 'main')
        self.write('README.md', 'main di tiep')
        self.commit('main di tiep')
        git(self.repo, 'switch', '-q', 'phong/x')
        self.assertEqual(self.check().returncode, 2)

    def test_uncommitted_source_is_not_what_gets_checked(self):
        self.draw('08-quy')
        self.commit('so do')
        self.draw('08-quy', content='{"v": "ban chua commit"}')
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('finalize', result.stdout)

    def test_waiver_needs_a_reason(self):
        self.write('web/src/features/expense/Fund.tsx', 'x')
        self.write('.scratch/x/luong/KHONG-DOI.md', '08-quy:\n')
        self.commit('doi')
        self.assertEqual(self.check().returncode, 1)
        self.write('.scratch/x/luong/KHONG-DOI.md', '08-quy: chỉ đổi chữ\n')
        self.assertEqual(self.check().returncode, 0)

    def test_route_change_needs_a_diagram_or_a_reason(self):
        self.write('web/src/app/router.tsx', 'x')
        self.commit('doi route')
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('router', result.stdout)
        self.write('.scratch/x/luong/KHONG-DOI.md', 'router: chỉ đổi cách tải trang\n')
        self.assertEqual(self.check().returncode, 0)

    def test_publish_refuses_room_not_merged_yet(self):
        self.draw('08-quy')
        self.commit('so do')
        worktree = self.repo.parent / 'wt'
        git(self.repo, 'worktree', 'add', '-q', str(worktree), 'HEAD')
        result = self.run_script('X', str(worktree))
        self.assertEqual(result.returncode, 1)
        self.assertIn('chưa gộp', result.stderr)

    def test_late_publish_does_not_overwrite_a_newer_diagram(self):
        room_b = self.worktree_with('08-quy')
        self.assertEqual(self.run_script('B', str(room_b)).returncode, 0)
        self.draw('08-quy', content='{"v": "A moi"}')
        self.commit('phong A sua')
        self.merge_to_main()
        room_a = self.repo.parent / 'wt-a'
        git(self.repo, 'worktree', 'add', '-q', str(room_a), 'HEAD')
        self.assertEqual(self.run_script('A', str(room_a)).returncode, 0)
        destination = self.repo / '.archify/luong-app/08-quy/candidate.json'
        self.assertEqual(json.loads(destination.read_text())['v'], 'A moi')
        result = self.run_script('B', str(room_b))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(destination.read_text())['v'], 'A moi')

    def test_publish_says_so_when_source_changed_but_html_is_gone(self):
        worktree = self.worktree_with('08-quy')
        shutil.rmtree(worktree / '.archify')
        result = self.run_script('X', str(worktree))
        self.assertEqual(result.returncode, 1)
        self.assertIn('08-quy', result.stderr)
        self.assertNotIn('đã đúng với main', result.stdout)

    def published(self):
        worktree = self.worktree_with('08-quy')
        self.assertEqual(self.run_script('X', str(worktree)).returncode, 0)
        return worktree, self.repo / '.archify/luong-app'

    def test_copy_failed_halfway_is_redone_next_run(self):
        worktree = self.worktree_with('08-quy')
        destination = self.repo / '.archify/luong-app'
        destination.mkdir(parents=True)
        (destination / '08-quy.html').write_text('cu', encoding='utf-8')
        (destination / '08-quy.html').chmod(0o444)  # chép HTML sẽ lỗi
        failed = self.run_script('X', str(worktree))
        self.assertEqual(failed.returncode, 1)
        self.assertNotIn('Traceback', failed.stderr)
        self.assertFalse((destination / '08-quy/candidate.json').exists())
        (destination / '08-quy.html').chmod(0o644)
        result = self.run_script('X', str(worktree))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('chép 1', result.stdout)
        self.assertTrue((destination / '08-quy.html').is_file())

    def test_version_of_copied_diagram_is_kept_when_a_later_one_fails(self):
        worktree = self.worktree_with('08-quy', '09-an-phat')
        destination = self.repo / '.archify/luong-app'
        destination.mkdir(parents=True)
        (destination / '09-an-phat.html').write_text('cu', encoding='utf-8')
        (destination / '09-an-phat.html').chmod(0o444)
        self.assertEqual(self.run_script('X', str(worktree)).returncode, 1)
        (destination / '09-an-phat.html').chmod(0o644)
        self.assertIn('08-quy', (destination / '.nguon.json').read_text(encoding='utf-8'))

    def test_shown_html_gone_or_replaced_is_copied_again(self):
        worktree, destination = self.published()
        (destination / '08-quy.html').unlink()
        self.assertEqual(self.run_script('X', str(worktree)).returncode, 0)
        self.assertTrue((destination / '08-quy.html').exists())
        (destination / '08-quy.html').write_text('<title>CU</title>', encoding='utf-8')
        self.assertEqual(self.run_script('X', str(worktree)).returncode, 0)
        self.assertIn('08-quy', (destination / '08-quy.html').read_text(encoding='utf-8'))

    def test_diagram_removed_from_main_leaves_the_index(self):
        worktree, destination = self.published()
        git(self.repo, 'rm', '-q', 'docs/luong/08-quy.json')
        self.draw('17-media')
        self.commit('doi ten')
        self.merge_to_main()
        room = self.repo.parent / 'wt-doi-ten'
        git(self.repo, 'worktree', 'add', '-q', str(room), 'HEAD')
        self.assertEqual(self.run_script('X', str(room)).returncode, 0)
        self.assertFalse((destination / '08-quy.html').exists())
        self.assertFalse((destination / '08-quy').exists())
        self.assertNotIn('08-quy', (destination / 'index.html').read_text(encoding='utf-8'))
        self.assertNotIn('08-quy', (destination / '.nguon.json').read_text(encoding='utf-8'))

    def test_diagram_nobody_holds_is_listed_then_fixed_by_finalizing_at_repo_root(self):
        worktree, destination = self.published()
        # Sửa thẳng trên main: không phòng nào có HTML, phòng khác dọn sau không được kẹt mãi
        self.draw('08-quy', content='{"v": "sua tren main"}')
        room = self.repo.parent / 'wt-khac'
        page = (self.repo / '.archify/luong-app/08-quy.html').read_bytes()
        receipt = (self.repo / '.archify/luong-app/08-quy.finalize.json').read_bytes()
        (self.repo / '.archify/luong-app/08-quy.html').write_text('x', encoding='utf-8')
        git(self.repo, 'add', 'docs/luong/08-quy.json')
        git(self.repo, 'commit', '-q', '-m', 'sua tren main')
        self.merge_to_main()
        git(self.repo, 'worktree', 'add', '-q', str(room), 'HEAD')
        result = self.run_script('Y', str(room))
        self.assertEqual(result.returncode, 1)
        self.assertIn('08-quy', result.stderr)
        self.assertNotIn('đã đúng với main', result.stdout)
        (destination / '08-quy.html').write_bytes(page)
        (destination / '08-quy.finalize.json').write_bytes(receipt)
        result = self.run_script('Y', str(room))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((destination / '08-quy/candidate.json').read_text())['v'], 'sua tren main')
        self.assertIn(git(self.repo, 'rev-parse', '--short', 'main'), (destination / 'README.md').read_text(encoding='utf-8'))

    def test_late_room_cannot_copy_old_html_even_before_newer_room_published(self):
        room_b = self.worktree_with('08-quy')
        self.draw('08-quy', content='{"v": "A moi"}')
        self.commit('phong A sua')
        self.merge_to_main()
        room_a = self.repo.parent / 'wt-a'
        git(self.repo, 'worktree', 'add', '-q', str(room_a), 'HEAD')
        (self.repo / '.archify/luong-app/08-quy.finalize.json').unlink()
        self.assertEqual(self.run_script('B', str(room_b)).returncode, 1)
        self.assertFalse((self.repo / '.archify/luong-app/08-quy/candidate.json').exists())
        self.assertEqual(self.run_script('A', str(room_a)).returncode, 0)
        self.assertEqual(self.run_script('B', str(room_b)).returncode, 0)
        candidate = json.loads((self.repo / '.archify/luong-app/08-quy/candidate.json').read_text())
        self.assertEqual(candidate['v'], 'A moi')

    def test_new_diagram_on_main_the_room_lacks_is_not_skipped(self):
        room = self.worktree_with('08-quy')
        self.draw('09-an-phat')
        self.commit('phong khac them')
        self.merge_to_main()
        (self.repo / '.archify/luong-app/09-an-phat.finalize.json').unlink()
        result = self.run_script('X', str(room))
        self.assertEqual(result.returncode, 1)
        self.assertIn('09-an-phat', result.stderr)

    def test_redeliver_after_finalize_still_counts(self):
        self.draw('08-quy')
        page = '<title>sau deliver</title>'
        self.write('.archify/luong-app/08-quy.html', page)
        source = (self.repo / 'docs/luong/08-quy.json').read_bytes()
        self.write('.archify/luong-app/08-quy.delivery.json', json.dumps({
            'artifact': {'sha256': hashlib.sha256(page.encode()).hexdigest()},
            'specification': {'sha256': hashlib.sha256(source).hexdigest()},
        }))
        self.commit('deliver lai')
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_delivered_from_a_draft_outside_git_does_not_pass(self):
        self.draw('08-quy')
        page = '<title>ban nhap</title>'
        self.write('.archify/luong-app/08-quy.html', page)
        self.write('.archify/luong-app/08-quy.delivery.json', json.dumps({
            'artifact': {'sha256': hashlib.sha256(page.encode()).hexdigest()},
            'specification': {'sha256': hashlib.sha256(b'ban nhap').hexdigest()},
        }))
        self.commit('deliver ban nhap')
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('finalize', result.stdout)

    def test_wrong_worktree_never_wipes_the_shown_diagrams(self):
        worktree, destination = self.published()
        (worktree / 'server').mkdir()
        other = self.repo.parent / 'repo-khac'
        other.mkdir()
        git(other, 'init', '-q', '-b', 'main')
        git(other, 'config', 'user.email', 't@example.test')
        git(other, 'config', 'user.name', 't')
        (other / 'README.md').write_text('x', encoding='utf-8')
        git(other, 'add', '-A')
        git(other, 'commit', '-q', '-m', 'goc')
        for wrong in (worktree / 'server', other):
            result = self.run_script('X', str(wrong))
            self.assertEqual(result.returncode, 1, str(wrong))
            self.assertTrue((destination / '08-quy.html').exists(), str(wrong))
        git(self.repo, 'rm', '-q', '-r', 'docs/luong')
        self.commit('xoa het')
        self.merge_to_main()
        room = self.repo.parent / 'wt-rong'
        git(self.repo, 'worktree', 'add', '-q', str(room), 'HEAD')
        self.assertEqual(self.run_script('X', str(room)).returncode, 1)
        self.assertTrue((destination / '08-quy.html').exists())

    def test_check_rejects_badly_named_diagram_that_publish_would_ignore(self):
        self.draw('17_doi-hinh')
        self.commit('sai ten')
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('17_doi-hinh', result.stdout)

    def test_other_files_in_source_folder_are_ignored(self):
        self.write('docs/luong/09-ghi-chu.md', 'x')
        room = self.worktree_with('08-quy')
        self.assertEqual(self.run_script('X', str(room)).returncode, 0)

    def test_missing_worktree_is_not_reported_as_not_merged(self):
        result = self.run_script('X', str(self.repo.parent / 'khong-co'))
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('chưa gộp', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_index_only_works_on_a_machine_without_the_folder(self):
        self.assertEqual(self.run_script('--index-only').returncode, 0)


if __name__ == '__main__':
    unittest.main()
