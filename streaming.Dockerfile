# Eclipse Temurin ships a correctly-configured JDK out of the box (JAVA_HOME
# already set, no guessing package names across Debian/Ubuntu releases).
# Python is layered on top instead of the other way around.
FROM eclipse-temurin:17-jdk-jammy

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pinned to match the Kafka connector version exactly.
RUN pip3 install --no-cache-dir pyspark==3.5.1

COPY streaming/spark_stream.py .

CMD ["python3", "spark_stream.py"]
