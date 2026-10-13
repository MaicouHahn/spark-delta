# MinIO

## O que é

O **MinIO** é um *object storage* de código aberto com API compatível com o **Amazon S3**. Ele guarda arquivos (objetos) dentro de **buckets** e é acessado por HTTP com a mesma API do S3. Por isso as mesmas ferramentas que funcionam com a AWS (boto3, conector S3A do Spark) funcionam com o MinIO rodando localmente no Docker.

Neste trabalho o MinIO faz o papel do **data lake**.

!!! warning "Imagem Docker do MinIO"
    O projeto da MinIO Community Edition foi arquivado em 2026 e a empresa removeu as imagens `minio/minio` do Docker Hub em setembro de 2026. Por isso o `docker-compose.yml` usa a mesma versão publicada no Quay (`quay.io/minio/minio:RELEASE.2025-02-03T21-03-04Z`), e o repositório traz um plano B que compila essa versão a partir do código-fonte (`docker/minio/Dockerfile`). Para um ambiente de produção hoje seria preciso avaliar alternativas S3 mantidas (AIStor, SeaweedFS, Garage); para este laboratório local a versão fixa atende.

| Conceito | No projeto |
|---|---|
| Bucket | `landing-zone`, `bronze`, `warehouse` |
| Objeto | Cada CSV, cada arquivo Parquet, cada JSON do `_delta_log` |
| Endpoint da API S3 | `http://localhost:9020` |
| Console web | `http://localhost:9021` (usuário e senha `minioadmin`) |

## Buckets do projeto

| Bucket | Criado por | Conteúdo |
|---|---|---|
| `landing-zone` | notebook 01 | `categoria.csv`, `cliente.csv`, ... (1 CSV por tabela) |
| `bronze` | notebook 02 | Uma pasta Delta por tabela (`produto/`, `estoque/`, ...) |
| `warehouse` | notebooks 02/03/04 | `spark-warehouse/`: dados das tabelas **gerenciadas** do Spark |

## Duas formas de acesso

=== "boto3 (Python)"

    Usado para criar buckets, gravar os CSVs e listar arquivos:

    ```python
    from spark_delta.storage import s3_client, ensure_bucket

    s3 = s3_client()
    ensure_bucket(s3, "landing-zone")
    s3.put_object(Bucket="landing-zone", Key="cliente.csv", Body=csv_bytes)
    ```

=== "S3A (Spark)"

    Usado pelo Spark para ler e gravar dados com o prefixo `s3a://`:

    ```python
    spark.read.csv("s3a://landing-zone/cliente.csv", header=True)
    df.write.format("delta").save("s3a://bronze/cliente")
    ```

## Por que object storage

- **Escalável e barato**: em produção a mesma arquitetura roda sobre S3, Azure Blob ou GCS, que armazenam volumes enormes a baixo custo.
- **Separa armazenamento de processamento**: os dados ficam no MinIO e qualquer motor (Spark, Trino, DuckDB...) pode ler as tabelas Delta.
- **Durável**: os dados não dependem da sessão do Spark nem do computador onde ele roda.
