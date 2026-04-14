FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir requests

COPY main.py .

EXPOSE 8000

CMD ["python3", "main.py"]
