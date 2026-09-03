FROM python:3.12-slim

WORKDIR /app
COPY cloud/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY cloud /app/cloud

ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/cloud/odds_collector.py"]
