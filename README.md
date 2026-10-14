# Trabalho 2: Apache Spark com MinIO e SQL Server

Pipeline de dados que **extrai todas as tabelas de um SQL Server**, grava como **CSV no MinIO** (bucket `landing-zone`), converte para **Delta Lake** (bucket `bronze`) e executa **INSERT, UPDATE e DELETE** nas tabelas Delta com Apache Spark.

Continuação do [Trabalho 1](https://github.com/MaicouHahn/Pyspark-Jupyter): o cenário de **Controle de Estoque** da loja de eletrônicos agora vem de um banco relacional (`LojaDB`), e as DMLs do Trabalho 1 são reproduzidas sobre a camada bronze.

📘 **Documentação (MkDocs):** [https://maicouhahn.github.io/spark-delta/](https://maicouhahn.github.io/spark-delta/)

> Este README é o **passo a passo para reproduzir o ambiente**. As explicações sobre o cenário, as tecnologias e cada etapa estão na documentação MkDocs.

## Integrantes

- Maicou Hahn Fortuna — [@MaicouHahn](https://github.com/MaicouHahn)
- Guilherme Victor Machado — [@gvm7b](https://github.com/gvm7b)
- Evandro Luiz Rodrigues Damazio

## Arquitetura

```
┌──────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│   SQL Server     │────▶│   MinIO (S3)     │────▶│   MinIO (S3)      │
│   2025 Dev       │     │   landing-zone/  │     │   bronze/         │
│                  │     │   (CSV)          │     │   (Delta Lake)    │
│   LojaDB         │     │                  │     │                   │
│   7 tabelas      │     │   1 CSV/tabela   │     │   INSERT/UPDATE   │
│                  │     │                  │     │   DELETE/HISTORY  │
└──────────────────┘     └──────────────────┘     └───────────────────┘
   Notebook 00              Notebook 01             Notebooks 02/03/04
   (Setup)                  (Extração)              (Delta + DML + tabelas)
```

## Versões utilizadas

| Componente | Versão |
|---|---|
| Ubuntu (WSL 2 no Windows 11) | 24.04 |
| Python | 3.11 (testado com 3.11.9 via pyenv) |
| UV | 0.4 ou superior |
| Java (OpenJDK) | 17 |
| PySpark | 3.5.3 |
| delta-spark | 3.2.0 (`io.delta:delta-spark_2.12:3.2.0`) |
| hadoop-aws | 3.3.4 (mesma versão do Hadoop do PySpark 3.5.3) |
| SQL Server | 2025 Developer (`mcr.microsoft.com/mssql/server:2025-latest`) |
| MinIO | `RELEASE.2025-02-03T21-03-04Z` (imagem do Quay ou compilada do código-fonte) |
| ODBC Driver for SQL Server | 18 |
| MkDocs / Material for MkDocs | 1.6 / 9.5 ou superior |

As bibliotecas Python e suas versões estão no [`pyproject.toml`](pyproject.toml).

---

## 1. Pré-requisitos (uma vez por máquina)

Todos os comandos abaixo são executados no terminal do **Ubuntu (WSL)**. Não use o PowerShell/Windows direto: o Spark precisa de várias configurações extras para funcionar nele.

### 1.1 Python 3.11 e UV

Se você já configurou o ambiente do Trabalho 1 (pyenv + Python 3.11.9 + UV via pipx), pode pular para o 1.2. Confira com:

```bash
python --version   # Python 3.11.x
uv --version
```

Se ainda não tem, siga a seção **"Instalação e Configuração do Ambiente"** do [README do Trabalho 1](https://github.com/MaicouHahn/Pyspark-Jupyter#readme) (pyenv → Python 3.11.9 → pipx → UV).

### 1.2 Java 17

O Spark roda na JVM.

```bash
sudo apt update
sudo apt install -y openjdk-17-jdk
java -version
```

Se `java -version` mostrar outra versão como padrão, selecione a 17:

```bash
sudo update-alternatives --config java
```

### 1.3 Docker

Instale o **Docker Desktop** no Windows e ative a integração com o WSL em *Settings → Resources → WSL Integration → Ubuntu*. Confira no Ubuntu:

```bash
docker --version
docker compose version
```

### 1.4 ODBC Driver 18 for SQL Server

Necessário para o Python (pyodbc) conversar com o SQL Server.

```bash
sudo apt install -y unixodbc-dev
curl https://packages.microsoft.com/keys/microsoft.asc | sudo tee /etc/apt/trusted.gpg.d/microsoft.asc
curl https://packages.microsoft.com/config/ubuntu/24.04/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql18
```

Valide a instalação:

```bash
odbcinst -q -d
```

Deve aparecer `[ODBC Driver 18 for SQL Server]`.

---

Caso de erro:
```bash
Warning: OpenPGP signature verification failed: https://packages.microsoft.com/ubuntu/24.04/prod noble InRelease: The following signatures couldn't be verified because the public key is not available: NO_PUBKEY EB3E94ADBE1229CF
Error: The repository 'https://packages.microsoft.com/ubuntu/24.04/prod noble InRelease' is not signed.
Notice: Updating from such a repository can't be done securely, and is therefore disabled by default.
Notice: See apt-secure(8) manpage for repository creation and user configuration details.
Error: Unable to locate package msodbcsql18
maicou@Maicou:~/projeto2/spark-delta$ odbcinst -q -d
Command 'odbcinst' not found, but can be installed with:
sudo apt install odbcinst
```

Rodar o bash
```bash
# 1. remove a configuração quebrada
sudo rm -f /etc/apt/sources.list.d/mssql-release.list /etc/apt/trusted.gpg.d/microsoft.asc

# 2. instala o repositório + chave (tenta o da sua versão; se não existir, usa o da 24.04)
VER=$(. /etc/os-release; echo $VERSION_ID)
curl -fsSL -o /tmp/packages-microsoft-prod.deb https://packages.microsoft.com/config/ubuntu/$VER/packages-microsoft-prod.deb \
  || curl -fsSL -o /tmp/packages-microsoft-prod.deb https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb
sudo dpkg -i /tmp/packages-microsoft-prod.deb

# 3. instala o driver
sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql18

# 4. valida
odbcinst -q -d
```

## 2. Configurar o projeto

### 2.1 Clonar o repositório

```bash
git clone https://github.com/MaicouHahn/spark-delta.git
cd spark-delta
```

### 2.2 Subir o SQL Server e o MinIO

```bash
docker compose up -d
docker compose ps
```

| Container | Imagem | Portas |
|---|---|---|
| `sqlserver-2025` | `mcr.microsoft.com/mssql/server:2025-latest` | `1433` |
| `minio` | `quay.io/minio/minio:RELEASE.2025-02-03T21-03-04Z` | `9020` (API S3), `9021` (console) |

| Serviço | Usuário | Senha |
|---|---|---|
| SQL Server | `sa` | `SqlServer@2025!` |
| MinIO | `minioadmin` | `minioadmin` |

Console do MinIO: http://localhost:9021

> **Erro `pull access denied for minio/minio`?** A MinIO removeu suas imagens do Docker Hub em setembro de 2026, por isso o projeto usa a cópia publicada no **Quay** (`quay.io/minio/minio`). Se o Quay também recusar o download (ele passou a exigir login para alguns usuários), use o **plano B**, que compila a mesma versão do MinIO a partir do código-fonte oficial no GitHub (leva de 5 a 10 minutos só na primeira vez):
>
> ```bash
> docker compose -f docker-compose.yml -f docker-compose.minio-build.yml up -d --build
> ```
>
> Daí em diante, use sempre esse mesmo comando (com os dois `-f`) para subir os containers. O resto do projeto não muda: portas, usuário e senha são os mesmos.

> O SQL Server leva uns 20 a 30 segundos para aceitar conexões depois de subir. Acompanhe com `docker logs -f sqlserver-2025` até aparecer `SQL Server is now ready for client connections`.

### 2.3 Variáveis de ambiente

```bash
cp .env.example .env
```

O `.env` já vem com os valores do `docker-compose.yml`; só altere se mudar senhas ou portas.

### 2.4 Ambiente Python (UV)

```bash
uv sync
source .venv/bin/activate
```

O `uv sync` cria o `.venv` com Python 3.11, instala todas as dependências do `pyproject.toml` (incluindo MkDocs) e instala o pacote do próprio projeto (`src/spark_delta`), que os notebooks importam.

Teste rápido:

```bash
python -c "import pyspark, delta, spark_delta; print('PySpark', pyspark.__version__)"
```

---

## 3. Executar os notebooks

Abra a pasta do projeto no **VS Code** conectado ao WSL (canto inferior esquerdo → *Connect to WSL*) ou rode `jupyter lab` no terminal com o `.venv` ativo.

> **Importante:** em cada notebook, clique em **Select Kernel** e escolha o Python do `.venv` do projeto (`.venv/bin/python`).

Execute **em ordem**:

| # | Notebook | O que faz |
|---|---|---|
| 0 | `notebook/00_setup_sqlserver.ipynb` | Cria o database `LojaDB` e carrega as 7 tabelas a partir de `data/*.csv` |
| 1 | `notebook/01_sqlserver_to_minio_csv.ipynb` | Extrai **todas** as tabelas do SQL Server → CSV no bucket `landing-zone` |
| 2 | `notebook/02_csv_to_delta.ipynb` | Lê os CSVs e grava como Delta Lake no bucket `bronze` |
| 3 | `notebook/03_dml_delta.ipynb` | INSERT, UPDATE e DELETE (os mesmos do Trabalho 1), HISTORY e Time Travel |
| 4 | `notebook/04_tabelas_gerenciadas_vs_externas.ipynb` | Demonstra a diferença entre tabelas gerenciadas e não gerenciadas |

> Na **primeira** execução do notebook 02, o Spark baixa do Maven os JARs do Delta e do `hadoop-aws` (alguns minutos, precisa de internet). Nas próximas eles já estão em cache em `~/.ivy2`.

Para refazer a demonstração de DML do zero, execute de novo o notebook 02 (recarrega a bronze) e depois o 03.

Depois de rodar, os buckets podem ser conferidos no console do MinIO (http://localhost:9021).

---

## 4. Documentação (MkDocs)

Visualizar localmente (http://127.0.0.1:8000):

```bash
uv run mkdocs serve
```

Publicar no GitHub Pages (cria/atualiza o branch `gh-pages`):

```bash
uv run mkdocs gh-deploy
```

Na primeira publicação, confira em *Settings → Pages* do repositório se a fonte é o branch `gh-pages`.

---

## 5. Estrutura do projeto

```
spark-delta/
├── data/                          # CSVs de origem do LojaDB (gerados por scripts/gerar_dados.py)
├── docs/                          # Páginas do MkDocs
├── notebook/
│   ├── 00_setup_sqlserver.ipynb
│   ├── 01_sqlserver_to_minio_csv.ipynb
│   ├── 02_csv_to_delta.ipynb
│   ├── 03_dml_delta.ipynb
│   └── 04_tabelas_gerenciadas_vs_externas.ipynb
├── scripts/
│   └── gerar_dados.py             # Gera o dataset sintético (seed fixa)
├── src/spark_delta/               # Código compartilhado pelos notebooks
│   ├── config.py                  #   lê o .env
│   ├── schemas.py                 #   schemas das tabelas para ler os CSVs
│   ├── spark_session.py           #   SparkSession com Delta + MinIO
│   ├── sqlserver.py               #   conexão pyodbc
│   └── storage.py                 #   cliente S3 (boto3) do MinIO
├── .env.example
├── .python-version
├── docker/minio/Dockerfile          # Plano B: compila o MinIO do código-fonte
├── docker-compose.yml
├── docker-compose.minio-build.yml   # Plano B: usa o Dockerfile acima
├── mkdocs.yml
├── pyproject.toml
└── README.md
```

## 6. Problemas comuns

| Sintoma | Causa provável / solução |
|---|---|
| `Can't open lib 'ODBC Driver 18 for SQL Server'` | Driver ODBC não instalado: refaça o passo 1.4 |
| `Login timeout expired` no notebook 00 | SQL Server ainda subindo: espere e rode de novo (`docker logs sqlserver-2025`) |
| `JAVA_HOME is not set` / `Java gateway process exited` | Java ausente ou versão errada: refaça o passo 1.2 |
| `ModuleNotFoundError: spark_delta` ou `pyspark` | Kernel errado: selecione o `.venv` do projeto e rode `uv sync` |
| `pull access denied for minio/minio` | Imagem removida do Docker Hub: use a versão atual do `docker-compose.yml` (Quay) ou o plano B do passo 2.2 |
| `unauthorized` ao baixar `quay.io/minio/minio` | Quay exigindo login: use o plano B do passo 2.2 |
| `Connection refused` em `localhost:9020` | MinIO parado: `docker compose up -d` (ou o comando do plano B) |
| `Path does not exist: s3a://landing-zone/...` | Notebook 01 não foi executado |
| Porta 1433, 9020 ou 9021 ocupada | Pare o serviço que usa a porta ou altere a porta no `docker-compose.yml` **e** no `.env` |

Para parar os containers: `docker compose down` (os dados ficam nos volumes). Para apagar tudo e recomeçar: `docker compose down -v`.

## Referências

- [Repositório modelo do professor](https://github.com/jlsilva01/spark-delta-minio-sqlserver)
- [Delta Lake - releases e compatibilidade](https://docs.delta.io/latest/releases.html)
- [Delta Spark - Maven](https://mvnrepository.com/artifact/io.delta/delta-spark)
- [MinIO - documentação](https://min.io/docs/minio/linux/index.html)
- [SQL Server 2025 em Docker](https://learn.microsoft.com/sql/linux/quickstart-install-connect-docker)
- [UV](https://docs.astral.sh/uv/)
