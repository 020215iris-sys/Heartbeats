# DB 구조 가이드 (v3 — 3-DB 구조)

## 컨테이너 구성

| 서비스명 | DB명 | 역할 | 호스트 포트 |
|---|---|---|---|
| `db_general` | `heartbeat_general` | 회원, 세션, 보호자 동의 등 운영 데이터 | **5432** |
| `db_sensitive` | `heartbeat_sensitive` | 진단, 상담, 위기 등 임상 데이터 | **5433** |
| `db_audit` | `heartbeat_audit` | 모든 접근/변경 감사 로그 (INSERT only) | **5434** |

사용자명은 모두 `heartbeat`, 비밀번호는 `.env` 참고.

## 컨테이너 내부 접속 호스트 (FastAPI에서 사용)
- 일반: `db_general:5432`
- 민감: `db_sensitive:5432`
- 감사: `db_audit:5432`

## 테이블 배치 (총 11개)

### 📘 일반 DB (3개)
- `users` — 회원 기본 정보
- `sessions` — JWT refresh token 관리
- `guardian_consents` — 보호자 알림 동의 이력

### 📕 민감 DB (6개)
- `diagnoses` — 자가검진 결과 (PHQ-9, GAD-7)
- `counseling_sessions` — 상담 세션 메타
- `conversations` — 대화 본문 (AES-256 암호화)
- `summaries` — 상담 종료 후 자동 요약
- `voice_files` — 음성 파일 메타 (실파일은 S3)
- `crisis_events` — 위기 감지 이벤트

### 📓 감사 DB (2개)
- `audit_logs_general` — 일반 DB 접근/변경 기록
- `audit_logs_sensitive` — 민감 DB 접근/변경 기록

## 크로스 DB 참조 정책

다른 DB 사이에는 PostgreSQL FK 제약을 걸 수 없어요. 따라서:

- **같은 DB 내 관계**: `REFERENCES table(col)`로 FK 설정 (예: `counseling_sessions.diagnosis_id` → `diagnoses.id`)
- **다른 DB 간 관계**: 그냥 `UUID NOT NULL` 컬럼만 두고, FK 제약 없음. **정합성은 FastAPI 애플리케이션 레벨에서 보장.**

크로스 DB 참조가 발생하는 곳:
- 민감 DB / 감사 DB의 `user_id` → 일반 DB의 `users.id`
- 감사 DB의 `resource_id` → 일반/민감 DB의 각 테이블 id

## 스키마 변경 절차 (개발 단계)

1. `db/{general|sensitive|audit}/init/` 안에 SQL 추가/수정
2. `docker compose down -v` (※ 모든 데이터 삭제됨, 개발 중에만!)
3. `docker compose up -d`
4. `docker compose logs db_general | grep -E "CREATE|ERROR"`로 확인

## CLI 접속
```bash
docker exec -it heartbeat_db_general psql -U heartbeat -d heartbeat_general
docker exec -it heartbeat_db_sensitive psql -U heartbeat -d heartbeat_sensitive
docker exec -it heartbeat_db_audit psql -U heartbeat -d heartbeat_audit
```

## 검증

```bash
# 일반 DB: 3개 테이블
docker exec -it heartbeat_db_general psql -U heartbeat -d heartbeat_general -c "\dt"
# 민감 DB: 6개 테이블 + vector 확장
docker exec -it heartbeat_db_sensitive psql -U heartbeat -d heartbeat_sensitive -c "\dt"
docker exec -it heartbeat_db_sensitive psql -U heartbeat -d heartbeat_sensitive -c "\dx"
# 감사 DB: 2개 테이블
docker exec -it heartbeat_db_audit psql -U heartbeat -d heartbeat_audit -c "\dt"
```

## 운영 배포 후
- `down -v`는 데이터 전부 삭제되므로 사용 불가
- Alembic 등 마이그레이션 도구로 전환 예정
- 감사 DB는 별도 백업 정책 (장기 보존, 1년 이상)
- 감사 DB는 애플리케이션 계정에 INSERT 권한만 부여 (UPDATE/DELETE 금지)
