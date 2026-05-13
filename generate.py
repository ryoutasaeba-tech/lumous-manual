#!/usr/bin/env python3
"""user-data.json から複数マニュアルの静的サイトを生成"""
import json, re, html, os, sys
from pathlib import Path

DATA = Path('/home/ryota/lumous-manual-diagram/user-data.json')
OUT = Path('/home/ryota/lumous-manual-public')

with DATA.open(encoding='utf-8') as f:
    data = json.load(f)

manuals = data.get('savedManuals', [])

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


VID_DIR = OUT / 'videos'
VIDEO_FILES = {f.stem: f.name for f in VID_DIR.iterdir() if f.is_file()} if VID_DIR.exists() else {}


def inject_video_src(html_str):
    """<video data-video-id="vid_xxx"> に src="videos/vid_xxx.mp4" を埋め込む"""
    def repl(match):
        vid_id = match.group(1)
        if vid_id in VIDEO_FILES:
            return f'<video src="videos/{VIDEO_FILES[vid_id]}" controls data-video-id="{vid_id}" style="max-width:100%;height:auto;"></video>'
        return f'<video controls data-video-id="{vid_id}" style="max-width:100%;height:auto;background:#eee;color:#999;padding:20px;">動画未取得: {vid_id}</video>'
    return re.sub(r'<video[^>]*data-video-id="([^"]+)"[^>]*></video>', repl, html_str)


def render_manual(m, idx):
    title = m.get('title', f'マニュアル{idx}')
    html_body = inject_video_src(m.get('html', ''))
    mermaids = m.get('mermaidCodes', [])
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


# 各マニュアルをHTMLとして書き出し
links = []
for i, m in enumerate(manuals):
    name = slug(m.get('title', ''), i) + '.html'
    out_path = OUT / name
    out_path.write_text(render_manual(m, i+1), encoding='utf-8')
    links.append((name, m.get('title', ''), m.get('date', '')))
    print(f'  ✓ {name} ({len(out_path.read_bytes())//1024} KB)')

# index.html (一覧ページ)
links_html = '\n'.join([
    f'<a href="./{name}"><div class="title">{html.escape(title)}</div>'
    f'<div class="date">{html.escape(date)}</div></a>'
    for name, title, date in links
])

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
<p style="color:#999;font-size:0.85em;text-align:center;">最終更新: {data.get('lastUpdate','')}</p>
</body>
</html>'''
(OUT / 'index.html').write_text(index, encoding='utf-8')
print(f'  ✓ index.html ({len((OUT/"index.html").read_bytes())//1024} KB)')

print(f'\nGenerated {len(manuals)} manuals + index')
