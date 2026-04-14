FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir schedule

COPY main.py .

CMD ["python3", "main.py"]
