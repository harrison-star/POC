import sqlite3
import random

conn = sqlite3.connect("POC.db")
cursor = conn.cursor()

# -----------------------------
# Parâmetros
# -----------------------------
NOVAS_MALHAS = 15   # ~15 malhas → ~60+ tabelas no total (com pipeline)
PROB_ATRASO = 0.3   # 30% atraso (aumenta bastante o cenário)

dominios = ["COMERCIAL", "FINANCEIRO", "RH", "LOGISTICA"]

# -----------------------------
# Descobrir índice atual (evitar duplicidade)
# -----------------------------
cursor.execute("SELECT COUNT(*) FROM malha_status")
offset = cursor.fetchone()[0]

# -----------------------------
# Inserir novas malhas
# -----------------------------
for i in range(NOVAS_MALHAS):
    dominio = random.choice(dominios)

    idx = offset + i

    nome = f"{dominio}_AREA_{idx}"
    projeto = f"proj_{dominio.lower()}_{idx}"

    raw = f"raw_{dominio.lower()}_{idx}"
    stg = f"stg_{dominio.lower()}_{idx}"
    dim = f"dim_{dominio.lower()}_{idx}"
    fact = f"fact_{dominio.lower()}_{idx}"
    dash = f"dashboard_{dominio.lower()}_{idx}"

    status = "ATRASADO" if random.random() < PROB_ATRASO else "OK"

    # malha (RAW)
    cursor.execute("""
    INSERT INTO malha_status (nome_malha, projeto, tabela, status)
    VALUES (?, ?, ?, ?)
    """, (nome, projeto, raw, status))

    # pipeline
    cursor.executemany("""
    INSERT INTO lineage (tabela_origem, tabela_destino)
    VALUES (?, ?)
    """, [
        (raw, stg),
        (stg, dim),
        (stg, fact),
        (fact, dash),
    ])

# -----------------------------
# Cross dentro do domínio (leve)
# -----------------------------
cursor.execute("SELECT tabela FROM malha_status")
raws = [r[0] for r in cursor.fetchall()]

for _ in range(20):
    r1 = random.choice(raws)
    r2 = random.choice(raws)

    if r1 != r2:
        cursor.execute("""
        INSERT INTO lineage (tabela_origem, tabela_destino)
        VALUES (?, ?)
        """, (r1, r2.replace("raw", "fact")))

# -----------------------------
# Mais impacto no executivo
# -----------------------------
cursor.execute("SELECT tabela FROM malha_status WHERE status = 'ATRASADO'")
atrasadas = [r[0] for r in cursor.fetchall()]

for raw in atrasadas:
    fact = raw.replace("raw", "fact")

    cursor.execute("""
    INSERT INTO lineage (tabela_origem, tabela_destino)
    VALUES (?, ?)
    """, (fact, "dashboard_executivo"))

conn.commit()
conn.close()

print("✅ Incremento realizado com sucesso!")