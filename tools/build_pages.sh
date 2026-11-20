#!/usr/bin/env sh
# Build frontend statis untuk Cloudflare Pages -> folder dist/
# Pengaturan Pages:
#   Build command          : sh tools/build_pages.sh
#   Build output directory : dist
#   Environment variables  : SKIP_DEPENDENCY_INSTALL=1   (jangan pip/npm install backend)
#                            SAKURA_API_URL=https://<alamat-backend>  (tanpa / di akhir)
set -eu

rm -rf dist
mkdir -p dist/Assets

cp -r frontend/. dist/
cp -r Character dist/Character
cp -r Assets/thumbnail Assets/animation Assets/1012111.jpg dist/Assets/

# Alamat backend disuntikkan sebelum script utama di index.html
API="${SAKURA_API_URL:-}"
API="${API%/}"
case "$API" in null|undefined|none) API="" ;; esac
if [ -n "$API" ]; then
  sed -i "s#<head>#<head>\n    <script>window.SAKURA_API_URL = \"$API\";</script>#" dist/index.html
  echo "SAKURA_API_URL = $API"
else
  echo "PERINGATAN: SAKURA_API_URL kosong, chat akan memanggil /api di domain Pages (gagal)."
fi

echo "Selesai: $(find dist -type f | wc -l) file di dist/"
