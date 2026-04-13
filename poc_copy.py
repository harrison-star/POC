import streamlit as st
import pandas as pd
import sqlite3
import networkx as nx
from pyvis.network import Network
import os

# -----------------------------
# Configuração da página
# -----------------------------
st.set_page_config(layout="wide")

# -----------------------------
# Conectar SQLite
# -----------------------------
conn = sqlite3.connect("POC.db")

# -----------------------------
# Ler dados
# -----------------------------
df_status = pd.read_sql("SELECT * FROM malha_status", conn)
df_lineage = pd.read_sql("SELECT * FROM lineage", conn)

# Padronização (evita erro de case)
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
# Identificar tabelas atrasadas
# -----------------------------
tabelas_atrasadas = df_status[df_status["status"] == "ATRASADO"]["tabela"].tolist()

# -----------------------------
# Propagar impacto
# -----------------------------
impacto_direto = set()
impacto_indireto = set()

for tabela in tabelas_atrasadas:
    if tabela in G:
        # 1 nível (filhos diretos)
        diretos = set(G.successors(tabela))
        impacto_direto.update(diretos)

        # todos os descendentes
        todos = set(nx.descendants(G, tabela))

        # indiretos = todos - diretos
        indiretos = todos - diretos
        impacto_indireto.update(indiretos)

# -----------------------------
# Filtro visual (reduzir poluição)
# -----------------------------
mostrar_so_impacto = st.checkbox("Mostrar apenas impacto", value=True)

if mostrar_so_impacto:
    nodes_filtrados = set(tabelas_atrasadas) | impacto_direto | impacto_indireto
    G = G.subgraph(nodes_filtrados).copy()

# -----------------------------
# Filtro Nome da Tabela
# -----------------------------
st.subheader("🔎 Buscar tabela")

tabela_busca = st.text_input("Digite o nome da tabela")


if tabela_busca:

    tabela_busca = tabela_busca.lower()

    if tabela_busca in tabelas_atrasadas:
        st.error(f"🔴 A tabela '{tabela_busca}' está ATRASADA (origem do problema)")

    elif tabela_busca in impacto_direto:
        # descobrir quem impacta
        causas = [
            origem for origem, destino in G.edges
            if destino == tabela_busca and origem in tabelas_atrasadas
        ]

        st.warning(f"🟠 A tabela '{tabela_busca}' está com atraso devido a dependência direta: {causas}")

    elif tabela_busca in impacto_indireto:
        st.warning(f"🟡 A tabela '{tabela_busca}' está impactada indiretamente por atrasos upstream")

    elif tabela_busca in G.nodes:
        st.success(f"🟢 A tabela '{tabela_busca}' não possui impacto de upstream — possível problema local (arquitetura/processo)")

    else:
        st.info("Tabela não encontrada no lineage")

# -----------------------------
# UI - Título + KPIs
# -----------------------------
st.title("📊 Data Lineage Impact Analysis")

col1, col2, col3 = st.columns(3)

total_impactados = impacto_direto.union(impacto_indireto)

col1.metric("🔴 Tabelas atrasadas", len(tabelas_atrasadas))
col2.metric("🟠 Impactadas", len(total_impactados))
col3.metric("🟢 Saudáveis", len(G.nodes) - len(tabelas_atrasadas) - len(total_impactados))

# -----------------------------
# Alerta executivo
# -----------------------------
if len(tabelas_atrasadas) > 0:
    st.error(f"⚠️ {len(tabelas_atrasadas)} tabela(s) atrasada(s) impactando o ambiente")
else:
    st.success("✅ Nenhum atraso detectado")

# -----------------------------
# Legenda
# -----------------------------
st.markdown("""
### 🔎 Legenda
- 🔴 **Atrasado** → origem do problema  
- 🟠 **Impacto direto** → depende diretamente da tabela atrasada  
- 🟡 **Impacto indireto** → depende de outra tabela impactada  
- 🟢 **Sem impacto** → não afetado  
""")

# -----------------------------
# Visualização com PyVis (PRO)
# -----------------------------
net = Network(
    height="650px",
    width="100%",
    bgcolor="#111111",
    font_color="white",
    directed=True
)

net.barnes_hut()

for node in G.nodes:
    if node in tabelas_atrasadas:
        color = "#FF4B4B"
        size = 30
    elif node in impacto_direto:
        color = "#FF8C00"
        size = 25
    elif node in impacto_indireto:
        color = "#FFD700"
        size = 20
    else:
        color = "#2ECC71"
        size = 15

    #net.add_node(node, label=node, color=color, size=size)
    label = node.replace("_", "\n")  # quebra linha → fica mais limpo

    net.add_node(
        node,
        label=label,
        color=color,
        size=size,
        shape="box"
    )

for edge in G.edges:
    net.add_edge(edge[0], edge[1], color="#888", width=2)

net.set_options("""
{
  "layout": {
    "hierarchical": {
      "enabled": true,
      "direction": "UD",
      "levelSeparation": 150,
      "nodeSpacing": 200,
      "treeSpacing": 300,
      "blockShifting": true,
      "edgeMinimization": true,
      "parentCentralization": true
    }
  },
  "physics": {
    "enabled": false
  },
  "edges": {
    "smooth": false,
    "color": "#999999"
  },
  "nodes": {
    "shape": "box",
    "margin": 10,
    "font": {
      "size": 16
    }
  }
}
""")

net.save_graph("graph.html")

# -----------------------------
# Exibir grafo
# -----------------------------
st.iframe("graph.html", height=650)

# -----------------------------
# Tabela detalhada
# -----------------------------
st.subheader("📋 Detalhamento")

df_view = df_status.copy()
def classificar_impacto(tabela):
    if tabela in tabelas_atrasadas:
        return "ATRASADO"
    elif tabela in impacto_direto:
        return "IMPACTO DIRETO"
    elif tabela in impacto_indireto:
        return "IMPACTO INDIRETO"
    else:
        return "SEM IMPACTO"

df_view["impacto"] = df_view["tabela"].apply(classificar_impacto)

st.dataframe(df_view)