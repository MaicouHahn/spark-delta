# Apache Spark (PySpark)

## O que é

O **Apache Spark** é um framework de código aberto para **processamento distribuído** de grandes volumes de dados. Surgiu em 2009 no AMPLab da Universidade da Califórnia em Berkeley e tornou-se projeto de primeiro nível da Apache Software Foundation em 2014.

O Spark divide os dados em **partições** e processa cada uma em paralelo, nos núcleos de uma máquina ou nos nós de um cluster, mantendo os dados intermediários **em memória** sempre que possível. Neste trabalho ele roda em modo local (`local[*]`), usando todos os núcleos do computador, mas o mesmo código rodaria num cluster.

| Módulo | Uso |
|---|---|
| **Spark Core** | Execução distribuída, RDDs (*Resilient Distributed Datasets*) |
| **Spark SQL / DataFrames** | Consultas SQL e API de tabelas: **é o que usamos** |
| **Structured Streaming** | Processamento de fluxos contínuos |
| **MLlib** | Machine learning |
| **GraphX** | Processamento de grafos |

**PySpark** é a API Python do Spark: o código é escrito em Python e executado pelo motor do Spark (que roda na JVM, por isso o Java é pré-requisito).

## Conceitos usados no projeto

**SparkSession** — ponto de entrada. Toda configuração (pacotes, extensões, acesso ao S3) é feita ao criá-la.

**DataFrame** — tabela distribuída com schema. `spark.read...csv(...)` e `spark.read.format("delta").load(...)` retornam DataFrames.

**Avaliação preguiçosa (*lazy*)** — transformações (`where`, `select`, `withColumn`) só montam um plano; o processamento acontece em uma **ação** (`count`, `show`, `write`).

**Catálogo** — lista de tabelas que o Spark SQL conhece pelo nome. Neste projeto é o catálogo padrão **em memória**, que dura só enquanto a sessão está aberta (ver [Gerenciadas × não gerenciadas](tabelas-gerenciadas.md)).

## A SparkSession do projeto

Definida em `src/spark_delta/spark_session.py` e usada pelos notebooks 02, 03 e 04:

```python
SparkSession.builder
    .appName(app_name)
    .master("local[*]")
    # 1. Bibliotecas baixadas do Maven na primeira execução
    .config("spark.jars.packages",
            "io.delta:delta-spark_2.12:3.2.0,org.apache.hadoop:hadoop-aws:3.3.4")
    # 2. Liga o Delta Lake no Spark SQL
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    # 3. Onde ficam as tabelas GERENCIADAS
    .config("spark.sql.warehouse.dir", "s3a://warehouse/spark-warehouse")
    # 4. Acesso ao MinIO pelo conector S3A do Hadoop
    .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9020")
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin")
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
    .getOrCreate()
```

| Configuração | Por quê |
|---|---|
| `delta-spark_2.12:3.2.0` | Delta 3.2 é a versão compatível com Spark 3.5; `_2.12` é a versão do Scala com que o PySpark 3.5.3 foi compilado |
| `hadoop-aws:3.3.4` | Conector S3A; precisa ser da **mesma versão do Hadoop** embutido no PySpark 3.5.3 (3.3.4) |
| `path.style.access = true` | O MinIO local responde em `http://localhost:9020/<bucket>` em vez de `http://<bucket>.localhost` |
| `connection.ssl.enabled = false` | O MinIO local não usa HTTPS |

Os valores reais vêm do `.env` (lidos por `src/spark_delta/config.py`); o trecho acima mostra os valores padrão.

## Leitura e escrita

```python
# CSV do MinIO com schema explícito
df = (spark.read
      .option("header", "true")
      .option("mode", "FAILFAST")
      .schema("cd_cliente INT, nm_cliente STRING, cpf STRING, ...")
      .csv("s3a://landing-zone/cliente.csv"))

# Grava como Delta na bronze
df.write.format("delta").mode("overwrite").save("s3a://bronze/cliente")

# Lê de volta
spark.read.format("delta").load("s3a://bronze/cliente").show(5)
```

O prefixo `s3a://` diz ao Spark para usar o conector S3A, que traduz as leituras e escritas em chamadas à API S3 do MinIO.
