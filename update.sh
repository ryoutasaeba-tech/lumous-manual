#!/bin/bash
# LUMOUSマニュアルのWeb公開更新
# 使い方: bash ~/lumous-manual-public/update.sh
# 送り先の枝を変えたいとき: BRANCH=名前 bash update.sh  (決めなければ main)
set -e

BRANCH="${BRANCH:-main}"
cd "$(dirname "$(readlink -f "$0")")"

echo "▶ 静的サイトを再生成中..."
python3 generate.py

# 追加された新しいファイル(動画など)も「変更」として数える
if [ -z "$(git status --porcelain)" ]; then
  echo "✓ 変更なし — マニュアルに更新はありません"
  exit 0
fi

echo "▶ 変更をコミット中..."
git add -A
git -c user.email="ryoutasaeba-tech@users.noreply.github.com" \
    -c user.name="ryoutasaeba-tech" \
    commit -q -m "update manuals: $(date '+%Y-%m-%d %H:%M')"

echo "▶ GitHub にpush中..."
git push origin "$BRANCH"

echo ""
echo "✅ 更新完了"
echo "   https://ryoutasaeba-tech.github.io/lumous-manual/"
echo "   (GitHub Pagesの反映に1〜2分かかります)"
