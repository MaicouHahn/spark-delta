"""Criação da SparkSession com Delta Lake e acesso ao MinIO via S3A."""

from __future__ import annotations

from pyspark.sql import SparkSession

from spark_delta.config import settings

# Versões compatíveis: PySpark 3.5.3 <-> Delta 3.2.0 (Scala 2.12) <-> Hadoop 3.3.4
SPARK_PACKAGES = ",".join([
    "io.delta:delta-spark_2.12:3.2.0",
    "org.apache.hadoop:hadoop-aws:3.3.4",
])

# Diretório das tabelas GERENCIADAS (bucket warehouse, prefixo spark-warehouse/)
WAREHOUSE_PREFIX = "spark-warehouse"
WAREHOUSE_DIR = f"s3a://{settings.warehouse_bucket}/{WAREHOUSE_PREFIX}"


def get_spark(app_name: str = "spark-delta") -> SparkSession:
    """Retorna uma SparkSession local configurada para Delta Lake + MinIO.

    ``spark.sql.warehouse.dir`` aponta para o bucket ``warehouse``: é ali que o
    Spark guarda os dados das TABELAS GERENCIADAS (criadas sem ``LOCATION``).
    As tabelas do bucket ``bronze`` são registradas com ``LOCATION`` e por isso
    são NÃO GERENCIADAS (externas).
    """
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.jars.packages", SPARK_PACKAGES)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.warehouse.dir", WAREHOUSE_DIR)
        # MinIO / S3A
        .config("spark.hadoop.fs.s3a.endpoint", settings.minio_endpoint)
        .config("spark.hadoop.fs.s3a.access.key", settings.minio_access_key)
        .config("spark.hadoop.fs.s3a.secret.key", settings.minio_secret_key)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .config("spark.hadoop.fs.s3a.aws.credentials.provider",
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
        .config("spark.sql.session.timeZone", "America/Sao_Paulo")
        .getOrCreate()
    )
