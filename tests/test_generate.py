"""generate.py の試験。本番には何も送らない。一時フォルダの中だけで動く。
実行: python3 -m unittest discover -s tests -v
"""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('LUMOUS_DATA', '/nonexistent/user-data.json')
import generate  # noqa: E402  (importしただけでは何も書き出さない)

FLOW = 'graph TD\n  A-->B'
HTML = ('<p>本文</p><div class="image-wrapper"><img src="x.png">'
        '<button class="img-delete" onclick="this.parentElement.remove()">×</button></div>'
        '<div class="video-wrapper"><video src="old" controls data-video-id="vid_1"></video>'
        '<button class="vid-delete" onclick="this.parentElement.remove()">×</button></div>'
        '<pre class="mermaid">graph TD\n  A--&gt;B</pre>')


class Pure(unittest.TestCase):
    def test_delete_buttons_removed(self):
        out = generate.strip_editor_buttons(HTML)
        self.assertNotIn('img-delete', out)
        self.assertNotIn('vid-delete', out)
        self.assertIn('<img src="x.png">', out)

    def test_video_known_and_unknown(self):
        h = '<video controls data-video-id="vid_1"></video><video data-video-id="vid_9"></video>'
        out = generate.inject_video_src(h, {'vid_1': 'vid_1.mp4'})
        self.assertIn('src="videos/vid_1.mp4"', out)
        self.assertIn('動画未取得: vid_9', out)

    def test_no_duplicate_flowchart(self):
        m = {'title': 'T', 'html': HTML, 'mermaidCodes': [FLOW, 'graph TD\n  X-->Y']}
        page = generate.render_manual(m, 1, {})
        self.assertEqual(page.count('A--&gt;B'), 1)      # すでに本文にあるものは重ねない
        self.assertEqual(page.count('X--&gt;Y'), 1)      # 無いものは末尾に足す

    def test_none_fields_do_not_crash(self):
        generate.render_manual({'title': 'T', 'html': '', 'date': None}, 1, {})


class EndToEnd(unittest.TestCase):
    def run_gen(self, data):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        (d / 'data.json').write_text(json.dumps(data), encoding='utf-8')
        out = d / 'out'
        out.mkdir()
        env = dict(os.environ, LUMOUS_DATA=str(d / 'data.json'), LUMOUS_OUT=str(out))
        r = subprocess.run([sys.executable, str(ROOT / 'generate.py')], env=env,
                           capture_output=True, text=True)
        return r, out

    def test_index_link_is_url_encoded_and_date_filled(self):
        r, out = self.run_gen({'savedManuals': [{'title': 'A#B?C(1)', 'html': 'x', 'date': '2026/1/1'}]})
        self.assertEqual(r.returncode, 0, r.stderr)
        idx = (out / 'index.html').read_text(encoding='utf-8')
        self.assertIn('%23', idx)                        # # がそのまま入ると壊れる
        self.assertNotIn('最終更新: </p>', idx)           # 空欄にならない

    def test_zero_manuals_does_not_overwrite(self):
        r, out = self.run_gen({'savedManuals': []})
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(list(out.iterdir()), [])

    def test_missing_data_file_stops_clearly(self):
        env = dict(os.environ, LUMOUS_DATA='/nonexistent/x.json', LUMOUS_OUT=tempfile.gettempdir())
        r = subprocess.run([sys.executable, str(ROOT / 'generate.py')], env=env,
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('データファイルがありません', r.stderr)


class UpdateSh(unittest.TestCase):
    def test_new_untracked_file_counts_as_change(self):
        """新しいファイル(動画など)だけ増えたとき、「変更なし」と言って終わらないこと。
        送り先は一時フォルダの空っぽの bare リポジトリ。本物の GitHub には行かない。"""
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            sh = lambda *a, **k: subprocess.run(a, check=True, capture_output=True, text=True, **k)
            sh('git', 'init', '-q', '--bare', str(t / 'remote.git'))
            work = t / 'work'
            sh('git', 'clone', '-q', str(t / 'remote.git'), str(work))
            for f in ('update.sh', 'generate.py'):
                (work / f).write_bytes((ROOT / f).read_bytes())
            (work / 'data.json').write_text(json.dumps({'savedManuals': [{'title': 'T', 'html': 'x'}]}))
            env = dict(os.environ, LUMOUS_DATA=str(work / 'data.json'), LUMOUS_OUT=str(work),
                       BRANCH='test-branch', GIT_CONFIG_GLOBAL='/dev/null')
            sh('git', '-C', str(work), 'checkout', '-q', '-b', 'test-branch')
            r1 = subprocess.run(['bash', 'update.sh'], cwd=work, env=env, capture_output=True, text=True)
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            # 2回目: 何も変わらない
            r2 = subprocess.run(['bash', 'update.sh'], cwd=work, env=env, capture_output=True, text=True)
            self.assertIn('変更なし', r2.stdout)
            # 3回目: 動画だけ新しく追加(git に未登録)
            (work / 'videos').mkdir()
            (work / 'videos' / 'new.mp4').write_bytes(b'x')
            r3 = subprocess.run(['bash', 'update.sh'], cwd=work, env=env, capture_output=True, text=True)
            self.assertNotIn('変更なし', r3.stdout)
            self.assertEqual(r3.returncode, 0, r3.stdout + r3.stderr)


if __name__ == '__main__':
    unittest.main()
