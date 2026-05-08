#!/bin/bash
set -e

npm install

# Post-merge ortamında stdin kapalıdır; --force ile interactive soruları atla.
# DRIZZLE_FORCE_PUSH=false olarak ayarlanırsa interactive mod kullanılır.
if [ "${DRIZZLE_FORCE_PUSH:-true}" = "true" ]; then
  npx drizzle-kit push --force
else
  npx drizzle-kit push
fi

# GitHub'a otomatik yedek push
if [ -z "$GITHUB_TOKEN" ]; then
  echo "UYARI: GITHUB_TOKEN bulunamadı, GitHub push atlandı." >&2
  exit 0
fi

echo "GitHub'a push yapılıyor..."
git config user.email "github@emergent.sh"
git config user.name "emergent-agent-e1"

REPO_URL="https://github.com/SimumCo/seftali.git"
AUTH_HEADER="Authorization: Basic $(printf 'x-access-token:%s' "$GITHUB_TOKEN" | base64 -w0)"

# Uzak repo'nun mevcut main SHA'sını al (--force-with-lease için)
REMOTE_SHA=$(git -c "http.extraHeader=$AUTH_HEADER" ls-remote "$REPO_URL" refs/heads/main 2>/dev/null | cut -f1)

if [ -n "$REMOTE_SHA" ]; then
  # Uzakta branch var; sadece beklenen SHA eşleşirse push yap
  git -c "http.extraHeader=$AUTH_HEADER" push "$REPO_URL" "main:main" "--force-with-lease=main:$REMOTE_SHA"
else
  # Uzakta branch henüz yok; ilk kez oluştur
  git -c "http.extraHeader=$AUTH_HEADER" push "$REPO_URL" "main:main"
fi

echo "GitHub push tamamlandı."
