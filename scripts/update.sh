#!/bin/bash
# Oracle Cloud 서버 업데이트 스크립트
# 사용법: ./scripts/update.sh [--rebuild]

set -e

cd "$(dirname "$0")/.."

echo ">>> git pull"
git pull

if [[ "$1" == "--rebuild" ]]; then
    echo ">>> docker compose up --build"
    docker compose up -d --build
else
    echo ">>> docker compose up"
    docker compose up -d
fi

echo ">>> 완료: $(date)"
docker compose ps
