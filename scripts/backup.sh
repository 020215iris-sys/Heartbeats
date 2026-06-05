#!/bin/bash
# scripts/backup.sh
# 하트비트 3-DB 백업
# 사용: bash scripts/backup.sh
#
# 결과: backups/YYYY-MM-DD_HHMMSS/{general,sensitive,audit}.sql 생성

set -e   # 중간에 에러 나면 즉시 중단

# 타임스탬프 폴더 생성
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
BACKUP_DIR="backups/${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}"

echo "🔄 백업 시작: ${BACKUP_DIR}"

# general
echo "  → general DB..."
docker exec heartbeat_db_general \
  pg_dump -U heartbeat -d heartbeat_general --clean --if-exists \
  > "${BACKUP_DIR}/general.sql"
[ -s "${BACKUP_DIR}/general.sql" ] || { echo "❌ general.sql이 비어있음. 백업 실패."; exit 1; }


# sensitive
echo "  → sensitive DB..."
docker exec heartbeat_db_sensitive \
  pg_dump -U heartbeat -d heartbeat_sensitive --clean --if-exists \
  > "${BACKUP_DIR}/sensitive.sql"
[ -s "${BACKUP_DIR}/sensitive.sql" ] || { echo "❌ sensitive.sql이 비어있음. 백업 실패."; exit 1; }

# audit
echo "  → audit DB..."
docker exec heartbeat_db_audit \
  pg_dump -U heartbeat -d heartbeat_audit --clean --if-exists \
  > "${BACKUP_DIR}/audit.sql"
[ -s "${BACKUP_DIR}/audit.sql" ] || { echo "❌ audit.sql이 비어있음. 백업 실패."; exit 1; }

# 파일 크기 출력
echo ""
echo "✅ 백업 완료:"
ls -lh "${BACKUP_DIR}"