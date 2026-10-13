"""Configuração central do projeto, lida do arquivo ``.env`` na raiz.

Os notebooks ficam em ``notebook/``, mas o ``.env`` e a pasta ``data/`` ficam na
raiz. Resolver os caminhos a partir deste arquivo evita depender do diretório
em que o Jupyter foi aberto.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(PROJECT_ROOT / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    # SQL Server
    db_server: str = os.getenv("DB_SERVER", "localhost")
    db_port: str = os.getenv("DB_PORT", "1433")
    db_user: str = os.getenv("DB_USER", "sa")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_database: str = os.getenv("DB_DATABASE", "LojaDB")
    db_schema: str = os.getenv("DB_SCHEMA", "dbo")

    # MinIO
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "http://localhost:9020")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    landing_bucket: str = os.getenv("MINIO_LANDING_BUCKET", "landing-zone")
    bronze_bucket: str = os.getenv("MINIO_BRONZE_BUCKET", "bronze")
    warehouse_bucket: str = os.getenv("MINIO_WAREHOUSE_BUCKET", "warehouse")


settings = Settings()
