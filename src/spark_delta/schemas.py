"""Schemas explícitos usados na leitura dos CSVs da landing-zone.

Com ``inferSchema`` o Spark transformaria CPF/CNPJ em número e perderia os
zeros à esquerda. Por isso as tabelas conhecidas têm o schema declarado aqui;
qualquer tabela nova extraída do banco (sem schema aqui) cai no
``inferSchema`` e continua sendo convertida normalmente.
"""

SCHEMAS: dict[str, str] = {
    "categoria": "cd_categoria INT, nm_categoria STRING",
    "fornecedor": "cd_fornecedor INT, nm_fornecedor STRING, cnpj STRING, cidade STRING, uf STRING",
    "produto": (
        "cd_produto INT, nm_produto STRING, cd_categoria INT, cd_fornecedor INT, "
        "preco DECIMAL(12,2), dt_cadastro DATE"
    ),
    "estoque": "cd_produto INT, quantidade INT, estoque_minimo INT, dt_atualizacao TIMESTAMP",
    "cliente": (
        "cd_cliente INT, nm_cliente STRING, cpf STRING, email STRING, cidade STRING, "
        "uf STRING, dt_cadastro DATE"
    ),
    "venda": (
        "cd_venda INT, cd_cliente INT, dt_venda TIMESTAMP, forma_pagamento STRING, "
        "vl_total DECIMAL(14,2)"
    ),
    "item_venda": "cd_venda INT, cd_produto INT, quantidade INT, vl_unitario DECIMAL(12,2)",
}
