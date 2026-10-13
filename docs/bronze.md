# 2. Conversão: `landing-zone` → `bronze` (Delta)

Notebook: `02_csv_to_delta.ipynb`.

## O que acontece

Para cada CSV encontrado no bucket `landing-zone`:

1. o Spark lê o arquivo com o **schema da tabela**;
2. acrescenta a coluna técnica `_dt_ingestao` (momento da carga);
3. grava como **tabela Delta** em `s3a://bronze/<tabela>` com `mode("overwrite")`.

```python
leitor = (spark.read
          .option("header", "true")
          .option("dateFormat", "yyyy-MM-dd")
          .option("timestampFormat", "yyyy-MM-dd HH:mm:ss")
          .option("mode", "FAILFAST"))
if tabela in SCHEMAS:
    df = leitor.schema(SCHEMAS[tabela]).csv(origem)
else:
    df = leitor.option("inferSchema", "true").csv(origem)

df = df.withColumn("_dt_ingestao", F.current_timestamp())
df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(destino)
```

## Decisões

**Schema explícito em vez de `inferSchema`.**
Com `inferSchema`, o Spark leria `cpf` e `cnpj` como números e perderia os zeros à esquerda (`01234567890` → `1234567890`). Os schemas ficam em `src/spark_delta/schemas.py`:

```python
SCHEMAS = {
    "cliente": "cd_cliente INT, nm_cliente STRING, cpf STRING, email STRING, "
               "cidade STRING, uf STRING, dt_cadastro DATE",
    "produto": "cd_produto INT, nm_produto STRING, cd_categoria INT, cd_fornecedor INT, "
               "preco DECIMAL(12,2), dt_cadastro DATE",
    ...
}
```

Uma tabela que exista no banco mas não esteja nesse dicionário ainda é convertida, com `inferSchema`. Assim a etapa continua cobrindo **todas** as tabelas extraídas.

**`mode = FAILFAST`.** No modo padrão (`PERMISSIVE`), um valor que não pode ser convertido vira `NULL` silenciosamente. Com `FAILFAST` a leitura falha e o problema aparece na hora.

**`DECIMAL` para dinheiro.** `preco`, `vl_total` e `vl_unitario` são `DECIMAL`, não `DOUBLE`, para não haver erro de arredondamento em valores monetários.

**`overwrite`.** Rodar o notebook de novo recarrega a bronze a partir da landing. No Delta, o overwrite **não apaga o histórico**: ele vira uma nova versão da tabela.

## Resultado

```text
s3://bronze/
├── categoria/    ┐
├── cliente/      │  cada pasta:
├── estoque/      │    _delta_log/00000000000000000000.json
├── fornecedor/   │    part-0000*.snappy.parquet
├── item_venda/   │
├── produto/      │
└── venda/        ┘
```

O notebook valida cada tabela com `DeltaTable.isDeltaTable(...)` e a contagem de registros, mostra o schema da `cliente` (com `cpf` como `string`) e lista os arquivos físicos da tabela `produto` no MinIO.
