# Tabelas gerenciadas × não gerenciadas

Notebook: `04_tabelas_gerenciadas_vs_externas.ipynb` (item 4 do trabalho).

## Definição

| | **Gerenciada (interna)** | **Não gerenciada (externa)** |
|---|---|---|
| O Spark gerencia | dados **e** metadados | **apenas os metadados** |
| Como se cria | sem `LOCATION`: `df.write.saveAsTable("t")` ou `CREATE TABLE t (...) USING delta` | com `LOCATION`: `CREATE TABLE t USING delta LOCATION 's3a://...'` |
| Onde ficam os dados | em `spark.sql.warehouse.dir` | onde o usuário indicou |
| `DROP TABLE` | apaga metadados **e arquivos** | apaga só os metadados; **arquivos preservados** |

Regra prática: tabela criada **a partir de um DataFrame** com `saveAsTable` (ou por `CREATE TABLE` sem caminho) é gerenciada; tabela criada **sobre arquivos que já existem** é não gerenciada.

## A prova no notebook 04

O notebook cria duas tabelas com o mesmo conteúdo (a `categoria` da bronze) e aplica `DROP TABLE` nas duas:

```python
# GERENCIADA: a partir de DataFrame, sem LOCATION
df_categoria.write.format("delta").saveAsTable("categoria_gerenciada")

# EXTERNA: sobre a pasta Delta que já existe na bronze
spark.sql("CREATE TABLE categoria_externa USING delta LOCATION 's3a://bronze/categoria'")
```

O catálogo confirma o tipo de cada uma:

```python
for t in spark.catalog.listTables():
    print(t.name, t.tableType)
# categoria_externa     EXTERNAL
# categoria_gerenciada  MANAGED
```

E `DESCRIBE TABLE EXTENDED` mostra os locais: `s3a://warehouse/spark-warehouse/categoria_gerenciada` para a gerenciada e `s3a://bronze/categoria` para a externa.

Depois do `DROP TABLE` nas duas, o notebook lista os arquivos no MinIO com boto3:

| | Antes do DROP | Depois do DROP |
|---|---|---|
| `warehouse/spark-warehouse/categoria_gerenciada/` | Parquet + `_delta_log` | **0 arquivos** |
| `bronze/categoria/` | Parquet + `_delta_log` | **todos os arquivos continuam** |

Por último a externa é registrada de novo com o mesmo `CREATE TABLE ... LOCATION` e volta inteira, **inclusive com o histórico de versões**, porque o `_delta_log` estava preservado. A gerenciada não tem volta.

## Comparação entre os dois laboratórios

| | **Trabalho 1** ([Pyspark-Jupyter](https://github.com/MaicouHahn/Pyspark-Jupyter)) | **Trabalho 2** (este repositório) |
|---|---|---|
| Criação | `CREATE TABLE estoque_delta (...) USING delta` e `CREATE TABLE local.estoque_iceberg (...) USING iceberg`, **sem `LOCATION`** | `CREATE TABLE <t> USING delta LOCATION 's3a://bronze/<t>'` |
| Tipo | **Gerenciadas**: o Spark/catálogo escolheu o local (`spark-warehouse/` no disco) | **Não gerenciadas**: os dados foram gravados por caminho no MinIO antes de existir a tabela no catálogo |
| Origem dos dados | `INSERT` manual dentro do Spark | SQL Server → CSV → Delta |
| `DROP TABLE` | Delta: apaga também os dados | Remove só o registro; os dados continuam no MinIO |
| Armazenamento | disco local da máquina | object storage, acessível por outras ferramentas |

!!! note "Iceberg no Trabalho 1"
    As tabelas Iceberg do Trabalho 1 usavam um catálogo próprio (`local`, tipo `hadoop`) com warehouse em `spark-warehouse/iceberg`: o catálogo também decidia onde gravar. No Iceberg, a remoção explícita dos arquivos de dados é pedida com `DROP TABLE ... PURGE`.

## Quando usar cada uma

| Use **gerenciada** quando... | Use **não gerenciada** quando... |
|---|---|
| a tabela só existe para o Spark (resultado intermediário, tabela temporária de análise) | os dados são compartilhados com outras ferramentas ou processos |
| é desejável que `DROP TABLE` limpe tudo | os dados não podem ser perdidos por um `DROP` acidental (caso da camada bronze) |
| o ambiente tem um metastore que organiza o warehouse | o local dos dados segue uma convenção própria (buckets por camada) |

## Ponto para discussão: o catálogo em memória

Este projeto usa o catálogo padrão do Spark **em memória**, sem Hive Metastore. Os metadados de **qualquer** tabela, gerenciada ou não, somem quando a sessão termina; por isso os notebooks 03 e 04 registram as tabelas de novo.

- Para as **externas** isso não é problema: o `_delta_log` dentro do MinIO guarda schema, versões e arquivos, e um `CREATE TABLE ... LOCATION` em qualquer sessão recupera tudo.
- Os arquivos de uma **gerenciada** criada numa sessão que terminou sem `DROP` ficam "órfãos" no warehouse, sem catálogo apontando para eles. O notebook 04 limpa esse resto no início para poder ser executado várias vezes.

Em produção, um metastore persistente (Hive Metastore, Unity Catalog, AWS Glue) guarda os metadados entre sessões e resolve esse problema.
