# 1. Extração: SQL Server → `landing-zone`

Notebooks: `00_setup_sqlserver.ipynb` (preparação) e `01_sqlserver_to_minio_csv.ipynb` (extração).

## Preparação do banco (notebook 00)

1. Conecta no `master` e cria o database `LojaDB` se ele não existir.
2. Cria as 7 tabelas (ver [DDL](dados.md#ddl-no-sql-server)) só se ainda não existirem.
3. Carrega `data/<tabela>.csv` em cada tabela, em lotes de 2.000 linhas, pulando as que já têm dados. Assim o notebook pode ser executado de novo sem duplicar registros.
4. Valida a contagem de cada tabela e mostra um `JOIN` entre `produto`, `categoria` e `estoque`.

## Extração (notebook 01)

### Descoberta das tabelas

A lista não está fixa no código: é lida do próprio banco. Uma tabela nova no schema `dbo` seria extraída automaticamente.

```python
cursor.execute("""
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = ?
    ORDER BY TABLE_NAME
""", settings.db_schema)
tabelas = [row[0] for row in cursor.fetchall()]
```

### Exportação para o MinIO

Para cada tabela: `SELECT *` → DataFrame pandas → CSV em memória → `put_object` no bucket. Nenhum arquivo intermediário é gravado em disco.

```python
for tabela in tabelas:
    cursor.execute(f"SELECT * FROM [{settings.db_schema}].[{tabela}]")
    colunas = [d[0] for d in cursor.description]
    df = pd.DataFrame.from_records(cursor.fetchall(), columns=colunas)

    buffer = io.StringIO()
    df.to_csv(buffer, index=False, date_format="%Y-%m-%d %H:%M:%S")

    s3.put_object(Bucket=settings.landing_bucket, Key=f"{tabela}.csv",
                  Body=buffer.getvalue().encode("utf-8"), ContentType="text/csv")
```

O `date_format` fixo garante que datas e horas cheguem num formato único, que é o mesmo informado ao Spark na etapa seguinte.

### Resultado

```text
s3://landing-zone/
├── categoria.csv
├── cliente.csv
├── estoque.csv
├── fornecedor.csv
├── item_venda.csv
├── produto.csv
└── venda.csv
```

!!! question "Por que CSV na landing-zone?"
    O enunciado pede CSV para bancos relacionais (JSON seria para não relacionais). A landing-zone guarda uma cópia **simples e fiel** do que saiu da origem, legível por qualquer ferramenta. A tipagem e o formato transacional ficam para a bronze.
