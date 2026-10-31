"""Kiểm thử bin/publish-luong.py bằng repo git tạm, không chạm thư mục luồng thật."""

import json
import os
from pathlib import Path
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
        self.write('docs/luong/08-quy.json', '{}')
        self.commit('doi')
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('08-quy', result.stdout)
        self.write('.scratch/x/luong/KHONG-DOI.md', '13-anh: chỉ đổi chữ nút, không đổi bước đi\n')
        self.assertEqual(self.check().returncode, 0)

    def test_publish_copies_room_diagram_and_records_code_version(self):
        self.write('docs/luong/08-quy.json', json.dumps({'meta': {'output': '.archify/luong-app/08-quy.html'}}))
        self.write('.archify/luong-app/08-quy.html', '<title>Sơ đồ Quỹ đội</title>')
        self.commit('so do')
        worktree = Path(self.repo.parent) / 'wt'
        git(self.repo, 'worktree', 'add', '-q', str(worktree), 'HEAD')
        sha = git(self.repo, 'rev-parse', '--short', 'HEAD')
        (self.repo / '.archify/luong-app/08-quy.html').unlink()
        result = self.run_script('X', str(worktree))
        self.assertEqual(result.returncode, 0, result.stderr)
        destination = self.repo / '.archify/luong-app'
        self.assertIn('Quỹ đội', (destination / '08-quy.html').read_text(encoding='utf-8'))
        self.assertEqual(json.loads((destination / '08-quy/candidate.json').read_text())['meta']['output'],
                         '.archify/luong-app/08-quy.html')
        readme = (destination / 'README.md').read_text(encoding='utf-8')
        self.assertIn(sha, readme)
        self.assertIn(sha, (destination / 'index.html').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
