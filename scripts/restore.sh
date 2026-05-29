#!/bin/bash
# scripts/restore.sh
# 백업 파일로부터 3-DB 복구
# 사용: bash scripts/restore.sh backups/2026-05-29_143012
#
# ⚠️ 주의: 기존 DB의 모든 데이터가 덮어쓰기 됩니다

set -e

# 인자 체크
if [ -z "$1" ]; then
  echo "❌ 사용법: bash scripts/restore.sh <백업폴더경로>"
  echo "   예: bash scripts/restore.sh backups/2026-05-29_143012"
  exit 1
fi

BACKUP_DIR="$1"

# 폴더 존재 확인
if [ ! -d "${BACKUP_DIR}" ]; then
  echo "❌ 폴더를 찾을 수 없습니다: ${BACKUP_DIR}"
  exit 1
fi

# 안전 확인
echo "⚠️  ${BACKUP_DIR} 의 내용으로 현재 DB를 덮어씁니다."
read -p "정말 진행하시겠습니까? (yes 입력): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "취소됨"
  exit 0
fi

echo "🔄 복구 시작..."

# general
echo "  → general DB..."
docker exec -i heartbeat_db_general \
  psql -U heartbeat -d heartbeat_general \
  < "${BACKUP_DIR}/general.sql"

# sensitive
echo "  → sensitive DB..."
docker exec -i heartbeat_db_sensitive \
  psql -U heartbeat -d heartbeat_sensitive \
  < "${BACKUP_DIR}/sensitive.sql"

# audit
echo "  → audit DB..."
docker exec -i heartbeat_db_audit \
  psql -U heartbeat -d heartbeat_audit \
  < "${BACKUP_DIR}/audit.sql"

echo "✅ 복구 완료"

## 인자 없으면 가장 최근 폴더 사용
# if [ -z "$1" ]; then
#   BACKUP_DIR=$(ls -td backups/*/ | head -1 | sed 's:/$::')
#   echo "최근 백업 사용: ${BACKUP_DIR}"
# else
#   BACKUP_DIR="$1"
# fi