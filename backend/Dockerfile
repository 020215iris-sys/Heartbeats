
FROM python:3.10-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
COPY ai/ /ai/
CMD ["uvicorn", "backend_main:app", "--host", "0.0.0.0", "--port", "8000"]