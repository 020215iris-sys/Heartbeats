# 하트비트 — DB·인프라

하트비트(Heartbeat) 서비스의 데이터베이스·인프라 영역 가이드입니다.

## 1. 개요

하트비트는 정신건강 임상 데이터를 다루는 AI 상담 서비스로,
**데이터 민감도에 따라 데이터베이스를 3개로 물리적으로 분리**합니다.
이는 단순한 스키마 분리가 아닌 **별도의 PostgreSQL 인스턴스(컨테이너)** 로
운영함으로써 다음을 달성합니다:

- 민감 임상 데이터의 격리 보관
- 감사 로그의 분리 보관 (변조 차단)
- DB별 독립적인 백업·접근 통제·장애 격리

## 2. 구성

| 컨테이너 | 이미지 | 호스트 포트 | 역할 |
|---|---|---|---|
| `heartbeat_db_general` | pgvector/pgvector:pg16 | 5432 | 회원·세션·보호자 동의 등 일반 운영 |
| `heartbeat_db_sensitive` | pgvector/pgvector:pg16 | 5433 | 분류·상담·대화·요약·위기 등 임상 |
| `heartbeat_db_audit` | postgres:16-alpine | 5434 | 감사 추적 로그 (INSERT-only) |
| `heartbeat_redis` | redis:7-alpine | 6379 | Celery 브로커 + 세션·OTP 캐시 |

> sensitive는 RAG·임베딩을 위해 pgvector 확장이 활성화되어 있습니다.

## 3. 시작하기

### 사전 요구
- Docker Desktop (WSL2 백엔드 권장)
- Git Bash 또는 동등한 셸

### 환경변수 설정
프로젝트 루트의 `.env.example`을 복사해서 `.env`를 만들고 비밀번호를 채웁니다:

```bash
cp .env.example .env
# .env를 열어 모든 PASSWORD 값을 임의의 강한 문자열로 변경
```

필요한 변수:
- `DB_GENERAL_PASSWORD`
- `DB_SENSITIVE_PASSWORD`
- `DB_AUDIT_PASSWORD`
- `DB_AUDIT_WRITER_PASSWORD` (audit 전용 제한 계정)

### 기동
```bash
docker compose up -d
```

모든 컨테이너가 `healthy` 상태가 될 때까지 약 10초 정도 걸립니다.
상태 확인:
```bash
docker compose ps
```

### 종료
```bash
docker compose down       # 데이터 보존
docker compose down -v    # 데이터까지 초기화 (개발 시에만)
```

## 4. DB별 책임 범위

### General DB (5432, `heartbeat_general`)
일상 운영 데이터. 다른 DB가 user_id로 논리 참조합니다.

| 테이블 | 용도 |
|---|---|
| `users` | 회원 |
| `sessions` | JWT refresh token (revoked_at으로 무효화 관리) |
| `guardian_consents` | 보호자 동의 |

### Sensitive DB (5433, `heartbeat_sensitive`)
정신건강 임상 데이터. **물리적으로 격리** 보관.

| 테이블 | 용도 |
|---|---|
| `category_catalog` | PHQ-9/GAD-7 등 분류 카테고리 마스터 |
| `classifications` | 사용자별 분류 세션 |
| `classification_results` | 문항별 응답·점수 (responses: jsonb) |
| `counseling_sessions` | 상담 세션 |
| `conversations` | 상담 대화 내용 |
| `summaries` | 상담 요약 (core_topics·prompt_adjustment: jsonb) |
| `voice_files` | 음성 파일 메타 |
| `crisis_events` | 위기 감지 이벤트 |

### Audit DB (5434, `heartbeat_audit`)
감사 추적 로그. **INSERT-only** 원칙 적용.

| 테이블 | 용도 |
|---|---|
| `audit_logs_general` | general DB 접근·변경 추적 |
| `audit_logs_sensitive` | sensitive DB 접근·변경 추적 |

## 5. 보안 설계

### 5.1 3-DB 물리 격리
일반 데이터와 임상 데이터를 **별개의 PostgreSQL 인스턴스**로 분리하여,
- 민감 DB만 별도의 접근 통제·백업 정책 적용 가능
- 한 DB의 장애·침해가 다른 DB로 전파되지 않음
- 백엔드 코드의 실수로도 DB 간 무단 참조가 물리적으로 불가능

### 5.2 audit DB의 INSERT-only 권한 분리
audit DB에는 두 종류의 접속 계정을 둡니다:

| 계정 | 권한 | 용도 |
|---|---|---|
| `heartbeat` (owner) | 전체 | 테이블 관리·마이그레이션 |
| `audit_writer` | INSERT, SELECT만 | **애플리케이션이 접속하는 계정** |

애플리케이션이 `audit_writer`로 접속함으로써,
**코드 버그나 SQL injection으로도 감사 로그를 수정·삭제할 수 없습니다.**
최소 권한 원칙(Principle of Least Privilege)을 적용한 변조 차단입니다.

### 5.3 크로스 DB 참조는 논리 참조
PostgreSQL은 DB 간 물리적 FK를 지원하지 않으므로,
sensitive/audit DB의 `user_id` 등은 **컬럼만 두고 FK 제약은 걸지 않습니다**.
참조 무결성은 백엔드 애플리케이션 계층에서 보장합니다.

## 6. 디렉터리 구조
db/
├── audit/init/        # audit DB 초기화 스크립트 (00~04)
├── general/init/      # general DB 초기화 스크립트 (01~04)
├── sensitive/init/    # sensitive DB 초기화 스크립트 (01~09)
└── README.md          # 본 문서

각 `init/` 폴더 내 `.sql`·`.sh` 파일은 알파벳 순으로
컨테이너 최초 기동 시 자동 실행됩니다.

## 7. 주요 변경 이력

| 일자 | 변경 | 비고 |
|---|---|---|
| (해당일) | ERD v4 적용 — DIAGNOSES 제거 후 classifications 3종 도입 | category_catalog / classifications / classification_results |
| (해당일) | `sessions.revoked_at` 추가 (TIMESTAMPTZ) | JWT refresh token 무효화 시각 |
| (해당일) | `summaries.core_topics` TEXT → JSONB | AI 출력의 배열 보존 |
| (해당일) | `summaries.prompt_adjustment` VARCHAR(255) → JSONB | AI 출력의 배열 보존 |
| (해당일) | audit DB `audit_writer` 롤 도입 (INSERT-only) | 변조 차단 |

## 8. 트러블슈팅

### `.sh: bad interpreter` 에러로 컨테이너가 unhealthy
init 스크립트(`.sh`)가 CRLF 줄바꿈으로 저장된 경우입니다.
VSCode 우하단에서 LF로 변경 후 저장, 또는 `.gitattributes`로 강제:
*.sh text eol=lf

### `variable is not set. Defaulting to a blank string.` 경고
프로젝트 루트의 `.env`가 누락되었거나 변수명이 잘못된 경우입니다.
`.env.example`을 참고하여 모든 키가 채워졌는지 확인하세요.

### init SQL을 수정했는데 반영이 안 됨
PostgreSQL Docker는 **빈 볼륨에 한해서만** init을 실행합니다.
변경을 반영하려면 볼륨까지 삭제:
```bash
docker compose down -v   # ⚠️ 모든 DB 데이터 삭제
docker compose up -d
```



## 9. 개발용 시드 데이터

`db/seed/` 폴더에 개발 환경에서만 쓰는 더미 데이터가 있습니다.
**프로덕션에서는 절대 실행하지 마세요.**

### 적용
```bash
docker exec -i heartbeat_db_general   psql -U heartbeat -d heartbeat_general   < db/seed/general.sql
docker exec -i heartbeat_db_sensitive psql -U heartbeat -d heartbeat_sensitive < db/seed/sensitive.sql
```

### 포함 데이터
- 사용자 3명 (test/admin/minor) — 비번은 모두 `Test1234!`
- 보호자 동의 1건
- PHQ-9 / GAD-7 카테고리 9개
- 분류·상담·대화·요약 한 세트

### 초기화
다시 처음부터 하고 싶으면 `down -v`로 DB 비우고 위 명령 재실행.