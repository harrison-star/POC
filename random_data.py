import sqlite3
import random

conn = sqlite3.connect("POC.db")
cursor = conn.cursor()

# Limpar
cursor.execute("DELETE FROM malha_status")
cursor.execute("DELETE FROM lineage")

# -----------------------------
# Definição de domínios
# -----------------------------
dominios = {
    "COMERCIAL": 8,
    "FINANCEIRO": 6,
    "RH": 5,
    "LOGISTICA": 6
}

estrutura = {}

# -----------------------------
# Criar malhas por domínio
# -----------------------------
for dominio, qtd in dominios.items():
    estrutura[dominio] = []

    for i in range(qtd):
        nome = f"{dominio}_AREA_{i}"
        projeto = f"proj_{dominio.lower()}_{i}"

        raw = f"raw_{dominio.lower()}_{i}"
        stg = f"stg_{dominio.lower()}_{i}"
        dim = f"dim_{dominio.lower()}_{i}"
        fact = f"fact_{dominio.lower()}_{i}"
        dash = f"dashboard_{dominio.lower()}_{i}"

        status = "ATRASADO" if random.random() < 0.15 else "OK"

        # malha (apenas RAW)
        cursor.execute("""
        INSERT INTO malha_status (nome_malha, projeto, tabela, status)
        VALUES (?, ?, ?, ?)
        """, (nome, projeto, raw, status))

        # pipeline interno
        cursor.executemany("""
        INSERT INTO lineage (tabela_origem, tabela_destino)
        VALUES (?, ?)
        """, [
            (raw, stg),
            (stg, dim),
            (stg, fact),
            (fact, dash),
        ])

        estrutura[dominio].append({
            "raw": raw,
            "dim": dim,
            "fact": fact,
            "dash": dash
        })

# -----------------------------
# Cross APENAS dentro do domínio
# -----------------------------
for dominio, items in estrutura.items():
    for _ in range(len(items) * 2):
        origem = random.choice(items)["dim"]
        destino = random.choice(items)["fact"]

        if origem != destino:
            cursor.execute("""
            INSERT INTO lineage (tabela_origem, tabela_destino)
            VALUES (?, ?)
            """, (origem, destino))

# -----------------------------
# Cross ENTRE domínios específicos
# -----------------------------
# COMERCIAL ↔ FINANCEIRO (realista)
for _ in range(10):
    origem = random.choice(estrutura["COMERCIAL"])["fact"]
    destino = random.choice(estrutura["FINANCEIRO"])["fact"]

    cursor.execute("""
    INSERT INTO lineage (tabela_origem, tabela_destino)
    VALUES (?, ?)
    """, (origem, destino))

# -----------------------------
# Dashboard executivo (somente alguns domínios)
# -----------------------------
for dominio in ["COMERCIAL", "FINANCEIRO"]:
    for item in estrutura[dominio]:
        cursor.execute("""
        INSERT INTO lineage (tabela_origem, tabela_destino)
        VALUES (?, ?)
        """, (item["fact"], "dashboard_executivo"))

conn.commit()
conn.close()

print("✅ Base realista com domínios criada!")