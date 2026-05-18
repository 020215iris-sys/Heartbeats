import os
from dotenv import load_dotenv

load_dotenv() # .env 파일을 읽어 os.environ에 채워줌

class Config:
    # 세션 쿠키 서명용 비밀키 (.env의 SECRET_KEY 읽음)
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-fallback-key")

    # 백엔드(FastAPI) 주소 (.env의 API_BASE_URL 읽음)
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

    # Flask-WTF의 CSRF 보호 켜기 (폼 위조 공격 방어)
    WTF_CSRF_ENABLED = True

    # 비회원 체험 시 보낼 수 있는 메시지 개수.
    # .env의 GUEST_MESSAGE_LIMIT 값 사용, 없으면 5개 기본.
    # int()로 변환하는 이유: os.getenv가 항상 문자열을 반환하기 때문
    GUEST_MESSAGE_LIMIT = int(os.getenv("GUEST_MESSAGE_LIMIT", "5"))