# Producer + simple_consumer share this image — same dependencies,
# different CMD chosen at the docker-compose service level.
FROM python:3.11-slim

WORKDIR /app

COPY producer_requirements.txt .
RUN pip install --no-cache-dir -r producer_requirements.txt

COPY producer/producer.py .
COPY producer/simple_consumer.py .

# Default command — overridden per-service in docker-compose.yml
CMD ["python", "producer.py"]
