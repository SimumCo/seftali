#!/bin/bash
# GitHub'a push script

REPO_URL="https://${GITHUB_TOKEN}@github.com/SimumCo/depo-com.git"

# Remote ekle veya güncelle
git remote remove github 2>/dev/null || true
git remote add github "$REPO_URL"

# Push yap
git push github main --force

echo "✅ Push tamamlandı!"
