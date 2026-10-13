# 3. DML nas tabelas Delta

Notebook: `03_dml_delta.ipynb`.

O enunciado pede para **reproduzir as 3 operações DML do Trabalho 1** nas tabelas Delta da bronze. No Trabalho 1 a tabela `estoque_delta` recebeu três produtos, teve categoria, quantidade e preço preenchidos por `UPDATE` e perdeu o Teclado Mecânico num `DELETE`. Aqui o mesmo roteiro é aplicado às tabelas `produto` e `estoque` do LojaDB, agora no MinIO.

| Trabalho 1 (`estoque_delta`, local) | Trabalho 2 (`produto` / `estoque` na bronze) |
|---|---|
| `INSERT` de Notebook Dell, Mouse Logitech e Teclado Mecânico só com id e nome | `INSERT` dos mesmos 3 produtos (`cd_produto` 9001 a 9003), sem categoria, fornecedor e preço |
| `ALTER TABLE ... ADD COLUMN` + `UPDATE` de categoria, quantidade e preço | `UPDATE` com os mesmos valores (as colunas já existem no modelo relacional) |
| `DELETE` do Teclado Mecânico | `DELETE` do Teclado Mecânico |
| `DESCRIBE HISTORY` | `DESCRIBE HISTORY` + Time Travel |

## Registro das tabelas

Os dados já estão no MinIO. Para usar SQL é preciso registrar cada pasta Delta no catálogo do Spark:

```python
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {tabela}
    USING delta
    LOCATION 's3a://bronze/{tabela}'
""")
```

Por ter `LOCATION`, essas tabelas são **não gerenciadas** (ver a [próxima página](tabelas-gerenciadas.md)).

Antes das alterações, o notebook guarda a versão atual de `produto` e `estoque`, para comparar no final.

## INSERT

```sql
INSERT INTO produto
SELECT 9001, 'Notebook Dell',    NULL, NULL, NULL, current_date(), current_timestamp() UNION ALL
SELECT 9002, 'Mouse Logitech',   NULL, NULL, NULL, current_date(), current_timestamp() UNION ALL
SELECT 9003, 'Teclado Mecânico', NULL, NULL, NULL, current_date(), current_timestamp();

INSERT INTO estoque
SELECT 9001, 0, 5,  current_timestamp(), current_timestamp() UNION ALL
SELECT 9002, 0, 10, current_timestamp(), current_timestamp() UNION ALL
SELECT 9003, 0, 10, current_timestamp(), current_timestamp();
```

A última coluna é a `_dt_ingestao` da bronze. O Delta valida cada linha contra o schema da tabela (*schema enforcement*): uma coluna a mais ou um tipo incompatível faz o comando falhar inteiro, sem gravar nada pela metade.

| cd_produto | nm_produto | nm_categoria | preco | quantidade |
|---|---|---|---|---|
| 9001 | Notebook Dell | NULL | NULL | 0 |
| 9002 | Mouse Logitech | NULL | NULL | 0 |
| 9003 | Teclado Mecânico | NULL | NULL | 0 |

## UPDATE

Mesmos valores do Trabalho 1. Em `produto` via SQL:

```sql
UPDATE produto SET cd_categoria = 1, cd_fornecedor = 1, preco = 3500.00 WHERE cd_produto = 9001;
UPDATE produto SET cd_categoria = 2, cd_fornecedor = 2, preco = 120.00  WHERE cd_produto = 9002;
UPDATE produto SET cd_categoria = 2, cd_fornecedor = 2, preco = 250.00  WHERE cd_produto = 9003;
```

Em `estoque` via API Python:

```python
dt_estoque = DeltaTable.forPath(spark, "s3a://bronze/estoque")
for cd_produto, qtd in [(9001, 15), (9002, 50), (9003, 30)]:
    dt_estoque.update(
        condition=F.col("cd_produto") == cd_produto,
        set={"quantidade": F.lit(qtd), "dt_atualizacao": F.current_timestamp()},
    )
```

| cd_produto | nm_produto | nm_categoria | preco | quantidade |
|---|---|---|---|---|
| 9001 | Notebook Dell | Computadores | 3500.00 | 15 |
| 9002 | Mouse Logitech | Periféricos | 120.00 | 50 |
| 9003 | Teclado Mecânico | Periféricos | 250.00 | 30 |

## DELETE

O Teclado Mecânico saiu de linha. Primeiro sai do `estoque` (SQL), depois do `produto` (API), respeitando a dependência entre as tabelas:

```python
spark.sql("DELETE FROM estoque WHERE cd_produto = 9003")
DeltaTable.forPath(spark, "s3a://bronze/produto").delete("cd_produto = 9003")
```

| cd_produto | nm_produto | nm_categoria | preco | quantidade |
|---|---|---|---|---|
| 9001 | Notebook Dell | Computadores | 3500.00 | 15 |
| 9002 | Mouse Logitech | Periféricos | 120.00 | 50 |

## HISTORY

```python
spark.sql("DESCRIBE HISTORY produto").select("version", "timestamp", "operation").show()
```

Partindo de uma bronze recém-carregada, a tabela `produto` termina com 6 versões:

| version | operation | origem |
|---|---|---|
| 0 | WRITE | carga do CSV (notebook 02) |
| 1 | WRITE | `INSERT` dos 3 produtos |
| 2 | UPDATE | Notebook Dell |
| 3 | UPDATE | Mouse Logitech |
| 4 | UPDATE | Teclado Mecânico |
| 5 | DELETE | Teclado Mecânico |

A coluna `operationMetrics` mostra, para cada versão, quantas linhas foram inseridas, atualizadas ou removidas.

!!! tip "Rodando de novo"
    Para refazer a demonstração do zero, execute o notebook 02 antes do 03. O overwrite da bronze cria uma nova versão; o notebook 03 sempre parte da versão que encontrar, então a numeração muda, mas a sequência de operações é a mesma.

## Time Travel

O notebook lê cada versão de `produto` desde antes do `INSERT` e mostra os 3 produtos aparecendo, sendo preenchidos e o Teclado Mecânico sumindo:

```python
for v in range(versao_inicial, versao_atual + 1):
    (spark.read.format("delta").option("versionAsOf", v).load("s3a://bronze/produto")
        .where("cd_produto >= 9001").show())
```

Por fim compara a versão anterior ao DML com a atual com `subtract`, listando as linhas que só existem agora.
