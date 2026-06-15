FROM python:3.10-slim

WORKDIR /app

# 의존성 먼저 복사·설치 (Docker 캐싱 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 코드 복사
COPY . .

# Flask 포트
EXPOSE 5173

# 실행
CMD ["python", "run.py"]