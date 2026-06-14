# backend/tasks/__init__.py
"""
Celery 태스크 모듈 진입점.

celery_app의 include=["tasks"]에 의해 워커 기동 시 이 파일이 import됨.
새 태스크 모듈을 추가할 때마다 여기서 명시적으로 import해야
Celery가 태스크를 등록하고 worker가 받아갈 수 있음.

추가 예시:
    from .ping import ping_task
    from .cleanup import delete_old_conversations
    from .notify import send_guardian_alert
"""
from .ping import ping_task  # 헬스체크 태스크
from .summary import summarize_latest_active_session
from .cleanup import (
    soft_delete_old_conversations,
    soft_delete_old_summaries,
    soft_delete_old_classifications,
    anonymize_old_counseling_sessions,
)