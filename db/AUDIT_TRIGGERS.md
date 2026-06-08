---

## 6. 기록되는 정보 (audit_logs_sensitive 컬럼별)

| 컬럼 | 출처 | 예시 값 |
|---|---|---|
| `id` | audit DB SERIAL 자동 증가 | `243` |
| `user_id` | INSERT/UPDATE: `NEW.user_id` / DELETE: `OLD.user_id` | `11111111-1111-...` |
| `action` | 트리거의 TG_OP 분기 결과 | `CREATE` / `UPDATE` / `DELETE` |
| `resource_type` | `TG_TABLE_NAME` → CASE 변환 | `CLASSIFICATION` |
| `resource_id` | INSERT/UPDATE: `NEW.id` / DELETE: `OLD.id` | `f326a1c3-836c-...` |
| `ip_address` | (트리거는 모름) | `NULL` |
| `created_at` | audit DB의 `DEFAULT now()` | `2026-06-03 18:15:38` |

---

## 7. 보안 핵심 — audit_writer 역할

audit DB에 별도 역할로 정의됨 (`db/audit/init/04_roles.sh`):

```sql
CREATE ROLE audit_writer LOGIN PASSWORD '...';
GRANT CONNECT ON DATABASE heartbeat_audit TO audit_writer;
GRANT USAGE   ON SCHEMA public           TO audit_writer;
GRANT INSERT, SELECT ON audit_logs_general   TO audit_writer;
GRANT INSERT, SELECT ON audit_logs_sensitive TO audit_writer;
-- UPDATE, DELETE, TRUNCATE 권한 미부여 = 변조 차단
```

**핵심:** 한 번 기록된 audit row는 audit_writer가 절대 못 지움. UPDATE도 불가. **감사 기록의 불변성 보장.**

USER MAPPING:

```sql
CREATE USER MAPPING FOR heartbeat
    SERVER audit_server
    OPTIONS (user 'audit_writer', password '...');
```

→ sensitive DB의 `heartbeat` 사용자(백엔드 + alembic)가 audit DB로 갈 때 → `audit_writer` 자격으로만 접속 → INSERT/SELECT만 가능.

---

## 8. 권한 모델 — 두 DB가 정반대

| DB | 역할 | 권한 |
|---|---|---|
| **sensitive DB (5433)** | `heartbeat` | 모든 권한 — INSERT/UPDATE/DELETE/SELECT 자유 |
| **audit DB (5434)** | `audit_writer` (fdw 경유) | INSERT/SELECT만 — UPDATE/DELETE 차단 |

**핵심 차이:**
- sensitive는 임상 데이터의 자유로운 조작 허용 → 트리거가 모든 조작을 audit에 자동 기록
- audit는 한 번 기록된 row 변조 불가 → 감사 무결성 보장

---

## 9. fdw 통신 실패 시

트리거 함수 안에서 INSERT 실패 → **원본 DML도 같이 롤백** (PostgreSQL 기본 동작).

즉:
- audit DB에 기록 실패 → sensitive DB에도 row 변경 안 됨
- **"감사 누락된 임상 데이터 조작은 절대 안 됨"** 보장

원인 가능성:
- audit DB 컨테이너 다운 → fdw 접속 실패
- 네트워크 문제
- audit_writer 비번 변경 후 USER MAPPING 갱신 안 됨

진단: 트리거 함수 안의 INSERT 에러 메시지를 백엔드 응답에서 그대로 받게 됨.

---

## 10. 감사 로그 조회 방법

### A. DBeaver로 audit DB(5434) 접속

**최근 감사 로그:**
```sql
SELECT id, user_id, action, resource_type, resource_id, created_at, ip_address
FROM audit_logs_sensitive
ORDER BY created_at DESC
LIMIT 20;
```

**특정 사용자의 활동 추적:**
```sql
SELECT * FROM audit_logs_sensitive
WHERE user_id = '11111111-1111-1111-1111-111111111111'
ORDER BY created_at DESC;
```

**action별 통계 (CREATE/UPDATE/DELETE 분포):**
```sql
SELECT action, count(*)
FROM audit_logs_sensitive
GROUP BY action
ORDER BY count(*) DESC;
```

**유형별 통계 (resource_type 분포):**
```sql
SELECT resource_type, count(*) 
FROM audit_logs_sensitive 
GROUP BY resource_type 
ORDER BY count(*) DESC;
```

**의심 정황 — DELETE 시도 추적:**
```sql
SELECT * FROM audit_logs_sensitive
WHERE action = 'DELETE'
ORDER BY created_at DESC;
```

**최근 1시간 모든 활동:**
```sql
SELECT * FROM audit_logs_sensitive
WHERE created_at >= now() - interval '1 hour'
ORDER BY created_at DESC;
```

**특정 리소스의 생애 추적 (INSERT → UPDATE들 → DELETE):**
```sql
SELECT action, created_at FROM audit_logs_sensitive
WHERE resource_id = '특정-uuid'
ORDER BY created_at ASC;
```

**특정 시간대 + 유형:**
```sql
SELECT * FROM audit_logs_sensitive
WHERE created_at BETWEEN '2026-06-01' AND '2026-06-02'
  AND resource_type = 'CRISIS_EVENT'
ORDER BY created_at DESC;
```

### B. 터미널에서 직접 psql

```bash
docker compose exec db_audit psql -U heartbeat -d heartbeat_audit \
  -c "SELECT * FROM audit_logs_sensitive ORDER BY created_at DESC LIMIT 10;"
```

---

## 11. 트리거 정의 확인 (sensitive DB)

**트리거 4개 부착 확인:**
```sql
SELECT tgname, tgrelid::regclass AS table_name, tgenabled
FROM pg_trigger
WHERE tgname LIKE 'trg_audit_%';
```
→ 4줄 (각 테이블별로 하나씩) + tgenabled = `O` (Origin, 활성)

**트리거가 어떤 동작 잡는지 확인:**
```sql
SELECT tgname, tgrelid::regclass AS table_name, tgtype
FROM pg_trigger
WHERE tgname LIKE 'trg_audit_%';
```
→ tgtype의 비트 플래그가 INSERT/UPDATE/DELETE 모두 포함

**트리거 함수 본문:**
```sql
SELECT pg_get_functiondef('log_to_audit_sensitive'::regproc);
```

**Foreign server:**
```sql
SELECT srvname, srvoptions FROM pg_foreign_server;
```
→ `audit_server` + `{host=db_audit, port=5432, dbname=heartbeat_audit}`

**USER MAPPING:**
```sql
SELECT srvname, usename FROM pg_user_mappings WHERE srvname = 'audit_server';
```
→ `audit_server | heartbeat`

---

## 12. 한계점 / 알려진 사항

- **ip_address는 항상 NULL**: 트리거는 누가 변경했는지 실제 사용자 IP를 모름 (DB 내부에서만 동작). 향후 별도 트랙(F-3)으로 백엔드 세션 변수 패턴 도입 검토 중.
- **conversations는 트리거 미적용**: INSERT 빈도 폭증 + audit 비용 폭증으로 정책상 제외. 백엔드 `/chat`에서 직접 audit 처리 (누락 가능성 있음).
- **UPDATE 시 변경 전/후 값 미저장**: 현재는 "UPDATE 일어났음"만 기록. 어떤 컬럼이 어떻게 변경됐는지 알려면 audit_logs_sensitive에 JSONB 컬럼(`old_values`, `new_values`) 추가 필요. 향후 후보.
- **DDL은 잡지 않음**: 트리거는 DML(INSERT/UPDATE/DELETE)만 감지. 스키마 변경(CREATE TABLE/ALTER 등)은 alembic이 별도 관리.
- **트리거 함수가 SECURITY DEFINER (heartbeat 권한)**: 마이그레이션 실행 시점 사용자가 함수 OWNER. USER MAPPING이 `FOR heartbeat`인 이유.
- **resource_type 매핑 누락 시**: CASE문에 없는 새 테이블에 트리거 부착하면 `upper(TG_TABLE_NAME)` 폴백. 의도하지 않은 표기 가능 — 새 테이블 추가 시 CASE문도 업데이트 권장.
- **옵션 B(RBAC)와 호환됨**: 백엔드가 `sensitive_app`(제한 계정)으로 INSERT해도
  `SECURITY DEFINER` 덕분에 트리거 함수가 `heartbeat`(OWNER) 권한으로 실행되어
  audit 자동 기록이 그대로 작동함. 검증 결과 트리거 → fdw → audit DB INSERT가
  23ms 이내에 완료됨을 확인. 자세한 메커니즘은 [`db/RBAC.md`](RBAC.md) 4장 참조.
---

## 13. 마이그레이션 파일 + 명령

**파일 위치:**

| Phase | 파일 |
|---|---|
| F-1 (INSERT 트리거 도입) | `backend/alembic_sensitive/versions/169975650e40_f_1_add_audit_triggers_via_postgres_fdw.py` |
| F-2 (UPDATE/DELETE 확장) | `backend/alembic_sensitive/versions/ec8f4101a306_f_2_extend_audit_triggers_to_update_and_.py` |

**적용 명령:**
```bash
docker compose exec api alembic -c alembic_sensitive.ini upgrade head
```

**현재 상태 확인:**
```bash
docker compose exec api alembic -c alembic_sensitive.ini current
```
→ `ec8f4101a306 (head)` 보이면 F-2까지 적용된 최신 상태.

**롤백 (응급 시):**
```bash
# F-2만 되돌리기 (F-1 INSERT-only 상태로)
docker compose exec api alembic -c alembic_sensitive.ini downgrade -1

# F-1도 되돌리기 (트리거 + fdw 전체 제거, baseline 상태)
docker compose exec api alembic -c alembic_sensitive.ini downgrade base
```

⚠️ 다운그레이드 후엔 새로운 INSERT/UPDATE/DELETE가 audit에 자동 기록 안 됨.

---


## 14. 트리거 비활성화 (테스트 한정)

⚠️ **이 명령은 OWNER 권한이 필요합니다.** 옵션 B 적용 후 백엔드 계정
(`sensitive_app`)으로는 `DISABLE TRIGGER`가 자동 차단됩니다 — 이게 권한 분리의
의도된 효과입니다. 테스트 목적으로 비활성화하려면 `heartbeat` 계정으로 접속해야
합니다.

```sql
-- 임시 비활성화 (개별 테이블)
ALTER TABLE classifications DISABLE TRIGGER trg_audit_classifications;

-- 활성화 복구
ALTER TABLE classifications ENABLE TRIGGER trg_audit_classifications;
```

⚠️ **프로덕션에서는 절대 비활성화 금지.** 감사 누락 = 규정 위반.

---

## 15. 검증 시나리오 — 3가지 동작 다 테스트

**sensitive DB(5433)에서 INSERT → UPDATE → DELETE 순차 실행:**

```sql
-- (1) INSERT
INSERT INTO classifications (id, user_id, compound_flags, selected_prompt_key)
VALUES (
    '99999999-9999-9999-9999-999999999999'::uuid,
    '11111111-1111-1111-1111-111111111111',
    '{"test": "audit_check"}'::jsonb,
    'TEST_F2'
);

-- (2) UPDATE
UPDATE classifications 
SET selected_prompt_key = 'TEST_F2_UPDATED'
WHERE id = '99999999-9999-9999-9999-999999999999';

-- (3) DELETE
DELETE FROM classifications 
WHERE id = '99999999-9999-9999-9999-999999999999';
```

**audit DB(5434)에서 3개 row 자동 기록 확인:**

```sql
SELECT id, user_id, action, resource_type, resource_id, created_at
FROM audit_logs_sensitive
WHERE resource_id = '99999999-9999-9999-9999-999999999999'
ORDER BY created_at ASC;
```

**예상 결과 — 3줄 (시간순):**

| action | resource_type | resource_id | created_at |
|---|---|---|---|
| `CREATE` | CLASSIFICATION | 99999999-... | (Step 1 시각) |
| `UPDATE` | CLASSIFICATION | 99999999-... | (Step 2 시각) |
| `DELETE` | CLASSIFICATION | 99999999-... | (Step 3 시각) |

3개 row 모두 보이면 **트리거 시스템 완전 작동.**

---

## 16. 관련 문서

- `db/MIGRATIONS.md` — Alembic 마이그레이션 사용 가이드 (multi-DB 명령 패턴, 트러블슈팅)
- `db/README.md` — 3DB 아키텍처 전반

---

> 작성: 새봄 / 2026-06-03  
> Phase: F-1 (`169975650e40`) + F-2 (`ec8f4101a306`)  
> 검증 완료: INSERT/UPDATE/DELETE 3가지 모두 audit DB 자동 기록 확인