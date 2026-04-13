import dash
from dash import dcc, html, Input, Output
import pandas as pd
import sqlite3
import networkx as nx
import plotly.graph_objects as go

# -----------------------------
# DATA
# -----------------------------
conn = sqlite3.connect("POC.db")

df_status = pd.read_sql("SELECT * FROM malha_status", conn)
df_lineage = pd.read_sql("SELECT * FROM lineage", conn)

df_status["status"] = df_status["status"].str.upper()
df_status["tabela"] = df_status["tabela"].str.lower()
df_lineage["tabela_origem"] = df_lineage["tabela_origem"].str.lower()
df_lineage["tabela_destino"] = df_lineage["tabela_destino"].str.lower()

# -----------------------------
# GRAPH
# -----------------------------
G = nx.from_pandas_edgelist(
    df_lineage,
    source="tabela_origem",
    target="tabela_destino",
    create_using=nx.DiGraph()
)

tabelas_atrasadas = df_status[df_status["status"] == "ATRASADO"]["tabela"].tolist()

impacto_direto = set()
impacto_indireto = set()

for t in tabelas_atrasadas:
    if t in G:
        diretos = set(G.successors(t))
        impacto_direto.update(diretos)

        todos = set(nx.descendants(G, t))
        impacto_indireto.update(todos - diretos)

total_impactados = impacto_direto.union(impacto_indireto)

# -----------------------------
# SANKEY
# -----------------------------
def gerar_sankey():
    nodes = list(G.nodes)
    idx = {n: i for i, n in enumerate(nodes)}

    colors = []
    for n in nodes:
        if n in tabelas_atrasadas:
            colors.append("red")
        elif n in impacto_direto:
            colors.append("orange")
        elif n in impacto_indireto:
            colors.append("gold")
        else:
            colors.append("green")

    return go.Figure(data=[go.Sankey(
        node=dict(label=nodes, color=colors),
        link=dict(
            source=[idx[s] for s, t in G.edges],
            target=[idx[t] for s, t in G.edges],
            value=[1]*len(G.edges)
        )
    )])

# -----------------------------
# APP
# -----------------------------
app = dash.Dash(__name__)

# -----------------------------
# LAYOUT
# -----------------------------
app.layout = html.Div([

    dcc.Store(id="page", data="dashboard"),

    # SIDEBAR
    html.Div([
        html.H2("📊 Lineage"),

        html.Button("Dashboard", id="btn_dash", n_clicks=0),
        html.Button("Incidentes", id="btn_inc", n_clicks=0),
        html.Button("Linhagem", id="btn_lin", n_clicks=0),
        html.Button("SLA", id="btn_sla", n_clicks=0),

    ], className="sidebar"),

    # CONTENT
    html.Div(id="content", className="content")

])

# -----------------------------
# ROUTER
# -----------------------------
@app.callback(
    Output("page", "data"),
    Input("btn_dash", "n_clicks"),
    Input("btn_inc", "n_clicks"),
    Input("btn_lin", "n_clicks"),
    Input("btn_sla", "n_clicks"),
)
def navegar(d, i, l, s):
    ctx = dash.callback_context

    if not ctx.triggered:
        return "dashboard"

    btn = ctx.triggered[0]["prop_id"].split(".")[0]

    return {
        "btn_dash": "dashboard",
        "btn_inc": "incidentes",
        "btn_lin": "linhagem",
        "btn_sla": "sla"
    }[btn]

# -----------------------------
# RENDER PAGINA
# -----------------------------
@app.callback(
    Output("content", "children"),
    Input("page", "data")
)
def render(page):

    # ---------------- DASHBOARD
    if page == "dashboard":
        return html.Div([

            html.H1("📊 Visão Geral"),

            html.Div([
                html.Div(f"Atrasadas: {len(tabelas_atrasadas)}", className="card"),
                html.Div(f"Impactadas: {len(total_impactados)}", className="card"),
                html.Div(f"Saudáveis: {len(G.nodes)}", className="card"),
            ], className="row"),

            html.Div(f"""
⚠️ {len(tabelas_atrasadas)} falhas impactando {len(total_impactados)} ativos downstream
""", className="alert")

        ])

    # ---------------- INCIDENTES
    elif page == "incidentes":
        return html.Div([

            html.H1("🚨 Incidentes"),

            html.Ul([
                html.Li(f"Tabela crítica: {t}") for t in tabelas_atrasadas
            ])

        ])

    # ---------------- LINHAGEM
    elif page == "linhagem":
        return html.Div([

            html.H1("🧭 Lineage"),

            dcc.Graph(figure=gerar_sankey())

        ])

    # ---------------- SLA
    elif page == "sla":
        return html.Div([

            html.H1("⏱ SLA"),

            html.P(f"{len(total_impactados)} ativos impactados podem violar SLA"),

            html.Progress(value=len(total_impactados), max=len(G.nodes))

        ])

# -----------------------------
# CSS
# -----------------------------
app.index_string = """
<!DOCTYPE html>
<html>
<head>
{%metas%}
{%css%}

<style>

body {
    margin: 0;
    font-family: Segoe UI;
    background-color: #0E1117;
    color: white;
}

.sidebar {
    position: fixed;
    width: 220px;
    height: 100vh;
    background: #111827;
    padding: 20px;
}

.sidebar button {
    width: 100%;
    margin-top: 10px;
    padding: 10px;
    border: none;
    background: #1F2937;
    color: white;
    cursor: pointer;
}

.content {
    margin-left: 240px;
    padding: 30px;
}

.row {
    display: flex;
    gap: 20px;
}

.card {
    background: #1F2937;
    padding: 20px;
    border-radius: 10px;
    flex: 1;
}

.alert {
    margin-top: 20px;
    padding: 20px;
    background: rgba(255,75,75,0.2);
    border-left: 5px solid red;
}

</style>

</head>
<body>
{%app_entry%}
<footer>
{%config%}
{%scripts%}
{%renderer%}
</footer>
</body>
</html>
"""

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)