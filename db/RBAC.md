# 하트비트 — 권한 분리 (RBAC) 가이드

옵션 B(Role-Based Access Control: 백엔드용 제한 권한 계정 분리)의 전체 설명서입니다.
"왜 필요한가", "어떻게 구성됐는가", "어떻게 검증·디버깅하는가"를 한 번에 정리합니다.

---

## 1. 한 줄 요약

> **백엔드(FastAPI) 컨테이너가 DB에 접속할 때는 CRUD만 가능한 제한 계정을 쓰고, DDL(CREATE/ALTER/DROP/TRUNCATE 등)이 필요한 alembic 마이그레이션만 OWNER 계정을 씁니다.**

이 분리로 SQL Injection·코드 실수·내부 사고가 발생해도 백엔드 계정의 권한 자체가 좁아서 피해 범위가 한정됩니다.

---

## 2. 왜 필요한가 — 권한 분리가 막아주는 시나리오

audit DB의 INSERT-only 격리(`audit_writer`)만으로는 다음 시나리오를 막을 수 없었습니다:

| 공격/사고 | audit 격리만 있을 때 | 옵션 B 적용 후 |
|---|---|---|
| 백엔드 SQL Injection으로 `DROP TABLE` 시도 | ❌ 통과 (heartbeat=SUPERUSER) | ✅ `permission denied` |
| 백엔드 SQL Injection으로 `TRUNCATE` 시도 | ❌ 통과 | ✅ `permission denied` |
| 백엔드를 통해 `DISABLE TRIGGER`로 audit 무력화 | ❌ 통과 | ✅ `must be owner` 에러 |
| 트리거 함수를 `CREATE OR REPLACE`로 빈 함수로 교체 | ❌ 통과 | ✅ 함수 OWNER 아니라 불가 |
| 개발자가 실수로 `DELETE WHERE 1=1` 마이그레이션 | ❌ 통과 | ✅ 일반 트래픽 경로엔 DELETE 권한 있지만, OWNER 권한 필요한 작업은 차단 |

핵심 개념 — **권한 분리(예방)** 와 **감사 로그(사후 추적)** 는 보완관계지 대체관계가 아닙니다.
audit이 잡는 것은 "정상 권한으로 수행된 변경"이고,
권한 분리는 "권한 자체를 남용하는 행위"를 차단합니다.

---

## 3. 권한 분리 구조 — 누가 무엇을 할 수 있는가

### 3.1 DB별 계정

| DB | 백엔드 트래픽 계정 | 마이그레이션 계정 | 비고 |
|---|---|---|---|
| general (5432) | `general_app` | `heartbeat` (OWNER, SUPERUSER) | |
| sensitive (5433) | `sensitive_app` | `heartbeat` (OWNER, SUPERUSER) | F-1/F-2 트리거 함수 OWNER도 `heartbeat` |
| audit (5434) | `audit_writer` (INSERT, SELECT만) | `heartbeat` (OWNER, SUPERUSER) | fdw 트리거가 이 계정으로 audit DB에 INSERT |

### 3.2 권한 매트릭스

| 작업 | `general_app` / `sensitive_app` | `audit_writer` | `heartbeat` (OWNER) |
|---|---|---|---|
| SELECT | ✅ | ✅ | ✅ |
| INSERT | ✅ | ✅ | ✅ |
| UPDATE | ✅ | ❌ | ✅ |
| DELETE | ✅ | ❌ | ✅ |
| TRUNCATE | ❌ | ❌ | ✅ |
| CREATE/ALTER/DROP TABLE | ❌ | ❌ | ✅ |
| ALTER TABLE … DISABLE TRIGGER | ❌ | ❌ | ✅ |
| CREATE/REPLACE FUNCTION | ❌ | ❌ | ✅ |
| ALTER USER MAPPING | ❌ | ❌ | ✅ |

### 3.3 두 경로의 완전 분리

```
[FastAPI 백엔드 컨테이너 (api)]
   ↓ DATABASE_URL_GENERAL    → general_app
   ↓ DATABASE_URL_SENSITIVE  → sensitive_app
   ↓ DATABASE_URL_AUDIT      → audit_writer
   ↓
[3개 DB 컨테이너] — 일반 트래픽

[alembic 마이그레이션 (CLI에서 실행)]
   ↓ ADMIN_DATABASE_URL_GENERAL    → heartbeat
   ↓ ADMIN_DATABASE_URL_SENSITIVE  → heartbeat
   ↓ ADMIN_DATABASE_URL_AUDIT      → heartbeat
   ↓
[3개 DB 컨테이너] — 스키마 변경 시에만
```

운영 시점에는 OWNER 계정이 한 번도 노출되지 않습니다.
마이그레이션은 개발자가 수동으로 실행하는 작업이라 노출 빈도가 매우 낮습니다.

---

## 4. F-1/F-2 audit 트리거와의 상호작용

옵션 B 적용 후에도 F-1/F-2 audit 트리거가 정상 작동하는 이유는 `SECURITY DEFINER` 메커니즘 덕분입니다.

### 4.1 트리거 발동 흐름

```
1) 백엔드가 sensitive_app으로 sensitive DB 접속
2) INSERT INTO counseling_sessions VALUES (...);  ← sensitive_app 권한으로 실행
3) AFTER INSERT 트리거 발동
4) log_to_audit_sensitive() 함수 호출
   ↓
   ⚠ 이 함수는 SECURITY DEFINER로 선언됨
   ↓ CURRENT_USER가 함수 OWNER(heartbeat)로 자동 전환
5) INSERT INTO audit_logs_sensitive_remote (foreign table) ...;
6) postgres_fdw가 USER MAPPING 조회
   ↓ FOR CURRENT_USER (= heartbeat 상태)
   ↓ → audit_writer 자격증명 획득
7) audit DB에 audit_writer로 접속
8) audit_logs_sensitive 테이블에 INSERT 성공
```

핵심은 `SECURITY DEFINER` — 트리거 함수가 호출자(sensitive_app)의 권한이 아닌 **함수 OWNER(heartbeat)의 권한으로 실행**된다는 점.
이 덕분에 백엔드 계정의 권한이 좁아져도 트리거 → fdw → audit 자동 기록이 그대로 작동합니다.

### 4.2 만약 트리거 함수 OWNER가 바뀐다면

`heartbeat`가 아닌 다른 계정으로 마이그레이션이 실행되면 함수 OWNER가 그쪽으로 바뀝니다. 그러면 `USER MAPPING FOR heartbeat`이 더 이상 매칭 안 되고 audit 기록 실패. 그래서 Phase 3에서 alembic이 반드시 `heartbeat` 계정으로 접속하도록 분리한 것입니다.

---

## 5. 어디에 무엇이 설정돼 있는가

### 5.1 비밀번호

| 변수 | 위치 | 역할 |
|---|---|---|
| `DB_GENERAL_PASSWORD` | 루트 `.env` | general DB의 heartbeat 계정 비번 |
| `DB_SENSITIVE_PASSWORD` | 루트 `.env` | sensitive DB의 heartbeat 계정 비번 |
| `DB_AUDIT_PASSWORD` | 루트 `.env` | audit DB의 heartbeat 계정 비번 |
| `DB_GENERAL_APP_PASSWORD` | 루트 `.env` | general_app 계정 비번 |
| `DB_SENSITIVE_APP_PASSWORD` | 루트 `.env` | sensitive_app 계정 비번 |
| `DB_AUDIT_WRITER_PASSWORD` | 루트 `.env` | audit_writer 계정 비번 + fdw USER MAPPING |

### 5.2 DB URL

`backend/.env`에:

```dotenv
# 백엔드 트래픽용 (제한 계정)
DATABASE_URL_GENERAL=postgresql://general_app:${DB_GENERAL_APP_PASSWORD}@db_general:5432/heartbeat_general
DATABASE_URL_SENSITIVE=postgresql://sensitive_app:${DB_SENSITIVE_APP_PASSWORD}@db_sensitive:5432/heartbeat_sensitive
DATABASE_URL_AUDIT=postgresql://audit_writer:${DB_AUDIT_WRITER_PASSWORD}@db_audit:5432/heartbeat_audit

# 마이그레이션용 (OWNER 계정)
ADMIN_DATABASE_URL_GENERAL=postgresql://heartbeat:${DB_GENERAL_PASSWORD}@db_general:5432/heartbeat_general
ADMIN_DATABASE_URL_SENSITIVE=postgresql://heartbeat:${DB_SENSITIVE_PASSWORD}@db_sensitive:5432/heartbeat_sensitive
ADMIN_DATABASE_URL_AUDIT=postgresql://heartbeat:${DB_AUDIT_PASSWORD}@db_audit:5432/heartbeat_audit
```

### 5.3 ROLE 생성 코드

| 위치 | 무엇 |
|---|---|
| `db/general/init/05_app_role.sh` | 컨테이너 최초 기동 시 `general_app` 자동 생성 |
| `db/sensitive/init/10_app_role.sh` | 컨테이너 최초 기동 시 `sensitive_app` 자동 생성 |
| `db/audit/init/04_roles.sh` | 컨테이너 최초 기동 시 `audit_writer` 자동 생성 |
| `scripts/apply_option_b.sh` | 이미 실행 중인 컨테이너에 옵션 B 사후 적용 (멱등) |
| `scripts/verify_option_b.sh` | 옵션 B 동작 검증 (정상 동작 + 권한 거부 + fdw 트리거) |

### 5.4 alembic env.py

세 환경 모두 `ADMIN_DATABASE_URL_*`을 읽습니다:

| 파일 | 읽는 변수 |
|---|---|
| `backend/alembic/env.py` | `ADMIN_DATABASE_URL_GENERAL` |
| `backend/alembic_sensitive/env.py` | `ADMIN_DATABASE_URL_SENSITIVE` |
| `backend/alembic_audit/env.py` | `ADMIN_DATABASE_URL_AUDIT` |

환경변수 누락 시 `RuntimeError`로 즉시 중단해 디버깅이 쉽습니다.

---

## 6. 검증 — 옵션 B가 정상 작동하는지 확인하기

### 6.1 정상 동작 (SELECT/INSERT 가능)

```bash
# general_app으로 users SELECT
docker exec -e PGPASSWORD="${DB_GENERAL_APP_PASSWORD}" -i heartbeat_db_general \
    psql -U general_app -d heartbeat_general -h localhost \
    -c "SELECT count(*) FROM users;"
```

### 6.2 위험 명령 거부 (TRUNCATE/DISABLE TRIGGER/DROP)

```bash
# 모두 'permission denied' 또는 'must be owner' 에러로 막혀야 정상
docker exec -e PGPASSWORD="${DB_SENSITIVE_APP_PASSWORD}" -i heartbeat_db_sensitive \
    psql -U sensitive_app -d heartbeat_sensitive -h localhost \
    -c "TRUNCATE counseling_sessions;"

docker exec -e PGPASSWORD="${DB_SENSITIVE_APP_PASSWORD}" -i heartbeat_db_sensitive \
    psql -U sensitive_app -d heartbeat_sensitive -h localhost \
    -c "ALTER TABLE counseling_sessions DISABLE TRIGGER ALL;"
```

### 6.3 audit_writer 변조 차단 (UPDATE/DELETE 차단)

```bash
# UPDATE/DELETE는 'permission denied'로 막혀야 정상
docker exec -e PGPASSWORD="${DB_AUDIT_WRITER_PASSWORD}" -i heartbeat_db_audit \
    psql -U audit_writer -d heartbeat_audit -h localhost \
    -c "UPDATE audit_logs_general SET action='HACK';"
```

### 6.4 fdw 트리거 무결성 (가장 중요)

```bash
# 1) sensitive_app으로 INSERT
docker exec -e PGPASSWORD="${DB_SENSITIVE_APP_PASSWORD}" -i heartbeat_db_sensitive \
    psql -U sensitive_app -d heartbeat_sensitive -h localhost \
    -c "INSERT INTO counseling_sessions(user_id)
        VALUES ('00000000-0000-0000-0000-000000099999')
        RETURNING id;"

# 2) audit DB에 자동 기록됐는지 확인 (1초 이내)
docker exec heartbeat_db_audit psql -U heartbeat -d heartbeat_audit \
    -c "SELECT id, user_id, action, resource_type, resource_id
        FROM audit_logs_sensitive
        WHERE user_id = '00000000-0000-0000-0000-000000099999'::uuid
        ORDER BY created_at DESC LIMIT 1;"
# 1줄 보이면 fdw + SECURITY DEFINER 메커니즘 정상
```

### 6.5 마이그레이션 환경

```bash
# 세 환경 모두 head 마이그레이션 ID 출력돼야 OK
docker compose exec api alembic -c alembic.ini current
docker compose exec api alembic -c alembic_sensitive.ini current
docker compose exec api alembic -c alembic_audit.ini current
```

`permission denied`나 `RuntimeError` 떠선 안 됨. `RuntimeError`가 뜨면 `ADMIN_DATABASE_URL_*` 누락.

### 6.6 일괄 검증 스크립트

위 모든 검증을 한 번에:

```bash
bash scripts/verify_option_b.sh
```

---

## 7. 트러블슈팅

### 7.1 백엔드가 `password authentication failed`로 죽는다

원인: `backend/.env`의 `DATABASE_URL_*`이 잘못된 비번 또는 잘못된 사용자.

확인:
```bash
docker compose exec api env | grep DATABASE_URL_
# 각 URL의 사용자/비번이 ROLE과 일치하는지
```

해결: 루트 `.env`의 `DB_*_APP_PASSWORD`와 backend/.env의 URL 안 비번이 같은 값을 가리키는지 확인.
일반적으로 backend/.env는 `${DB_*_APP_PASSWORD}` 변수 참조 패턴을 사용하므로 루트 `.env`의 값만 정확하면 자동으로 일치.

### 7.2 백엔드 SQL 실행 시 `permission denied for table xxx`

원인: 새 테이블이 alembic 마이그레이션으로 추가됐는데 app 계정에 GRANT가 안 됐을 가능성.

확인:
```sql
-- heartbeat 계정으로 실행
\dp public.새로운_테이블
-- general_app 또는 sensitive_app에 권한이 있어야 함
```

해결: `ALTER DEFAULT PRIVILEGES`가 init 스크립트에 들어 있어서 정상이라면 자동으로 GRANT됨. 안 됐으면 수동 GRANT:
```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON 새로운_테이블 TO general_app;
```

### 7.3 alembic 실행 시 `RuntimeError: ADMIN_DATABASE_URL_*`

원인: backend/.env에 ADMIN URL 누락.

해결: 다음 3개가 다 있는지 확인:
```bash
grep -E "^ADMIN_DATABASE_URL_" backend/.env
```

### 7.4 트리거가 발동했는데 audit DB에 기록이 안 됨

원인: `USER MAPPING FOR heartbeat`이 사라졌거나 비번이 안 맞음.

확인:
```sql
-- sensitive DB에서
SELECT srvname, usename, umoptions FROM pg_user_mappings;
```

해결: F-1 마이그레이션을 downgrade → upgrade 재실행하면 USER MAPPING 재생성.
```bash
docker compose exec api alembic -c alembic_sensitive.ini downgrade base
docker compose exec api alembic -c alembic_sensitive.ini upgrade head
```

### 7.5 컨테이너를 `down -v`하고 다시 띄웠는데 ROLE이 없음

원인: init 스크립트가 실행 안 됐을 가능성 (CRLF 줄바꿈, 권한 등).

확인:
```bash
file db/general/init/05_app_role.sh  # CRLF 표시가 없어야 함
ls -la db/*/init/*.sh                # 실행 권한 표시 (x)가 있어야 함
docker compose logs db_general | grep -i "05_app_role"
```

해결: LF 줄바꿈으로 다시 저장 + 실행 권한 부여 + `down -v` → `up` 재시도.

---

## 8. 향후 — 옵션 A로의 확장 (GA 단계)

베타 단계에서 옵션 B만으로 충분하지만, GA 전에 옵션 A로 보강 권장:

| 항목 | 옵션 B (현재) | 옵션 A (GA 전) |
|---|---|---|
| 백엔드 트래픽 계정 | app 계정 (제한) | 동일 |
| 테이블 OWNER | `heartbeat` (SUPERUSER) | 별도 `heartbeat_owner` (SUPERUSER 아님) |
| SUPERUSER 보유 | `heartbeat` | 마이그레이션 용 별도 계정만 |
| `pgvector` CREATE EXTENSION | SUPERUSER 직접 | trusted extension 패턴 |

옵션 A 작업 시 주의:
1. `SECURITY DEFINER` 함수 OWNER 변경 시 USER MAPPING 재생성 필요
2. `ALTER TABLE … OWNER TO`를 모든 테이블에 적용
3. `ALTER FUNCTION … OWNER TO`를 트리거 함수에 적용
4. `pgvector` 등 SUPERUSER 필요 확장의 대안 검토

---

## 9. 변경 이력

| 일자 | 단계 | 변경 |
|---|---|---|
| 2026-06-05 | Phase 1 | `general_app`, `sensitive_app` ROLE 추가 + 백엔드 `.env`의 URL 변경 |
| 2026-06-05 | Phase 2 | Docker init 스크립트로 영속화 + `./ai:/ai` 마운트 추가 |
| 2026-06-05 | Phase 3 | alembic 3개 환경을 `ADMIN_DATABASE_URL_*` 사용하도록 변경 |
| 2026-06-05 | Phase 4 | RBAC.md 문서 작성 + README.md/AUDIT_TRIGGERS.md 업데이트 |
