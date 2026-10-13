"""Conexão com o SQL Server via pyodbc (ODBC Driver 18)."""

from __future__ import annotations

import pyodbc

from spark_delta.config import settings

ODBC_DRIVER = "ODBC Driver 18 for SQL Server"


def connect(database: str | None = None, autocommit: bool = True) -> pyodbc.Connection:
    """Abre uma conexão. Sem ``database`` conecta no ``master``."""
    conn_str = (
        f"DRIVER={{{ODBC_DRIVER}}};"
        f"SERVER={settings.db_server},{settings.db_port};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        "TrustServerCertificate=yes;"
    )
    if database:
        conn_str += f"DATABASE={database};"
    return pyodbc.connect(conn_str, autocommit=autocommit)
