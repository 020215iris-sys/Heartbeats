# backend/celery_app.py
"""
Celery 앱 초기화 (Asynchronous Task Queue)

이 모듈이 다루는 것:
- Celery 인스턴스 생성 + Redis 브로커 연결
- 자동 태스크 디스커버리 (backend/tasks/ 하위 모듈)
- Asia/Seoul 타임존 적용 (Beat 스케줄 시각 정확성)
- JSON 직렬화 강제 (pickle 대비 보안)

사용:
    from celery_app import celery_app

    @celery_app.task
    def my_task(arg):
        ...

    # 다른 곳에서 호출
    my_task.delay("hello")  # 비동기 dispatch — 워커가 처리
"""
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()  # backend/.env 자동 로드 (로컬 개발용)


# ──────────────────────────────────────────
# 1. Redis 연결 URL
# ──────────────────────────────────────────
# docker-compose 네트워크에서 redis 서비스명으로 접근.
# 환경변수가 있으면 우선, 없으면 기본값 사용 (개발 안전망).
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    f"redis://{REDIS_HOST}:{REDIS_PORT}/0",   # Redis DB 0 = 메시지 큐
)
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    f"redis://{REDIS_HOST}:{REDIS_PORT}/1",   # Redis DB 1 = 태스크 결과 (격리)
)


# ──────────────────────────────────────────
# 2. Celery 앱 인스턴스
# ──────────────────────────────────────────
celery_app = Celery(
    "heartbeat",                       # 앱 식별자 (Flower 모니터링 등에 표시)
    broker=CELERY_BROKER_URL,          # 태스크 메시지 큐
    backend=CELERY_RESULT_BACKEND,     # 태스크 결과 저장소
    include=["tasks"],                 # 자동 import할 모듈 (Step 3에서 만듦)
)


# ──────────────────────────────────────────
# 3. Celery 동작 설정
# ──────────────────────────────────────────
celery_app.conf.update(
    # 타임존 — Beat 스케줄("매일 오전 9시" 등)의 기준 시각
    timezone="Asia/Seoul",
    enable_utc=False,

    # 직렬화 — JSON만 허용 (pickle은 임의 코드 실행 위험)
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # 결과 저장 만료 (Redis DB 1에 무한정 쌓이지 않도록)
    result_expires=3600,                  # 1시간

    # 워커 prefetch — 1로 두면 태스크가 워커에 공평하게 분배됨
    worker_prefetch_multiplier=1,

    # 태스크 완료 후 ACK — 실패 시 재시도 가능 (메시지 유실 방지)
    task_acks_late=True,
    
    broker_connection_retry_on_startup=True,

)