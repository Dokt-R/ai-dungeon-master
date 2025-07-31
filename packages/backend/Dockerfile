# Backend Dockerfile
FROM python:3.13-slim

WORKDIR /

COPY /packages/backend /packages/backend
COPY /packages/shared /packages/shared
COPY /packages/__init__.py /packages

RUN pip install --no-cache-dir -r packages/backend/requirements.txt

EXPOSE 8000

CMD ["uvicorn", "packages.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]