import html
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

st.set_page_config(
    page_title="HEIWA | Explorador de Argumentos",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- Design ---------------------------------------
st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
.hero {padding: 1.25rem 1.4rem; border: 1px solid #e4e7ec; border-radius: 16px;
       background: linear-gradient(120deg, #f7f9fc, #ffffff); margin-bottom: 1rem;}
.hero h1 {margin: 0; font-size: 2rem; color: #182230;}
.hero p {margin: .4rem 0 0 0; color: #475467;}
div[data-testid="stMetric"] {border: 1px solid #eaecf0; padding: 12px 14px; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>HEIWA — Explorador de Argumentos</h1>
  <p>Explore a estrutura de debates em redes interconectadas (Interconnected Nodes).</p>
</div>
""", unsafe_allow_html=True)

COLS = {
    "conversation": ["Conversation_id", "Conversation ID", "conversation_id"],
    "text": ["Texto", "text", "Texto original"],
    "claim": ["Trecho que contém a afirmação (claim) extraída", "Claim", "claim"],
    "data": ["Trecho que contém dados extraídos", "Dado", "Data"],
    "warrant": ["Trecho que contém justificativa (warrant) extraído", "Warrant", "Justificativa (Warrant)"],
    "rebuttal": ["Trecho que contém refutação (rebuttal) extraído", "Rebuttal", "Refutação"],
    "backing": ["Trecho que contém Apoio adicional (backing) extraído", "Backing", "Apoio adicional"],
    "qualifier": ["Trecho que contém qualificador extraído", "Qualifier", "Qualificador"],
    "id": ["ID", "Id", "id"],
    "claim_reason": ["Justificativa do trecho ser uma afirmação (claim)", "Justificativa da afirmação"],
    "data_reason": ["Justificativa do trecho conter dados", "Justificativa dos dados"],
    "warrant_reason": ["Justificativa do trecho conter justificativa (warrant)", "Justificativa do warrant"],
    "rebuttal_reason": ["Justificativa do trecho conter refutação (rebuttal)", "Justificativa do rebuttal"],
    "backing_reason": ["Justificativa do trecho conter Apoio adicional (backing)", "Justificativa do backing"],
    "qualifier_reason": ["Justificativa do trecho conter qualificador", "Justificativa do qualifier"],
}

ELEMENTS = [
    ("claim", "Afirmação (claim)", "#D92D20", "image", "https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/afir-removebg-preview.png"),
    ("data", "Dado", "#4F46E5", "image", "https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/dado-removebg-preview.png"),
    ("warrant", "Justificativa (warrant)", "#16A34A", "image", "https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/download.png"),
    ("rebuttal", "Refutação (rebuttal)", "#D97706", "image", "https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/refut-removebg-preview.png"),
    ("backing", "Apoio adicional (backing)", "#0891B2", "image", "https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/download%20(1).png"),
    ("qualifier", "Qualificador", "#9333EA", "image", "https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/Gemini_Generated_Image_9mm63g9mm63g9mm6-removebg-preview%20(1).png"),
]

# Paleta do mapa de calor: 0 (cinza) -> 5 (vermelho escuro)
HEATMAP_COLORS = ["#E5E7EB", "#FDE68A", "#F59E0B", "#EA580C", "#DC2626", "#7F1D1D"]


def find_col(df, key):
    for candidate in COLS.get(key, []):
        if candidate in df.columns:
            return candidate
    return None

def clean_value(value):
    if pd.isna(value): return ""
    val = str(value).strip()
    return "" if val.lower() in {"nan", "none", "null"} else val

def short(text, limit=42):
    text = clean_value(text).replace("\n", " ")
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"

def main():
    with st.sidebar:
        st.header("1. Carregar dados")
        uploaded = st.file_uploader("Envie a sua folha de cálculo", type=["xlsx", "xls", "csv"])
        heatmap_ativo = st.checkbox(
            "Ativar Mapa de Calor (Densidade)",
            value=False,
            help="Colore as afirmações com base na quantidade de elementos conectados (0 a 5).",
        )

    if uploaded is None:
        st.info("Comece por enviar um ficheiro Excel (.xlsx/.xls) ou CSV.")
        return

    try:
        if uploaded.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded, encoding="utf-8", on_bad_lines='skip')
        else:
            df = pd.read_excel(uploaded)
    except Exception as exc:
        st.error(f"Erro na leitura: {exc}")
        return

    conv_col = find_col(df, "conversation")
    claim_col = find_col(df, "claim")
    if not claim_col or not conv_col:
        st.error("Colunas essenciais (Conversation_id ou Claim) não encontradas.")
        return

    # 1 & 3. Otimização de Interface - Filtro focado em Conversation_id
    with st.sidebar:
        st.header("2. Explorar Conversas")
        df[conv_col] = df[conv_col].apply(clean_value)
        valid_convs = [c for c in df[conv_col].unique() if c]

        selected_convs = st.multiselect(
            "Selecione as Conversas (Conversation_id)",
            options=valid_convs,
            default=valid_convs[:2] if valid_convs else None,
            help="Filtra os clusters centrais de debate."
        )

        physics = st.checkbox("Física do grafo ativada", value=True)

    filtered = df[df[conv_col].isin(selected_convs)].copy() if selected_convs else df.iloc[0:0]

    if filtered.empty:
        st.warning("Nenhuma conversa selecionada ou dados insuficientes.")
        return

    # 2. Painel de Estatísticas Argumentativas
    st.markdown("### Estatísticas Argumentativas da Seleção")
    type_cols = {key: find_col(df, key) for key, *_ in ELEMENTS}

    metrics = {key: filtered[col].apply(lambda x: clean_value(x) != "").sum()
               for key, col in type_cols.items() if col}

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Total de Afirmações (Claims)", metrics.get("claim", 0))
    col_m2.metric("Total de Dados de Suporte", metrics.get("data", 0))
    col_m3.metric("Total de Refutações", metrics.get("rebuttal", 0))

    chart_data = pd.DataFrame({
        "Elementos": ["Dados", "Justificativas", "Refutações", "Apoios", "Qualificadores"],
        "Quantidade": [metrics.get(k, 0) for k in ["data", "warrant", "rebuttal", "backing", "qualifier"]]
    }).set_index("Elementos")

    with st.expander("Ver Proporção de Elementos Argumentativos", expanded=True):
        st.bar_chart(chart_data)

    # 1. Reestruturação do Grafo (PyVis) via Conversation_id
    st.markdown("### Rede Argumentativa Interativa")

    net = Network(height="650px", width="100%", bgcolor="#FFFFFF", font_color="#101828", directed=True)

    # 4. Física do Grafo: Ajuste de repulsão (gravitationalConstant mais negativo para afastar clusters)
    net.set_options("""
    {
      "nodes": {"font": {"size": 14, "face": "Arial"}},
      "edges": {"smooth": {"type": "continuous"}},
      "interaction": {"hover": true, "navigationButtons": true},
      "physics": {
        "enabled": true,
        "forceAtlas2Based": {
          "gravitationalConstant": -120,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08,
          "damping": 0.4
        },
        "solver": "forceAtlas2Based"
      }
    }
    """)
    if not physics:
        net.toggle_physics(False)

    text_col = find_col(df, "text")
    id_col = find_col(df, "id")
    reason_keys = {
        "claim": "claim_reason", "data": "data_reason", "warrant": "warrant_reason",
        "rebuttal": "rebuttal_reason", "backing": "backing_reason", "qualifier": "qualifier_reason"
    }

    # Agrupar por Conversation_id para formar os Clusters
    for conv_id, group in filtered.groupby(conv_col):
        # Nó central da conversa
        node_conv_id = f"conv::{conv_id}"
        net.add_node(
            node_conv_id,
            label=f"Conversa\n{short(conv_id, 15)}",
            shape="hexagon",
            color="#1F2937",
            size=45,
            title=f"<b>ID da Conversa:</b> {conv_id}",
        )

        for row_index, row in group.iterrows():
            values = {key: clean_value(row[col]) if col else "" for key, col in type_cols.items()}
            claim_value = values["claim"]
            if not claim_value:
                continue

            # Cálculo de densidade argumentativa para o Mapa de Calor
            elementos_presentes = sum(
                1 for k in ["data", "warrant", "rebuttal", "backing", "qualifier"] if values[k]
            )

            claim_id = f"claim::{row_index}"
            claim_reason = (
                clean_value(row[find_col(df, reason_keys["claim"])])
                if find_col(df, reason_keys["claim"]) else ""
            )
            orig_text = html.escape(clean_value(row[text_col])) if text_col else ""

            # Tooltip com pontuação de densidade
            claim_title = (
                f"<b>Afirmação:</b><br>{html.escape(claim_value)}"
                f"<br><br><b>Densidade:</b> {elementos_presentes}/5 elementos"
                f"<br><br><b>Texto Original:</b><br>{orig_text}"
            )
            if claim_reason:
                claim_title += f"<br><br><b>Justificativa da Anotação:</b><br>{html.escape(claim_reason)}"

            # Lógica de alternância do Mapa de Calor
            if heatmap_ativo:
                net.add_node(
                    claim_id,
                    label=short(claim_value, 20),
                    title=claim_title,
                    shape="dot",
                    color=HEATMAP_COLORS[elementos_presentes],
                    size=30 + (elementos_presentes * 5),
                )
            else:
                _, _, _, shape, img_url = ELEMENTS[0]
                net.add_node(
                    claim_id,
                    label=short(claim_value, 20),
                    title=claim_title,
                    shape=shape,
                    image=img_url,
                    size=30,
                )

            # Ligar Afirmação ao nó central da Conversa
            net.add_edge(claim_id, node_conv_id, color="#9CA3AF", length=150)

            for kind, label_name, color, shape, img_url in ELEMENTS[1:]:
                value = values[kind]
                if not value:
                    continue

                node_id = f"{kind}::{row_index}"
                reason_col = find_col(df, reason_keys[kind])
                reason = html.escape(clean_value(row[reason_col])) if reason_col else ""

                # Tooltip HTML
                title = f"<b>{label_name}:</b><br>{html.escape(value)}"
                if reason:
                    title += f"<br><br><b>Justificativa:</b><br>{reason}"

                # No modo heatmap, remove imagens dos nós periféricos para não poluir a análise térmica
                if heatmap_ativo:
                    net.add_node(
                        node_id,
                        label=short(value, 15),
                        title=title,
                        shape="dot",
                        color=color,
                        size=15,
                    )
                else:
                    net.add_node(
                        node_id,
                        label=short(value, 15),
                        title=title,
                        shape="image",
                        image=img_url,
                        size=20,
                    )

                # Ligar Elemento Periférico à sua respectiva Afirmação
                edge_color = "#D97706" if kind == "rebuttal" else "#D0D5DD"
                # Arestas mais espessas no modo heatmap para reforçar a leitura de densidade
                edge_width = 2 if heatmap_ativo else 1
                net.add_edge(
                    node_id,
                    claim_id,
                    title=label_name,
                    color=edge_color,
                    arrows="to",
                    length=80,
                    width=edge_width,
                )

    try:
        html_graph = net.generate_html()
        components.html(html_graph, height=670, scrolling=False)
    except Exception as exc:
        st.error(f"Erro na renderização: {exc}")


if __name__ == "__main__":
    main()