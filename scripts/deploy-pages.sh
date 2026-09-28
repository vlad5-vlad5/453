#!/usr/bin/env bash
# Собрать dist/ и задеплоить в ветку gh-pages (GitHub Pages).
# Требует git-доступ к origin. Запуск: ./scripts/deploy-pages.sh
set -euo pipefail
cd "$(dirname "$0")/.."

npm run build

ORIGIN=$(git remote get-url origin)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
cp -r dist/. "$T/"
cd "$T"
git init -q -b gh-pages
git config user.email "deploy@local"
git config user.name "deploy"
git add -A
git commit -q -m "deploy: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git remote add origin "$ORIGIN"
git push -f origin gh-pages

echo "Готово! GitHub Pages обновится через ~1 минуту:"
echo "  https://vlad5-vlad5.github.io/453/"
