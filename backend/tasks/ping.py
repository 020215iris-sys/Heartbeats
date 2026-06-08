# backend/tasks/ping.py
"""
Celery 동작 확인용 헬스체크 태스크.

목적:
- worker 프로세스가 살아있는지 확인
- Redis 브로커 연결이 정상인지 검증
- 새 태스크 추가 시 디스커버리 패턴이 잘 동작하는지 확인

이 태스크는 production에서도 헬스체크/모니터링용으로 유지해도 OK.
"""
from datetime import datetime
from celery_app import celery_app


@celery_app.task(name="tasks.ping")
def ping_task() -> dict:
    """
    단순 핑 태스크 — 호출 시각과 상태를 반환.

    호출 (FastAPI 라우터나 Python shell에서):
        from tasks.ping import ping_task

        # 비동기 dispatch (즉시 반환, 워커가 백그라운드에서 실행)
        result = ping_task.delay()

        # 결과 대기 (최대 5초)
        print(result.get(timeout=5))
        # → {"status": "pong", "timestamp": "2026-06-08T15:30:00.123456"}

    Returns:
        dict: status와 KST 기준 timestamp
    """
    return {
        "status": "pong",
        "timestamp": datetime.now().isoformat(),
    }