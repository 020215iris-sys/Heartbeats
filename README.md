# 🫀 Heartbeat

> **Prompt Agent 기반 개인화 AI 정서 케어 서비스**
> 사용자의 상담 맥락을 기억하고, 개인 맞춤형 상담을 제공하는 AI 심리 상담 플랫폼

![Status](https://img.shields.io/badge/status-active-success)
![Python](https://img.shields.io/badge/Python-3.10-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![Docker](https://img.shields.io/badge/Docker-2496ED)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

# 목차

* 프로젝트 소개
* 프로젝트 배경
* 핵심 기능
* 시스템 아키텍처
* 기술 스택
* 디렉토리 구조
* 설치 및 실행
* 브랜치 전략
* 팀 구성

---

# 프로젝트 소개

Heartbeat는 AI 상담의 **기억 단절 문제**를 해결하기 위해 개발한
개인 맞춤형 AI 정서 케어 서비스입니다.

기존 AI 상담은 이전 대화의 맥락을 충분히 유지하지 못해
상담의 연속성과 개인화 측면에서 한계가 존재했습니다.

Heartbeat는 Prompt Agent 기반 상담 메모리 구조를 통해
사용자의 상담 이력을 반영하고,
위기 상황 감지 및 맞춤형 상담을 제공하는 것을 목표로 합니다.

---

# 프로젝트 배경

최근 정신건강 서비스 수요는 지속적으로 증가하고 있지만,

* 상담 비용 부담
* 상담 접근성 부족
* 상담사의 부족
* 지속적인 상담 관리의 어려움

등의 문제가 존재합니다.

Heartbeat는 이러한 문제를 AI 기술을 활용하여
보완할 수 있는 정서 케어 서비스를 목표로 개발되었습니다.

---

#  핵심 기능

### 🤖 AI 상담

* 자연스러운 대화형 상담
* 상담 기록 기반 응답 생성
* 사용자 맞춤형 페르소나 제공

### 🧠 Prompt Agent

* 상담 요약 생성
* 장기 메모리 관리
* System Prompt 자동 생성

### 🚨 위기 감지

* Function Calling 기반 위험도 분류
* 자해·자살 위험 감지
* 안전 안내 프로세스 제공

### 📊 상담 기록 관리

* 상담 요약 저장
* 감정 변화 추적
* 사용자 상담 이력 관리

---

# 🏗 시스템 아키텍처

(아키텍처 이미지 삽입)

```
Frontend
        │
        ▼
Backend (FastAPI)
        │
        ▼
Prompt Agent
        │
        ├── Summary Memory
        ├── Persona
        ├── Risk Detection
        ▼
LLM (Cerebras)
        │
        ▼
PostgreSQL / Redis
```

---

# 🛠 기술 스택

| 분야       | 기술                                     |
| -------- | -------------------------------------- |
| Frontend | HTML, CSS, JavaScript                  |
| Backend  | FastAPI                                |
| AI       | Cerebras API, LoRA, Prompt Engineering |
| Database | PostgreSQL, Redis                      |
| DevOps   | Docker, GitHub                         |
| ETC      | SQLAlchemy, Alembic                    |

---

# 📂 디렉토리 구조

```text
Heartbeats/
│
├── ai/                    # AI 모델 및 추론 파이프라인
│   ├── app/               # AI 서비스 로직
│   ├── data/              # 학습/평가 데이터
│   ├── prompts/           # Prompt 템플릿
│   ├── scripts/           # 학습 및 유틸리티 스크립트
│   └── requirements.txt
│
├── backend/               # FastAPI 서버
│   ├── core/              # 공통 설정 및 핵심 모듈
│   ├── routers/           # API 라우터
│   ├── services/          # 비즈니스 로직
│   ├── questionnaires/    # 심리검사(PHQ-9, GAD-7, ISI)
│   ├── tasks/             # Celery 비동기 작업
│   ├── alembic/           # DB 마이그레이션
│   └── backend_main.py
│
├── frontend/              # 사용자 웹 인터페이스
│   ├── app/
│   └── run.py
│
├── db/                    # 데이터베이스 설계 및 관리
│   ├── general/           # 일반 데이터
│   ├── sensitive/         # 민감 정보
│   ├── audit/             # 감사 로그
│   └── seed/              # 초기 데이터
│
├── docs/                  # 프로젝트 문서
├── scripts/               # 공용 실행 스크립트
│
├── docker-compose.yml
├── README.md
└── .env.example
```

```

---

# 🚀 설치 및 실행

```bash
git clone https://github.com/organization/Heartbeat.git

cd Heartbeat
```

### Backend

```bash
pip install -r requirements.txt

uvicorn backend_main:app --reload
```

### Frontend

```bash
pip install -r requirements.txt

python run.py
```

---

# 🌿 브랜치 전략

Git Flow를 기반으로 협업을 진행했습니다.

```
main

feature/ai

feature/backend

feature/frontend

feature/db
```

### 작업 프로세스

1. develop 최신화
2. feature 브랜치 생성
3. 기능 개발
4. Pull Request 생성
5. Code Review
6. Merge
7. Release

---

# 👥 Team

| Part     | Description                                |
| -------- | ------------------------------------------ |
| AI       | Prompt Agent, LLM, Summary, Risk Detection |
| Backend  | API, Authentication, Business Logic        |
| Frontend | UI/UX, Chat Interface, Data collection     |
| Database | Schema Design, Migration, Data Management  |

---

# 📈 Project Goals

* 상담의 맥락을 유지하는 AI 상담 구현
* 사용자 맞춤형 정서 케어 제공
* 위기 상황 감지 및 안전 프로세스 구축
* AI와 웹 서비스를 통합한 실사용 가능한 플랫폼 개발

---

# 📄 License

This project is licensed under the MIT License.
