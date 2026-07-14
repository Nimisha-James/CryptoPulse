import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, avg, stddev, to_timestamp
from pyspark.sql.types import StructType, StringType, DoubleType

KAFKA_HOST = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")

spark = SparkSession.builder \
    .appName("CryptoStreamProcessor") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.postgresql:postgresql:42.7.3") \
    .config("spark.sql.shuffle.partitions", "3") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

schema = StructType() \
    .add("asset", StringType()) \
    .add("price_usd", DoubleType()) \
    .add("volume_24h", DoubleType()) \
    .add("change_24h_pct", DoubleType()) \
    .add("event_time", DoubleType())

raw_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_HOST) \
    .option("subscribe", "crypto_prices") \
    .option("startingOffsets", "latest") \
    .load()

parsed = raw_stream.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

parsed = parsed.withColumn("event_timestamp", to_timestamp(col("event_time")))

# Watermark: tolerate events up to 2 minutes late before considering them "too late" to include
watermarked = parsed.withWatermark("event_timestamp", "2 minutes")

rolling_metrics = watermarked.groupBy(
    window(col("event_timestamp"), "5 minutes", "1 minute"),
    col("asset")
).agg(
    avg("price_usd").alias("avg_price"),
    stddev("price_usd").alias("volatility")
).select(
    col("window.start").alias("window_start"),
    col("window.end").alias("window_end"),
    col("asset"),
    col("avg_price"),
    col("volatility")
)

def write_to_postgres(batch_df, batch_id):
    batch_df.write \
        .format("jdbc") \
        .option("url", f"jdbc:postgresql://{POSTGRES_HOST}:5432/crypto_db") \
        .option("dbtable", "live_metrics") \
        .option("user", "dataeng") \
        .option("password", "dataeng123") \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()

query = rolling_metrics.writeStream \
    .outputMode("update") \
    .foreachBatch(write_to_postgres) \
    .start()

query.awaitTermination()