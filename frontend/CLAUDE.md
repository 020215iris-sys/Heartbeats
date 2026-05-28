# 하트비트 프론트엔드 — Claude Code 안내

## 프로젝트 한 줄
정신건강 AI 상담 서비스 "하트비트"의 **프론트엔드** (팀 4명 중 1명, 본인은 프론트엔드).
백엔드(FastAPI, 송지현)·DB(PostgreSQL, 이새봄)·AI(현다은)는 별도 팀원 영역이며 아직 미연동 상태.

## 절대 규칙 (위반 금지)

0. **`frontend/` 폴더 내 파일만 수정한다.**
   백엔드(`backend/`), DB(`db/`), 루트 등 외부 파일 수정 금지.
   외부 수정이 필요하면 `frontend/` 안에 `[주제]_수정필요.txt` 파일로 기록만 남긴다.

1. **진단 데이터는 절대 프론트엔드 디스크에 저장하지 않는다.**
   ERD에서 민감 DB (port 5433)로 분리된 영역. 정신건강 검사 결과는 개인정보보호법상 민감정보.
   진단 결과는 세션에만 임시 보관. 영구 저장은 백엔드 책임.

2. **비밀번호는 `werkzeug.security`로 해시 (절대 평문 저장 금지).**
   이미 적용됨. 컬럼명은 `hashed_password` (not `password_hash` — ERD 표기 따름).

3. **모든 폼은 Flask-WTF + CSRF 보호.**
   raw `<form>` + `request.form.get()` 사용 금지. WTForms 클래스 만들고 `{{ form.hidden_tag() }}` 사용.

4. **ERD 필드명 그대로 사용.**
   `hashed_password`, `nickname`, `phone_number`, `is_active`, `created_at`, `last_login_at`, `deleted_at`.
   id는 모두 UUID (`uuid.uuid4()`).

5. **외부(백엔드) 호출은 반드시 `app/services/api_client.py`를 통해서만.**
   백엔드 붙으면 이 파일만 갈아끼우면 됨. 라우트에서 직접 `requests.post()` 호출 금지.

## 기술 스택

- Python 3.10+ (`dict | None` union 문법 사용)
- Flask 3.0 + Jinja2
- Flask-WTF + WTForms
- Tailwind CSS (CDN, 운영 단계에서 빌드 파이프라인으로 교체 예정)
- 세션: Flask 기본 (쿠키 기반)
- 비밀번호: werkzeug scrypt
- 임시 저장소: CSV (`data/users.csv` — gitignored, dev 전용)

**왜 Flask인가:** 원안은 React + TS였으나 담당자(현표)가 Python만 학습된 상태라 변경. MVP 일정 우선.

## 실행

```bash
cd frontend
source venv/bin/activate      # Windows: venv\Scripts\activate
python run.py
# → http://localhost:5173
```

`.env` 필수 키: `SECRET_KEY`, `API_BASE_URL`, `GUEST_MESSAGE_LIMIT`.

## 폴더 구조

```
frontend/
├── .env, .env.example, .gitignore
├── Dockerfile
├── requirements.txt
├── run.py                    # 진입점
├── data/                     # CSV 저장소 (gitignored)
│   └── users.csv
└── app/
    ├── __init__.py           # 앱 팩토리 + 컨텍스트 프로세서
    ├── config.py
    ├── extensions.py         # csrf 인스턴스
    ├── forms/                # WTForms 폼 클래스
    │   ├── auth.py
    │   ├── survey.py         # 동적 폼 생성기 (build_survey_form)
    │   └── chat.py
    ├── routes/               # Blueprint별 라우트
    │   ├── main.py           # 랜딩, 게스트 시작
    │   ├── auth.py           # 로그인/가입/로그아웃
    │   ├── survey.py         # 초기 설문
    │   └── chat.py           # 채팅
    ├── services/             # 외부 통신/비즈니스 로직
    │   ├── api_client.py     # 백엔드 호출 (현재 mock)
    │   ├── user_storage.py   # users.csv 다루는 모듈
    │   ├── guest.py          # 게스트 세션 관리
    │   └── personas.py       # 상담사 페르소나 데이터
    ├── questionnaires/       # 설문 도구 정의
    │   ├── __init__.py       # 점수/심각도/follow-up 헬퍼
    │   └── placeholder.py    # 임시 설문 (실제 도구 정해지면 교체)
    └── templates/
        ├── base.html         # 공통 레이아웃 + 헤더
        ├── landing.html
        ├── auth/login.html, signup.html
        ├── survey/initial.html, result.html
        └── chat/room.html
```

## 핵심 패턴

### 앱 팩토리
`create_app()` 함수 안에서 Flask 앱 생성·blueprint 등록·확장 초기화. 전역 `app` 변수 안 씀.

### 컨텍스트 프로세서
`current_user` dict가 모든 템플릿에 자동 주입. 세 상태:
- `current_user.status == "anonymous"` (비로그인)
- `current_user.status == "guest"` (익명 체험)
- `current_user.status == "authenticated"` (회원)

### 동적 폼 생성
설문 폼은 `forms/survey.py`의 `build_survey_form(instrument)`로 런타임 생성.
`type()` 메타프로그래밍 사용. 문항 수가 바뀌어도 코드 변경 불필요.

### 게스트 모드
`services/guest.py`의 함수들이 세션에서 `guest_active`, `guest_message_count`를 관리.
한도(`GUEST_MESSAGE_LIMIT`, 기본 5) 초과 시 회원가입으로 유도.

### 페르소나
`services/personas.py`에 상담사 캐릭터 정의 (이름, 아바타, 강조 색, 첫 인사말).
채팅 라우트가 페르소나 dict를 템플릿에 넘김.

## 데이터 모델

### users.csv (ERD `USERS` 매핑, MVP 임시)
```
id, email, nickname, hashed_password, phone_number, phone_verified,
role, is_active, created_at, last_login_at, deleted_at
```

### 세션 키
- 인증: `access_token`, `user_id`, `email`, `nickname`, `role`
- 게스트: `guest_active`, `guest_message_count`
- 채팅: `chat_messages` (최근 20개 슬라이딩, 쿠키 4KB 제한)
- 설문: `last_survey_result`, `last_diagnosis_id`
- 페르소나: `persona_code` (선택, 없으면 기본 "empathy")

### 진단 결과 — 디스크 저장 안 함
세션의 `last_survey_result`에만 임시 저장. 새로고침은 살아남지만 로그아웃 시 사라짐.
영구 저장은 백엔드 영역 (`POST /diagnoses` 백엔드 API 명세는 [노션 링크] 참고).

## 사용자 상태 분기 (헤더, 라우트 권한 등)

```python
is_authenticated = "access_token" in session
is_guest = guest_svc.is_guest()
# 둘 다 False면 anonymous

# 예: 채팅 페이지는 authenticated 또는 guest만
if not is_authenticated and not is_guest:
    return redirect(url_for("main.landing"))
```

## 구현 완료

- [x] 회원가입/로그인 (이메일+비번+닉네임+휴대폰)
- [x] 역할 선택 (사용자/보호자, 카드 UI)
- [x] CSV 저장소 (users.csv), 이메일/휴대폰 unique 검증
- [x] 게스트 모드 + 한도
- [x] 헤더 동적 처리 (3가지 상태)
- [x] 초기 설문 placeholder (다질환 구조)
- [x] 점수/심각도/follow-up 평가 로직
- [x] 설문 결과 페이지
- [x] 채팅 페이지 (페르소나 캐릭터 헤더, 말풍선, 음성 자리)
- [x] 1393 안전 안내 (채팅 페이지)

## 진행 중 / 다음 단계

우선순위 순:

- [ ] **결과 페이지 → 채팅 연결**: 설문 결과 "AI 상담 시작하기" 버튼이 실제로 `/chat/`로 이동
- [ ] **위기 감지 모달**: 자살/자해 키워드 트리거 시 1393 안내 모달 (백엔드 신호 받을 준비)
- [ ] **페르소나 선택 화면**: 사용자가 다온/라온/온유 중 선택
- [ ] **`@login_required` 변형 데코레이터**: guest 또는 authenticated만 접근 가능한 보호된 페이지용
- [ ] **음성 모드 실 구현**: Web Speech API로 STT/TTS (브라우저 내장)
- [ ] **보호자 연결**: 사용자가 초대 코드 발급 → 보호자가 그 코드로 가입 후 연결

## 의사결정 기록

| 결정 | 이유 |
|---|---|
| SMS 인증 보류 (Phase 4) | 비용·이탈률·복잡도. MVP 어뷰징 위협 낮음 |
| 소셜 로그인 보류 (Phase 4~5) | 익명성 가치와 충돌, 전화번호 필수화와도 충돌 |
| placeholder 설문 사용 | 실제 도구(PHQ-9 vs 다른 거) 팀에서 미확정 |
| 다질환 구조 지원 | 1차 선별 → 2차 표적 흐름 위해 한 문항이 여러 질환에 기여하는 구조 |
| 진단 데이터 영구 저장 안 함 | 민감정보, 백엔드/DB 영역. ERD가 민감 DB로 분리해둠 |

## 코딩 컨벤션

- 함수 docstring 권장 (특히 services 레이어)
- 한국어 주석 OK
- 사용자 표시 텍스트는 항상 한국어
- 변수명은 영어 snake_case
- WTForms validator `message=` 는 한국어
- 시간은 UTC ISO 8601 (`datetime.now(timezone.utc).isoformat()`)
- `print` 디버깅 후 반드시 제거. 운영 환경에선 `app.logger.info` 사용

## 참고 링크

- 기획서: [노션 링크 추가]
- ERD v2: [노션 링크 추가]
- 백엔드 API 명세 초안: [노션 링크 추가]