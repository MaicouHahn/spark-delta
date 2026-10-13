# Delta Lake

## O que é

O **Delta Lake** é um formato de tabela de código aberto, criado pela Databricks (empresa fundada pelos criadores do Spark) e hoje mantido na Linux Foundation. Ele adiciona a um data lake recursos que antes só existiam em bancos de dados: **transações ACID, atualização e exclusão de linhas, versionamento e controle de schema**.

Uma tabela Delta é uma pasta com:

- **arquivos Parquet** com os dados (formato colunar e comprimido);
- a pasta **`_delta_log/`**, o *log de transações*: um arquivo JSON por versão da tabela, descrevendo quais arquivos Parquet foram adicionados e removidos em cada operação.

```text
s3a://bronze/produto/
├── _delta_log/
│   ├── 00000000000000000000.json   ← versão 0: carga do CSV (notebook 02)
│   ├── 00000000000000000001.json   ← versão 1: INSERT (notebook 03)
│   ├── 00000000000000000002.json   ← versão 2: UPDATE
│   └── ...
├── part-00000-....snappy.parquet
└── part-00000-....snappy.parquet
```

Para ler a tabela, o Spark consulta o log e descobre quais arquivos Parquet formam a versão desejada. Por isso o Delta funciona sobre um object storage como o MinIO, que não tem nenhum mecanismo de tabela.

## Recursos demonstrados no trabalho

| Recurso | O que significa | Onde aparece |
|---|---|---|
| **ACID** | Cada operação é atômica: ou o commit no `_delta_log` acontece inteiro, ou nada muda | Todo `write`, `INSERT`, `UPDATE`, `DELETE` |
| **DML** | `INSERT`, `UPDATE`, `DELETE` por linha, via SQL ou API Python `DeltaTable` | Notebook 03 |
| **Schema enforcement** | Gravações com colunas ou tipos incompatíveis são rejeitadas | Notebook 03 (`INSERT` respeitando o schema) |
| **Histórico** | `DESCRIBE HISTORY` lista cada versão, operação e métricas | Notebook 03 |
| **Time Travel** | Ler a tabela como estava numa versão anterior (`versionAsOf`) | Notebook 03 |

## Como o UPDATE e o DELETE funcionam

Arquivos Parquet são imutáveis. Para alterar uma linha, o Delta:

1. encontra os arquivos que contêm as linhas afetadas;
2. reescreve esses arquivos com as linhas alteradas (ou sem as linhas removidas);
3. grava uma nova versão no `_delta_log` marcando os arquivos antigos como removidos e os novos como adicionados.

Os arquivos antigos **continuam no storage**: é isso que permite o Time Travel. Eles só são apagados fisicamente pelo comando `VACUUM`, depois do período de retenção (7 dias por padrão).

## Duas formas de executar DML

=== "Spark SQL"

    ```python
    spark.sql("UPDATE produto SET preco = 3500.00 WHERE cd_produto = 9001")
    spark.sql("DELETE FROM estoque WHERE cd_produto = 9003")
    ```

=== "API DeltaTable (Python)"

    ```python
    from delta.tables import DeltaTable
    from pyspark.sql import functions as F

    dt = DeltaTable.forPath(spark, "s3a://bronze/estoque")
    dt.update(condition=F.col("cd_produto") == 9001,
              set={"quantidade": F.lit(15)})

    DeltaTable.forPath(spark, "s3a://bronze/produto").delete("cd_produto = 9003")
    ```

As duas geram o mesmo resultado e o mesmo tipo de entrada no histórico. O notebook 03 usa as duas.

## Histórico e Time Travel

```python
# Todas as versões da tabela
spark.sql("DESCRIBE HISTORY produto").select("version", "operation").show()

# Tabela como estava na versão 0
spark.read.format("delta").option("versionAsOf", 0).load("s3a://bronze/produto")
```

## Delta × Iceberg (Trabalho 1)

No Trabalho 1 o grupo usou também o **Apache Iceberg**, que resolve o mesmo problema (tabelas transacionais sobre arquivos Parquet) com outra organização de metadados: em vez de um log de transações, o Iceberg mantém arquivos de metadados com **snapshots** e *manifests*. Para este trabalho o enunciado pede apenas Delta Lake.
