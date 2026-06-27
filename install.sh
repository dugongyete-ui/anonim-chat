#!/bin/bash

echo "================================"
echo "  Anonim Chat Bot - Installer"
echo "================================"

echo ""
echo "[1/2] Menginstall dependencies..."
npm install --omit=dev

if [ $? -ne 0 ]; then
    echo "✘ Gagal install dependencies!"
    exit 1
fi

echo ""
echo "[2/2] Mengecek environment variables..."

MISSING=0

if [ -z "$BOT_TOKEN" ]; then
    echo "✘ BOT_TOKEN belum diset"
    MISSING=1
fi

if [ -z "$MONGO_URI" ]; then
    echo "✘ MONGO_URI belum diset"
    MISSING=1
fi

if [ $MISSING -eq 1 ]; then
    echo ""
    echo "⚠ Pastikan environment variables di atas sudah diset sebelum menjalankan bot."
    echo "  Tambahkan di Replit Secrets atau file .env"
    exit 1
fi

echo "✔ Semua environment variables tersedia"
echo ""
echo "================================"
echo "  Instalasi selesai!"
echo "  Jalankan bot dengan: node index.js"
echo "================================"
