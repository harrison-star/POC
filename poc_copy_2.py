import streamlit as st
import pandas as pd
import sqlite3
import networkx as nx

# -----------------------------
# Configuração da página
# -----------------------------
st.set_page_config(layout="wide")

# -----------------------------
# ESTILO VISUAL (UX)
# -----------------------------
st.markdown("""
<style>
.main-title {
    font-size:32px;
    font-weight:700;
    color:#111;
}

.sub-title {
    font-size:18px;
    color:#555;
    margin-bottom:20px;
}

.kpi-card {
    background-color:#f5f7fa;
    padding:15px;
    border-radius:10px;
    text-align:center;
    box-shadow:0px 1px 4px rgba(0,0,0,0.1);
}

.alert-box {
    padding:20px;
    border-radius:10px;
    font-size:16px;
    font-weight:500;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Conectar SQLite
# -----------------------------
conn = sqlite3.connect("POC.db")

# -----------------------------
# Ler dados
# -----------------------------
df_status = pd.read_sql("SELECT * FROM malha_status", conn)
df_lineage = pd.read_sql("SELECT * FROM lineage", conn)

# Padronização
df_status["status"] = df_status["status"].str.upper()
df_status["tabela"] = df_status["tabela"].str.lower()
df_lineage["tabela_origem"] = df_lineage["tabela_origem"].str.lower()
df_lineage["tabela_destino"] = df_lineage["tabela_destino"].str.lower()

# -----------------------------
# Filtro por malha
# -----------------------------
malhas = df_status["nome_malha"].unique()
malha_sel = st.selectbox("📂 Selecione a malha", ["Todas"] + list(malhas))

if malha_sel != "Todas":
    df_status = df_status[df_status["nome_malha"] == malha_sel]

# -----------------------------
# Criar grafo
# -----------------------------
G = nx.from_pandas_edgelist(
    df_lineage,
    source="tabela_origem",
    target="tabela_destino",
    create_using=nx.DiGraph()
)

# -----------------------------
# Identificar atrasos
# -----------------------------
tabelas_atrasadas = df_status[df_status["status"] == "ATRASADO"]["tabela"].tolist()

# -----------------------------
# Propagar impacto
# -----------------------------
impacto_direto = set()
impacto_indireto = set()

for tabela in tabelas_atrasadas:
    if tabela in G:
        diretos = set(G.successors(tabela))
        impacto_direto.update(diretos)

        todos = set(nx.descendants(G, tabela))
        indiretos = todos - diretos
        impacto_indireto.update(indiretos)

total_impactados = impacto_direto.union(impacto_indireto)

# -----------------------------
# HEADER EXECUTIVO
# -----------------------------
st.markdown('<div class="main-title">📊 Data Lineage Impact Analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Monitoramento de impacto de dados baseado em dependências (lineage)</div>', unsafe_allow_html=True)

# -----------------------------
# KPIs (CARDS)
# -----------------------------
col1, col2, col3 = st.columns(3)

col1.markdown(f"""
<div class="kpi-card">
    <h2 style="color:#FF4B4B;">{len(tabelas_atrasadas)}</h2>
    <p>🔴 Tabelas Atrasadas</p>
</div>
""", unsafe_allow_html=True)

col2.markdown(f"""
<div class="kpi-card">
    <h2 style="color:#FF8C00;">{len(total_impactados)}</h2>
    <p>🟠 Tabelas Impactadas</p>
</div>
""", unsafe_allow_html=True)

col3.markdown(f"""
<div class="kpi-card">
    <h2 style="color:#2ECC71;">{len(G.nodes) - len(tabelas_atrasadas) - len(total_impactados)}</h2>
    <p>🟢 Tabelas Saudáveis</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# ALERTA EXECUTIVO
# -----------------------------
st.markdown("### 📢 Diagnóstico Executivo")

if len(tabelas_atrasadas) > 0:
    st.markdown(f"""
    <div class="alert-box" style="background-color:#ffe5e5; color:#900;">
    ⚠️ {len(tabelas_atrasadas)} falha(s) de ingestão impactando {len(total_impactados)} ativos downstream
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="alert-box" style="background-color:#e6f9ec; color:#0a662e;">
    ✅ Ambiente saudável, sem impacto relevante
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# BUSCA
# -----------------------------
st.subheader("🔎 Buscar tabela")
tabela_busca = st.text_input("Digite o nome da tabela")

if tabela_busca:
    tabela_busca = tabela_busca.lower()

    if tabela_busca in tabelas_atrasadas:
        st.error(f"🔴 '{tabela_busca}' está ATRASADA")

    elif tabela_busca in impacto_direto:
        st.warning(f"🟠 '{tabela_busca}' impactada diretamente")

    elif tabela_busca in impacto_indireto:
        st.warning(f"🟡 '{tabela_busca}' impactada indiretamente")

    elif tabela_busca in G.nodes:
        st.success(f"🟢 '{tabela_busca}' sem impacto upstream")

    else:
        st.info("Tabela não encontrada")

# -----------------------------
# GRAFO (GRAPHVIZ)
# -----------------------------
st.subheader("🧭 Fluxo de Impacto")

dot = "digraph G {\n"
dot += "rankdir=TB;\n"
dot += "node [shape=box style=filled fontname=Helvetica];\n"

def get_color(node):
    if node in tabelas_atrasadas:
        return "#FF4B4B"
    elif node in impacto_direto:
        return "#FF8C00"
    elif node in impacto_indireto:
        return "#FFD700"
    else:
        return "#2ECC71"

for node in G.nodes:
    label = node.replace("_", "\\n")
    color = get_color(node)
    dot += f'"{node}" [label="{label}" fillcolor="{color}"];\n'

for origem, destino in G.edges:
    dot += f'"{origem}" -> "{destino}";\n'

dot += "}"

st.graphviz_chart(dot)

# -----------------------------
# TABELA
# -----------------------------
st.subheader("📋 Detalhamento")

df_view = df_status.copy()

def classificar(t):
    if t in tabelas_atrasadas:
        return "ATRASADO"
    elif t in impacto_direto:
        return "IMPACTO DIRETO"
    elif t in impacto_indireto:
        return "IMPACTO INDIRETO"
    else:
        return "SEM IMPACTO"

df_view["impacto"] = df_view["tabela"].apply(classificar)

st.dataframe(df_view)