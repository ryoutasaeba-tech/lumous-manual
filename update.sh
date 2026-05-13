#!/bin/bash
# LUMOUSマニュアルのWeb公開更新
# 使い方: bash ~/lumous-manual-public/update.sh
set -e

cd "$(dirname "$(readlink -f "$0")")"

echo "▶ 静的サイトを再生成中..."
python3 generate.py

if git diff --quiet && git diff --cached --quiet; then
  echo "✓ 変更なし — マニュアルに更新はありません"
  exit 0
fi

echo "▶ 変更をコミット中..."
git add -A
git -c user.email="ryoutasaeba-tech@users.noreply.github.com" \
    -c user.name="ryoutasaeba-tech" \
    commit -q -m "update manuals: $(date '+%Y-%m-%d %H:%M')"

echo "▶ GitHub にpush中..."
git push origin main

echo ""
echo "✅ 更新完了"
echo "   https://ryoutasaeba-tech.github.io/lumous-manual/"
echo "   (GitHub Pagesの反映に1〜2分かかります)"
