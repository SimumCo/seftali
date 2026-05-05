#!/bin/bash
set -e
cd frontend
if [ ! -d "node_modules" ] || [ ! -d "node_modules/ajv/dist/compile" ]; then
  echo ">>> Bağımlılıklar yükleniyor..."
  npm install --legacy-peer-deps
  # Node 20 + react-scripts 5 uyumluluk düzeltmesi
  npm install ajv@^8 --legacy-peer-deps --save
fi
PORT=5000 BROWSER=none npm start
