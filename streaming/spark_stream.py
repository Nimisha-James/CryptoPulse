from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, avg, stddev, to_timestamp
from pyspark.sql.types import StructType, StringType, DoubleType

spark = SparkSession.builder \
    .appName("CryptoStreamProcessor") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1") \
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
    .option("kafka.bootstrap.servers", "localhost:9092") \
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
)

query = rolling_metrics.writeStream \
    .outputMode("update") \
    .format("console") \
    .option("truncate", False) \
    .start()

query.awaitTermination()
