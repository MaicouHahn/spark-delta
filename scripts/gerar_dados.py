"""Gera o conjunto de dados sintético do LojaDB (loja de eletrônicos).

O cenário é a continuação do Trabalho 1 (Controle de Estoque): agora o estoque
vive em um banco relacional (SQL Server) com categorias, fornecedores,
produtos, clientes, vendas e itens de venda.

Uso (na raiz do projeto):

    uv run python scripts/gerar_dados.py

Os arquivos são gravados em ``data/`` (um CSV por tabela). A semente é fixa,
então o resultado é sempre o mesmo.
"""

from __future__ import annotations

import csv
import random
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

SEED = 42
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

N_FORNECEDORES = 25
N_CLIENTES = 1000
N_VENDAS = 5000

CATEGORIAS = [
    (1, "Computadores"),
    (2, "Periféricos"),
    (3, "Monitores"),
    (4, "Smartphones"),
    (5, "Áudio"),
    (6, "Armazenamento"),
    (7, "Redes"),
    (8, "Games"),
]

# categoria -> (marcas, modelos, faixa de preço)
CATALOGO = {
    1: (["Dell", "Lenovo", "Acer", "Asus", "HP", "Samsung"],
        ["Notebook 14 pol i5", "Notebook 15 pol i7", "Notebook gamer RTX", "Ultrabook 13 pol",
         "Desktop Core i5", "Desktop Ryzen 7", "All-in-One 24 pol", "Mini PC"],
        (1800, 9500)),
    2: (["Logitech", "Redragon", "HyperX", "Razer", "Microsoft"],
        ["Mouse sem fio", "Mouse gamer", "Teclado mecânico", "Teclado sem fio",
         "Webcam Full HD", "Headset USB", "Mousepad estendido"],
        (40, 900)),
    3: (["LG", "Samsung", "AOC", "Dell", "Philips"],
        ["Monitor 24 pol", "Monitor 27 pol", "Monitor 32 pol curvo", "Monitor ultrawide 29 pol"],
        (650, 3800)),
    4: (["Samsung", "Motorola", "Xiaomi", "Apple"],
        ["Smartphone 128GB", "Smartphone 256GB", "Smartphone 5G", "Smartphone Lite"],
        (900, 8500)),
    5: (["JBL", "Sony", "Edifier", "Philips"],
        ["Fone Bluetooth", "Caixa de som portátil", "Soundbar", "Fone intra-auricular"],
        (80, 2200)),
    6: (["Kingston", "Samsung", "WD", "Seagate", "SanDisk"],
        ["SSD 480GB", "SSD NVMe 1TB", "HD externo 2TB", "Pendrive 64GB", "Cartão microSD 128GB"],
        (35, 950)),
    7: (["TP-Link", "Intelbras", "Mercusys", "D-Link"],
        ["Roteador Wi-Fi 6", "Repetidor Wi-Fi", "Switch 8 portas", "Adaptador USB Wi-Fi"],
        (60, 750)),
    8: (["Sony", "Microsoft", "Nintendo", "8BitDo"],
        ["Controle sem fio", "Console", "Volante", "Cadeira gamer"],
        (180, 4800)),
}

NOMES = [
    "Ana", "Bruno", "Carla", "Daniel", "Eduarda", "Felipe", "Gabriela", "Henrique",
    "Isabela", "João", "Larissa", "Lucas", "Mariana", "Matheus", "Natália", "Otávio",
    "Paula", "Rafael", "Sabrina", "Thiago", "Vanessa", "Vinícius", "Beatriz", "Gustavo",
    "Juliana", "Leonardo", "Camila", "Rodrigo", "Fernanda", "Pedro",
]
SOBRENOMES = [
    "Silva", "Souza", "Oliveira", "Santos", "Pereira", "Costa", "Rodrigues", "Almeida",
    "Nascimento", "Lima", "Araújo", "Fernandes", "Carvalho", "Gomes", "Martins", "Rocha",
    "Ribeiro", "Alves", "Monteiro", "Mendes", "Hahn", "Machado", "Damazio", "Fortuna",
]
CIDADES = [
    ("Criciúma", "SC"), ("Florianópolis", "SC"), ("Joinville", "SC"), ("Tubarão", "SC"),
    ("Içara", "SC"), ("Araranguá", "SC"), ("Blumenau", "SC"), ("Porto Alegre", "RS"),
    ("Caxias do Sul", "RS"), ("Curitiba", "PR"), ("São Paulo", "SP"), ("Campinas", "SP"),
    ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"),
]
SUFIXOS_FORNECEDOR = ["Distribuidora", "Importadora", "Comércio de Eletrônicos", "Tecnologia", "Atacado"]
PREFIXOS_FORNECEDOR = [
    "Sul", "Atlântico", "Vale", "Serra", "Litoral", "Planalto", "Horizonte", "Capital",
    "Delta", "Prime", "Nova Era", "Conecta", "Digital", "Alpha", "Mega",
]


def money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def digits(rng: random.Random, n: int) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(n))


def random_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def write_csv(name: str, header: list[str], rows: list[tuple]) -> None:
    path = DATA_DIR / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"  {name:<12} {len(rows):>6} registros -> {path.relative_to(DATA_DIR.parent)}")


def main() -> None:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(exist_ok=True)

    # categoria
    write_csv("categoria", ["cd_categoria", "nm_categoria"], CATEGORIAS)

    # fornecedor
    fornecedores = []
    usados = set()
    for cd in range(1, N_FORNECEDORES + 1):
        while True:
            nome = f"{rng.choice(PREFIXOS_FORNECEDOR)} {rng.choice(SUFIXOS_FORNECEDOR)} Ltda"
            if nome not in usados:
                usados.add(nome)
                break
        cidade, uf = rng.choice(CIDADES)
        fornecedores.append((cd, nome, digits(rng, 14), cidade, uf))
    write_csv("fornecedor", ["cd_fornecedor", "nm_fornecedor", "cnpj", "cidade", "uf"], fornecedores)

    # produto + estoque
    produtos, estoque = [], []
    cd_produto = 1
    for cd_categoria, (marcas, modelos, (pmin, pmax)) in CATALOGO.items():
        for modelo in modelos:
            for marca in rng.sample(marcas, k=min(3, len(marcas))):
                preco = money(rng.uniform(pmin, pmax))
                dt_cadastro = random_date(rng, date(2022, 1, 1), date(2024, 6, 30))
                produtos.append((
                    cd_produto, f"{modelo} {marca}", cd_categoria,
                    rng.randint(1, N_FORNECEDORES), preco, dt_cadastro.isoformat(),
                ))
                estoque.append((
                    cd_produto, rng.randint(0, 120), rng.choice([5, 10, 15, 20]),
                    datetime(2026, 9, 30, rng.randint(8, 18), rng.randint(0, 59)).strftime("%Y-%m-%d %H:%M:%S"),
                ))
                cd_produto += 1
    write_csv("produto", ["cd_produto", "nm_produto", "cd_categoria", "cd_fornecedor", "preco", "dt_cadastro"], produtos)
    write_csv("estoque", ["cd_produto", "quantidade", "estoque_minimo", "dt_atualizacao"], estoque)

    # cliente
    clientes = []
    for cd in range(1, N_CLIENTES + 1):
        nome = f"{rng.choice(NOMES)} {rng.choice(SOBRENOMES)} {rng.choice(SOBRENOMES)}"
        login = nome.lower().split()[0] + "." + nome.lower().split()[-1]
        login = (login.replace("á", "a").replace("ã", "a").replace("é", "e").replace("í", "i")
                 .replace("ó", "o").replace("ú", "u").replace("ç", "c").replace("ô", "o"))
        cidade, uf = rng.choice(CIDADES)
        clientes.append((
            cd, nome, digits(rng, 11), f"{login}{cd}@email.com", cidade, uf,
            random_date(rng, date(2021, 1, 1), date(2025, 12, 31)).isoformat(),
        ))
    write_csv("cliente", ["cd_cliente", "nm_cliente", "cpf", "email", "cidade", "uf", "dt_cadastro"], clientes)

    # venda + item_venda
    precos = {p[0]: p[4] for p in produtos}
    vendas, itens = [], []
    for cd_venda in range(1, N_VENDAS + 1):
        dt_venda = datetime.combine(
            random_date(rng, date(2024, 1, 1), date(2026, 9, 30)), datetime.min.time()
        ) + timedelta(minutes=rng.randint(8 * 60, 21 * 60))
        total = Decimal("0.00")
        for cd_prod in rng.sample(list(precos), k=rng.choice([1, 1, 2, 2, 3, 4])):
            qtd = rng.choice([1, 1, 1, 2, 3])
            vl_unit = precos[cd_prod]
            itens.append((cd_venda, cd_prod, qtd, vl_unit))
            total += vl_unit * qtd
        vendas.append((
            cd_venda, rng.randint(1, N_CLIENTES), dt_venda.strftime("%Y-%m-%d %H:%M:%S"),
            rng.choice(["PIX", "CARTAO_CREDITO", "CARTAO_DEBITO", "BOLETO"]), total,
        ))
    write_csv("venda", ["cd_venda", "cd_cliente", "dt_venda", "forma_pagamento", "vl_total"], vendas)
    write_csv("item_venda", ["cd_venda", "cd_produto", "quantidade", "vl_unitario"], itens)


if __name__ == "__main__":
    print(f"Gerando dados em {DATA_DIR} (seed={SEED})")
    main()
    print("Concluído.")
