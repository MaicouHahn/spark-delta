"""Acesso ao MinIO (API compatível com S3) via boto3."""

from __future__ import annotations

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from spark_delta.config import settings


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket(client, bucket: str) -> bool:
    """Cria o bucket se ele não existir. Retorna True quando criou."""
    try:
        client.head_bucket(Bucket=bucket)
        return False
    except ClientError:
        client.create_bucket(Bucket=bucket)
        return True


def list_objects(client, bucket: str, prefix: str = "") -> list[dict]:
    """Lista todos os objetos (com paginação) de um bucket/prefixo."""
    objetos = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objetos.extend(page.get("Contents", []))
    return objetos
