# 하트비트 상담 흐름 및 Prompt Agent 연결 정리

작성일: 2026-06-05  
담당: 백엔드 (지현)

---

## 1. 전체 상담 흐름 개요

```
로그인
↓
이전 Summary 있음? (summaries 테이블 조회)
↓                        ↓
없음 (첫 상담)           있음 (재상담)
↓                        ↓
Groq 직접 대화           Prompt Agent 호출
(프롬프트 없음)          (system_prompt 생성)
↓                        ↓
        상담 진행 (Groq + history)
        ↓
        conversations 테이블 저장
        ↓
        상담 종료? (로그아웃 / 60분 / 새 채팅)
        ↓
        summaries 저장
        (LoRA 4개 컬럼 + Groq 위험도 2개 컬럼)
        ↓
        다음 재상담
```

---

## 2. 핵심 개념 정리

### system_content (= system_prompt)
- Groq한테 보내는 `messages[0]`, 즉 **AI 행동 지침**
- 재상담 시 → Prompt Agent가 summary 기반으로 생성한 값
- 첫 상담 시 → 현재 빈 값 (`""`)

```python
messages[0] = {"role": "system", "content": system_content}
messages[1] = {"role": "user", "content": "안녕"}
```

### Prompt Agent
- LLM(Groq)에 `prompt_agent_prompt.txt`를 system으로 넣고 호출하는 것
- 입력: summary 6개 컬럼 + 설문결과 + 닉네임
- 출력: `{"system_prompt": "ss님, 지난 상담에서...", "reason": "..."}`
- 이 출력값이 `system_content`가 됨

### summaries 테이블 6개 컬럼
| 컬럼 | 생성 주체 |
|------|-----------|
| main_complaint | LoRA (Colab) |
| core_topics | LoRA (Colab) |
| next_session_notes | LoRA (Colab) |
| prompt_adjustment | LoRA (Colab) |
| risk_level | Groq |
| suicidal_mentioned | Groq |

---

## 3. Prompt Agent INPUT 구조

```json
{
  "nickname": "사용자",
  "classification_results": {
    "category_code": "PHQ9",
    "total_score": 10,
    "severity": "moderate",
    "score_delta": 0
  },
  "summary": {
    "main_complaint": "...",
    "core_topics": [],
    "next_session_notes": "...",
    "prompt_adjustment": []
  },
  "risk_level": "low",
  "suicidal_mentioned": false
}
```

현재 `classification_results: {}` 빈값 → 설문 결과가 CSV에만 저장되고 DB 미연결 상태

---

## 4. 현재 문제점

### 문제 1: 재상담 채팅에서 매 메시지마다 agent 재호출
- **원인**: `system_content`가 메모리에만 존재, 요청 끝나면 사라짐
- **현상**: 메시지 보낼 때마다 Prompt Agent 호출 → 토큰 낭비 + 속도 저하

```
첫 메시지  → agent 호출 → system_prompt 생성 → 사라짐
두 번째    → agent 또 호출 → 또 생성 → 사라짐
세 번째    → agent 또또 호출...
```

- **해결**: `counseling_sessions` 테이블에 `system_prompt TEXT` 컬럼 추가

```
첫 메시지  → agent 호출 → system_prompt 생성 → DB 저장
두 번째    → DB에서 꺼내서 재사용 (agent 호출 없음)
세 번째    → 재사용
```

### 문제 2: 첫 상담 프롬프트 없음
- 현재 `system_content = ""` 빈 값으로 Groq이랑 대화
- **예정**: 회원가입 시 설문 + 개인정보 기반으로 나중에 연결

### 문제 3: classification_results 빈값
- 설문 결과가 CSV에만 저장되고 DB 미연결
- agent INPUT에 빈값으로 들어가서 설문 기반 상담 불가

### 문제 4: system_prompt 품질 저하
- agent가 만들어주는 system_prompt가 너무 짧거나 외국어 섞임
- `prompt_agent_prompt.txt` 개선 필요

---

## 5. 원하는 최종 흐름

```
재상담 첫 메시지
↓
agent 1번 호출
입력: summary(이전상담요약) + 설문결과 + 개인정보
↓
system_prompt 생성 (모든 정보가 녹아있음)
↓
counseling_sessions.system_prompt 에 저장

재상담 두 번째 메시지부터
↓
DB에서 system_prompt 꺼냄 (agent 호출 없음)
↓
[system_prompt + Groq history + 현재메시지] → Groq
```

**핵심**: system_prompt 안에 summary + 설문 + 개인정보가 모두 녹아있어서
이후 대화에서 따로 또 보낼 필요 없음

---

## 6. 필요한 작업

### DB 담당자
- `counseling_sessions` 테이블에 `system_prompt TEXT` 컬럼 추가
- 이유: 재상담 시 agent가 생성한 system_prompt를 저장해두고 같은 세션 안에서 재사용하기 위함

### AI파트 담당자
`prompt_agent_prompt.txt` 수정 요청:
- 반드시 한국어로만 작성 (현재 외국어 섞임)
- 최소 5문장 이상
- summary, 설문결과, 개인정보를 상담 전략에 구체적으로 반영
- 입력 스키마: `nickname`, `classification_results`, `summary`, `risk_level`, `suicidal_mentioned`

### 백엔드
DB 컬럼 추가 후:
- 재상담 첫 메시지 → agent 호출 → `counseling_sessions.system_prompt` 저장
- 두 번째 메시지부터 → DB에서 꺼내서 재사용
- `classification_results` 설문 DB 연결 (설문 완성 후)

---

## 7. 현재 완료된 작업

- `general_prompt` → `prompt_agent_prompt` 교체 완료
- summary 있을 때만 agent 호출 (`if recent_summary:`)
- 닉네임 JWT에 추가 (auth.py)
- 한글 외 모든 외국어 감지 차단
- 상담 종료 시 중요 사건 추출 (`important_memory`) 추가 - 터미널 출력만, DB 미저장
- 디버깅 print 추가 (AGENT INPUT / OUTPUT / LLM SYSTEM PROMPT)

---

## 8. 관련 파일

| 파일 | 역할 |
|------|------|
| `backend/backend_main.py` | 채팅 엔드포인트, agent 호출 |
| `backend/routers/counseling.py` | 세션 종료, 요약 저장 |
| `backend/routers/auth.py` | 로그인, JWT 생성 |
| `backend/summary_service.py` | Colab LoRA 호출 |
| `ai/prompts/active/prompt_agent_prompt.txt` | agent 지시문 |
| `ai/prompts/active/general_prompt.txt` | 구 프롬프트 (현재 미사용) |
