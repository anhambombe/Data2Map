import streamlit as st
import folium
from streamlit_folium import st_folium
from utils1a import load_shapefile, load_data_file, create_choropleth_map, add_legend
import io
import pandas as pd
import base64

# Configuração da página
st.set_page_config(
    page_title="DataOnMap",
    page_icon="dataonmapicon.icon",
    layout="wide",
    initial_sidebar_state="auto"
)

# Função para converter a imagem em base64
def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
        return f"data:image/ico;base64,{encoded}"
    except FileNotFoundError:
        st.error("Arquivo de ícone 'dataonmapicon.ico' não encontrado.")
        return ""

image_base64 = get_image_base64("dataonmapicon.ico")

# CSS para responsividade
st.markdown("""
    <style>
        .reportview-container .main .block-container {
            max-width: 100%;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .folium-map {
            width: 100% !important;
            height: 80vh !important;
            min-height: 500px !important;
        }
        h1, h4 {
            font-family: 'Segoe UI', 'Roboto', sans-serif;
        }
        .header-container {
            position: relative;
            text-align: center;
        }
        .logo-image {
            position: absolute;
            top: -10px;
            left: 63%;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 2px solid #1ABC9C;
            box-shadow: 0 0 8px #1ABC9C;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 8px #1ABC9C; }
            50% { box-shadow: 0 0 20px #1ABC9C; }
            100% { box-shadow: 0 0 8px #1ABC9C; }
        }
    </style>
    <div class='header-container'>
        <h1 style='color: #2C3E50; font-weight: bold; margin: 0;'>📍 <span style='color: #1ABC9C;'>DataOnMap</span></h1>
        <img class="logo-image" src="{image_base64}" alt="Logo redonda brilhandae">
    </div>
    <h4 style='text-align: center; color: #7F8C8D;'>Simplificando a elaboração de mapas coropléticos</h4>
""", unsafe_allow_html=True)

# Mapeamento de cores em português para valores em inglês
color_mapping_internal = {
    "Vermelho": "red",
    "Verde": "green",
    "Branco": "white",
    "Amarelo": "yellow",
    "Azul": "blue",
    "Ciano": "cyan",
    "Laranja": "orange",
    "Cinza": "gray",
    "Preto": "black"
}

def display_message(message_placeholder, message, message_type):
    """
    Exibe uma mensagem no Streamlit com base no tipo.

    Args:
        message_placeholder: Objeto Streamlit para exibir mensagens.
        message: Texto da mensagem.
        message_type: "info", "warning", ou "error".
    """
    if message_type == "info":
        message_placeholder.info(message)
    elif message_type == "warning":
        message_placeholder.warning(message)
    elif message_type == "error":
        message_placeholder.error(message)
    message_placeholder.empty()

def choropleth_tab():
    st.subheader(":rainbow[Mapa Coroplético]")
    message_placeholder = st.empty()

    # Inicializar estados no session_state
    if "map_buffer" not in st.session_state:
        st.session_state.map_buffer = None
    if "excel_key" not in st.session_state:
        st.session_state.excel_key = 0
    if "txt_separator" not in st.session_state:
        st.session_state.txt_separator = ","

    # Carregamento de arquivos na barra lateral
    with st.sidebar.expander("Leitura de dados"):
        shapefile_zip2 = st.file_uploader("Shapefile das Províncias (.zip)", type=["zip"], key="shapefile_prov")
        shapefile_zip = st.file_uploader("Shapefile dos Municípios (.zip)", type=["zip"], key="shapefile_mun")
        excel_file = st.file_uploader("Tabela de Dados", type=["xlsx", "xls", "txt", "csv"], key=f"excel_{st.session_state.excel_key}")

        sheet_name = None
        if excel_file and excel_file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
            try:
                xl = pd.ExcelFile(excel_file)
                sheet_names = xl.sheet_names
                if sheet_names:
                    sheet_name = st.selectbox("Selecione a planilha:", sheet_names, key="sheet_select")
                    st.session_state.excel_key += 1  # Resetar chave para forçar recarregamento
                else:
                    message_placeholder.error("O arquivo Excel não contém planilhas válidas.")
                    return
            except Exception as e:
                message_placeholder.error(f"Erro ao ler as planilhas do arquivo Excel: {e}")
                return
        elif excel_file and excel_file.type == "text/plain":
            st.session_state.txt_separator = st.text_input("Separador para arquivo TXT (ex.: ',', ';')", value=st.session_state.txt_separator, key="txt_separator")

    if shapefile_zip2 and shapefile_zip and excel_file:
        with st.spinner("Carregando arquivos..."):
            gdf2, msg, msg_type = load_shapefile(shapefile_zip2)
            display_message(message_placeholder, msg, msg_type)
            if gdf2 is None:
                return
            gdf, msg, msg_type = load_shapefile(shapefile_zip)
            display_message(message_placeholder, msg, msg_type)
            if gdf is None:
                return
            data, msg, msg_type = load_data_file(excel_file, sheet_name=sheet_name)
            display_message(message_placeholder, msg, msg_type)
            if data is None:
                return

        # Seleção de colunas para união e categorias
        with st.sidebar.expander("Selecione as colunas"):
            join_column_shapefile = st.selectbox("Coluna de união (Shapefile):", [None] + list(gdf.columns))
            join_column_data = st.selectbox("Coluna de união (Tabela):", [None] + list(data.columns))
            categorical_column = st.selectbox("Coluna de categorias:", [None] + list(data.columns))

        # Configuração dos limites
        with st.sidebar.expander("Configurar limites"):
            col1, col2 = st.columns([0.5, 0.5])
            with col1:
                prov_border_width = st.slider("Largura dos limites (Províncias):", min_value=0.5, max_value=5.0, value=1.0, step=0.1)
                prov_border_color = st.color_picker("Cor dos limites (Províncias):", "#000000")
            with col2:
                mun_border_width = st.slider("Largura dos limites (Municípios):", min_value=0.5, max_value=5.0, value=0.5, step=0.1)
                mun_border_color = st.color_picker("Cor dos limites (Municípios):", "#808080")

        # Configuração de rótulos
        with st.sidebar.expander("Rótulos de dados"):
            col1, col2 = st.columns([0.5, 0.5])
            with col1:
                exibir_labels_prov = st.checkbox("Exibir Labels das Províncias no Mapa", key="provi_checkbox")
            with col2:
                exibir_labels_distr = st.checkbox("Exibir Labels dos Municípios no Mapa", key="distritos_checkbox")

            prov_label_config = {}
            if exibir_labels_prov:
                prov_label_config["column"] = st.selectbox(
                    "Coluna para rótulos (Províncias):",
                    [None] + list(gdf2.columns),
                    key="prov_label_column"
                )
                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    prov_label_config["font_size"] = st.slider(
                        "Tamanho da fonte (Províncias):",
                        min_value=8, max_value=30, value=12, step=1,
                        key="prov_font_size"
                    )
                with col2:
                    prov_label_config["bold"] = st.checkbox("Texto em negrito (Províncias)", key="bold_prov")
                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    fontcolor_pt1 = st.radio(
                        "Selecione a cor da fonte (Províncias):",
                        options=list(color_mapping_internal.keys()),
                        key="prov_fontcolor_pt1"
                    )
                    prov_label_config["font_color"] = color_mapping_internal[fontcolor_pt1]
                with col2:
                    font_options = ["Arial", "Verdana", "Times New Roman", "Courier New", "Georgia", "Comic Sans MS", "Tahoma", "Trebuchet MS"]
                    prov_label_config["font_name"] = st.radio(
                        "Selecione o nome da fonte (Províncias):",
                        options=font_options,
                        key="prov_fontname1"
                    )

            mun_label_config = {}
            if exibir_labels_distr:
                mun_label_config["column"] = st.selectbox(
                    "Coluna para rótulos (Municípios):",
                    [None] + list(gdf.columns),
                    key="mun_label_column"
                )
                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    mun_label_config["font_size"] = st.slider(
                        "Tamanho da fonte (Municípios):",
                        min_value=8, max_value=30, value=12, step=1,
                        key="mun_font_size"
                    )
                with col2:
                    mun_label_config["bold"] = st.checkbox("Texto em negrito (Municípios)", key="bold_mun")
                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    fontcolor_pt = st.radio(
                        "Selecione a cor da fonte (Municípios):",
                        options=list(color_mapping_internal.keys()),
                        key="mun_fontcolor_pt"
                    )
                    mun_label_config["font_color"] = color_mapping_internal[fontcolor_pt]
                with col2:
                    font_options = ["Arial", "Verdana", "Times New Roman", "Courier New", "Georgia", "Comic Sans MS", "Tahoma", "Trebuchet MS"]
                    mun_label_config["font_name"] = st.radio(
                        "Selecione o nome da fonte (Municípios):",
                        options=font_options,
                        key="mun_fontname"
                    )

        # Seleção de cores para categorias
        color_mapping = {}
        with st.sidebar.expander("Selecione as cores"):
            if categorical_column and categorical_column in data.columns:
                unique_categories = data[categorical_column].dropna().unique()
                if len(unique_categories) > 0:
                    cols = st.columns(min(len(unique_categories), 3))
                    for i, category in enumerate(unique_categories):
                        with cols[i % len(cols)]:
                            color_mapping[category] = st.color_picker(f"Cor para {category}", "#FF0000", key=f"color_{category}")
                else:
                    message_placeholder.warning("A coluna de categorias selecionada não contém valores válidos.")
            else:
                message_placeholder.info("Selecione uma coluna de categorias para configurar as cores.")

        # Botão para gerar o mapa
        if st.sidebar.button("Gerar Mapa"):
            if not (shapefile_zip2 and shapefile_zip and excel_file):
                message_placeholder.error("Faça o upload de todos os arquivos necessários (shapefiles e tabela de dados).")
                return
            if not (join_column_shapefile and join_column_data):
                message_placeholder.error("Selecione as colunas de união para o shapefile e a tabela de dados.")
                return
            if not categorical_column:
                message_placeholder.error("Selecione a coluna de categorias.")
                return
            # Validar colunas de junção
            if join_column_shapefile and join_column_data:
                try:
                    if gdf[join_column_shapefile].dtype != data[join_column_data].dtype:
                        message_placeholder.error("As colunas de união têm tipos de dados diferentes. Converta para o mesmo tipo.")
                        return
                except KeyError:
                    message_placeholder.error("As colunas de união selecionadas não existem nos dados.")
                    return
            with st.spinner("Unindo dados..."):
                try:
                    gdf = gdf.merge(data, left_on=join_column_shapefile, right_on=join_column_data, how="left")
                    message_placeholder.success("Dados unidos com sucesso!")
                except ValueError as e:
                    message_placeholder.error(f"Erro ao unir os dados: {e}")
                    return
                except Exception as e:
                    message_placeholder.error(f"Erro inesperado ao unir os dados: {e}")
                    return
            if categorical_column not in gdf.columns:
                message_placeholder.error(f"A coluna de categorias '{categorical_column}' não foi encontrada no shapefile após a união.")
                return
            with st.spinner("Gerando mapa..."):
                m, msg, msg_type = create_choropleth_map(
                    gdf,
                    gdf2,
                    categorical_column,
                    color_mapping,
                    join_column_data,
                    prov_label_config=prov_label_config,
                    mun_label_config=mun_label_config,
                    prov_border_width=prov_border_width,
                    prov_border_color=prov_border_color,
                    mun_border_width=mun_border_width,
                    mun_border_color=mun_border_color
                )
                display_message(message_placeholder, msg, msg_type)
                if m is None:
                    return
                add_legend(m, color_mapping, "Categorias")
                st.session_state.map_buffer = io.BtyesIO()
                m.save(st.session_state.map_buffer, close_file=False)
                st.session_state.map_buffer = st.session_state.map_buffer.getvalue()
                with st.spinner("Renderizando mapa..."):
                    st_folium(m, width=900, height=600, returned_objects=[], key="folium_map")
                message_placeholder.success("Mapa gerado e renderizado com sucesso!")

        # Botão de download
        if st.session_state.map_buffer:
            st.download_button(
                label="Baixar Mapa como HTML",
                data=st.session_state.map_buffer,
                file_name="mapa.html",
                mime="text/html",
                key="download_map"
            )
            if st.checkbox("Salvar mapa"):
                nome = st.text_input("Nome do mapa:", "meu_mapa")
                if nome:
                    st.download_button(
                        label="Baixar Mapa como HTML",
                        data=st.session_state.map_buffer,
                        file_name=f"{nome}.html",
                        mime="text/html",
                        key="download_map_custom"
                    )
                else:
                    message_placeholder.warning("Insira um nome para o mapa.")

    else:
        message_placeholder.info("Faça o upload de todos os arquivos necessários (shapefiles e tabela de dados).")

# Executar a aba Map
choropleth_tab()

# Rodapé
st.sidebar.markdown("""
---
**DataOnMap** © 2024 | **Devs.com**  
**Versão:** 1.0.0
""")
