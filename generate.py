#!/usr/bin/env python3
"""user-data.json から複数マニュアルの静的サイトを生成"""
import json, re, html, os, sys, datetime
from pathlib import Path
from urllib.parse import quote

# 場所は環境変数で変えられる。決めなければ、今までと同じ場所を使う。
DATA = Path(os.environ.get('LUMOUS_DATA', '/home/ryota/lumous-manual-diagram/user-data.json'))
OUT = Path(os.environ.get('LUMOUS_OUT', '/home/ryota/lumous-manual-public'))

CSS = """
body { font-family: -apple-system, "Hiragino Sans", "Yu Gothic", sans-serif; max-width: 980px; margin: 0 auto; padding: 24px; line-height: 1.7; color: #333; background: #f8f9fa; }
h1 { color: #685021; border-bottom: 3px solid #c39f59; padding-bottom: 8px; }
h2 { color: #8b6f47; margin-top: 28px; }
h3 { color: #685021; }
.card { background: white; border-radius: 12px; padding: 24px; margin: 16px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.idx a { display: block; padding: 16px 20px; background: white; margin: 12px 0; border-radius: 10px; text-decoration: none; color: #333; border-left: 4px solid #c39f59; transition: all .2s; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.idx a:hover { transform: translateX(4px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-left-color: #685021; }
.idx .title { font-size: 1.1em; font-weight: bold; color: #685021; }
.idx .date { color: #999; font-size: 0.85em; margin-top: 4px; }
.back { display: inline-block; margin: 12px 0; padding: 8px 16px; background: #685021; color: white; text-decoration: none; border-radius: 6px; }
.back:hover { background: #8b6f47; }
.mermaid-box { background: #fafafa; padding: 16px; border-radius: 8px; margin: 16px 0; overflow-x: auto; }
img { max-width: 100%; height: auto; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; }
table td, table th { border: 1px solid #ddd; padding: 8px; }
table th { background: #f1ebd9; }
@media print { body { background: white; max-width: none; } .back { display: none; } .card { box-shadow: none; } }
"""

MERMAID = '<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>\n' \
          '<script>mermaid.initialize({startOnLoad:true, theme:"base", themeVariables:{primaryColor:"#c39f59",primaryBorderColor:"#8b6f47",primaryTextColor:"#333",lineColor:"#8b6f47"}});</script>'


def slug(s, i):
    s = re.sub(r'[\\/:*?"<>|]', '_', s)
    s = re.sub(r'\s+', '_', s).strip('_')
    return f"manual_{i}_{s[:40]}"


def load_video_files(out):
    vid_dir = Path(out) / 'videos'
    return {f.stem: f.name for f in vid_dir.iterdir() if f.is_file()} if vid_dir.exists() else {}


# 編集画面の「×」ボタン(クリックすると画像・動画が消える)は、公開ページには要らない
DELETE_BTN_RE = re.compile(r'<button[^>]*class="(?:img|vid)-delete"[^>]*>.*?</button>', re.S)


def strip_editor_buttons(html_str):
    return DELETE_BTN_RE.sub('', html_str)


def inline_mermaid_codes(html_str):
    """本文にすでに入っているフローチャートの中身を集める(重ねて出さないため)"""
    found = re.findall(r'<pre class="mermaid">(.*?)</pre>', html_str, re.S)
    return {html.unescape(c).strip() for c in found}


def inject_video_src(html_str, VIDEO_FILES):
    """<video data-video-id="vid_xxx"> に src="videos/vid_xxx.mp4" を埋め込む"""
    def repl(match):
        vid_id = match.group(1)
        if vid_id in VIDEO_FILES:
            return f'<video src="videos/{VIDEO_FILES[vid_id]}" controls data-video-id="{vid_id}" style="max-width:100%;height:auto;"></video>'
        print(f'  ⚠ 警告: 動画ファイルが見つかりません: {vid_id}(公開ページに灰色の枠が出ます)', file=sys.stderr)
        return f'<video controls data-video-id="{vid_id}" style="max-width:100%;height:auto;background:#eee;color:#999;padding:20px;">動画未取得: {vid_id}</video>'
    return re.sub(r'<video[^>]*data-video-id="([^"]+)"[^>]*></video>', repl, html_str)


def render_manual(m, idx, VIDEO_FILES=None):
    title = m.get('title', f'マニュアル{idx}')
    html_body = strip_editor_buttons(inject_video_src(m.get('html', ''), VIDEO_FILES or {}))
    already = inline_mermaid_codes(html_body)
    mermaids = [c for c in m.get('mermaidCodes', []) if c.strip() not in already]
    date = m.get('date', '')

    # Mermaidブロックを差し込む(html内のmermaidプレースホルダがなければ末尾に追加)
    extra_mermaid = ''
    for code in mermaids:
        extra_mermaid += f'<div class="mermaid-box"><div class="mermaid">{html.escape(code)}</div></div>\n'

    body = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
{MERMAID}
</head>
<body>
<a class="back" href="./">← 一覧に戻る</a>
<div class="card">
<h1>{html.escape(title)}</h1>
{f'<div style="color:#999;font-size:0.9em;">作成: {html.escape(date)}</div>' if date else ''}
<hr>
{html_body}
</div>
{f'<div class="card"><h2>フローチャート</h2>{extra_mermaid}</div>' if extra_mermaid else ''}
<a class="back" href="./">← 一覧に戻る</a>
</body>
</html>'''
    return body


def main():
    if not DATA.exists():
        sys.exit(f'エラー: データファイルがありません: {DATA}')
    with DATA.open(encoding='utf-8') as f:
        data = json.load(f)
    manuals = data.get('savedManuals', [])
    if not manuals:
        # 空のまま上書きして、公開ページを空にしてしまうのを防ぐ
        sys.exit('エラー: マニュアルが0件です。公開ページを空にしないため、何も書き出さずに止めます。')
    VIDEO_FILES = load_video_files(OUT)
    # 各マニュアルをHTMLとして書き出し
    links = []
    for i, m in enumerate(manuals):
        name = slug(m.get('title', ''), i) + '.html'
        out_path = OUT / name
        out_path.write_text(render_manual(m, i+1, VIDEO_FILES), encoding='utf-8')
        links.append((name, m.get('title') or '', m.get('date') or ''))
        print(f'  ✓ {name} ({len(out_path.read_bytes())//1024} KB)')

    # index.html (一覧ページ)
    links_html = '\n'.join([
        f'<a href="./{quote(name)}"><div class="title">{html.escape(title)}</div>'
        f'<div class="date">{html.escape(date or "")}</div></a>'
        for name, title, date in links
    ])

    last_update = str(data.get('lastUpdate') or datetime.date.today().isoformat())

    index = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LUMOUS マニュアル一覧</title>
<style>{CSS}</style>
</head>
<body>
<h1>📚 LUMOUS マニュアル一覧</h1>
<p>業務マニュアル({len(manuals)}件)。クリックすると詳細ページが開きます。</p>
<div class="idx">
{links_html}
</div>
<hr>
<p style="color:#999;font-size:0.85em;text-align:center;">最終更新: {html.escape(last_update)}</p>
</body>
</html>'''
    (OUT / 'index.html').write_text(index, encoding='utf-8')
    print(f'  ✓ index.html ({len((OUT/"index.html").read_bytes())//1024} KB)')

    print(f'\nGenerated {len(manuals)} manuals + index')


if __name__ == '__main__':
    main()
