# Bot Dockerfile
FROM python:3.13-slim

WORKDIR /

COPY /packages/bot /packages/bot
COPY /packages/shared /packages/shared
COPY /packages/__init__.py /packages

RUN pip install --no-cache-dir -r packages/bot/requirements.txt

CMD ["python", "packages/bot/main.py"]