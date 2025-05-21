```python
import streamlit as st
import folium
from streamlit_folium import st_folium
from utils1a import load_shapefile, load_data_file, create_choropleth_map, add_legend, get_image_base64
import io
import pandas as pd
import time

# Configuração da página
st.set_page_config(
    page_title="DataOnMap",
    page_icon="dataonmapicon.png",
    layout="wide",
    initial_sidebar_state="auto"
)

# Carregar imagem base64
image_base64 = get_image_base64("dataonmapicon.ico")

# HTML + CSS com posicionamento acima da letra "p"
st.markdown(f"""
    <style>
        .reportview-container .main .block-container {{
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }}
        .folium-map {{
            width: 100% !important;
            height: 600px !important;
            min-height: 600px !important;
        }}
        h1, h4 {{
            font-family: 'Segoe UI', 'Roboto', sans-serif;
        }}
        .header-container {{
            position: relative;
            text-align: center;
        }}
        .logo-image {{
            position: absolute;
            top: -10px;
            left: 63%;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 2px solid #1ABC9C;
            box-shadow: 0 0 8px #1ABC9C;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ box-shadow: 0 0 8px #1ABC9C; }}
            50% {{ box-shadow: 0 0 20px #1ABC9C; }}
            100% {{ box-shadow: 0 0 8px #1ABC9C; }}
        }}
    </style>

    <div class='header-container'>
        <h1 style='color: #2C3E50; font-weight: bold; margin: 0;'>📍 <span style='color: #1ABC9C;'>DataOnMap</span></h1>
        <img class="logo-image" src="{image_base64}" alt="Logo redonda brilhante">
    </div>
    <h4 style='text-align: center; color: #7F8C8D;'>Simplificando a elaboração de mapas coropléticos</h4>
""", unsafe_allow_html=True)

# Mapeamento de cores em português para valores em inglês
color_mapping_internal = {
    "Vermelho 1": "red",
    "Verde 3": "green",
    "Branco": "white",
    "Amarelo": "yellow",
    "Azul": "blue",
    "Ciano": "cyan",
    "Laranja": "orange",
    "Cinza 3": "gray",
    "Preto": "black"
}

@st.cache_data
def merge_data(_gdf, _data, join_column_shapefile, join_column_data):
    """Cache the merge operation to avoid redundant processing."""
    return _gdf.merge(_data, left_on=join_column_shapefile, right_on=join_column_data, how="left")

def choropleth_tab():
    st.subheader(":rainbow[Mapa Coroplético]")
    message_placeholder = st.empty()

    # Inicializar session_state
    if 'gdf' not in st.session_state:
        st.session_state.gdf = None
    if 'gdf2' not in st.session_state:
        st.session_state.gdf2 = None
    if 'data' not in st.session_state:
        st.session_state.data = None
    if 'map_buffer' not in st.session_state:
        st.session_state.map_buffer = None
    if 'categorical_column' not in st.session_state:
        st.session_state.categorical_column = None

    # Carregar arquivos
    with st.sidebar:
        with st.expander("Leitura de dados"):
            shapefile_zip2 = st.file_uploader("Shapefile das Províncias (.zip)", type=["zip"], key="shapefile_zip2")
            shapefile_zip = st.file_uploader("Shapefile dos Municípios (.zip)", type=["zip"], key="shapefile_zip")
            excel_file = st.file_uploader("Tabela de Dados", type=["xlsx", "xls", "txt", "csv"], key="excel_file")

            sheet_name = None
            if excel_file and excel_file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
                try:
                    xl = pd.ExcelFile(excel_file)
                    sheet_names = xl.sheet_names
                    if sheet_names:
                        sheet_name = st.selectbox("Selecione a planilha:", sheet_names, key="sheet_name")
                    else:
                        message_placeholder.error("O arquivo Excel não contém planilhas válidas.")
                        return
                except Exception as e:
                    message_placeholder.error(f"Erro ao ler as planilhas do arquivo Excel: {e}")
                    return

    # Processar arquivos
    if shapefile_zip2 and shapefile_zip and excel_file:
        with st.spinner("Carregando arquivos..."):
            st.session_state.gdf2 = load_shapefile(shapefile_zip2)
            st.session_state.gdf = load_shapefile(shapefile_zip)
            st.session_state.data = load_data_file(excel_file, sheet_name=sheet_name)
        if st.session_state.gdf is None or st.session_state.gdf2 is None or st.session_state.data is None:
            message_placeholder.error("Erro ao carregar os arquivos. Verifique os shapefiles e a tabela de dados.")
            return
        else:
            message_placeholder.success("Arquivos carregados com sucesso!")

    # Formulário para configurações
    with st.sidebar.form(key="map_form"):
        files_loaded = st.session_state.gdf is not None and st.session_state.gdf2 is not None and st.session_state.data is not None

        with st.expander("Selecione as colunas", expanded=files_loaded):
            gdf_columns = list(st.session_state.gdf.columns) if files_loaded else []
            data_columns = list(st.session_state.data.columns) if files_loaded else []
            join_column_shapefile = st.selectbox("Coluna de união (Shapefile):", [None] + gdf_columns, key="join_column_shapefile", disabled=not files_loaded)
            join_column_data = st.selectbox("Coluna de união (Tabela):", [None] + data_columns, key="join_column_data", disabled=not files_loaded)
            st.session_state.categorical_column = st.selectbox("Coluna de categorias:", [None] + data_columns, key="categorical_column", disabled=not files_loaded)

        with st.expander("Configurar limites"):
            col1, col2 = st.columns([0.5, 0.5])
            with col1:
                prov_border_width = st.slider("Largura dos limites (Províncias):", min_value=0.5, max_value=5.0, value=1.0, step=0.1, key="prov_border_width")
                prov_border_color = st.color_picker("Cor dos limites (Províncias):", "#000000", key="prov_border_color")
            with col2:
                mun_border_width = st.slider("Largura dos limites (Municípios):", min_value=0.5, max_value=5.0, value=0.5, step=0.1, key="mun_border_width")
                mun_border_color = st.color_picker("Cor dos limites (Municípios):", "#808080", key="mun_border_color")

        with st.expander("Rótulos de dados"):
            col1, col2 = st.columns([0.5, 0.5])
            with col1:
                exibir_labels_prov = st.checkbox("Exibir Labels das Províncias no Mapa", key="provi_checkbox")
            with col2:
                exibir_labels_distr = st.checkbox("Exibir Labels dos Municípios no Mapa", key="distritos_checkbox")

            prov_label_config = {}
            if exibir_labels_prov:
                gdf2_columns = list(st.session_state.gdf2.columns) if files_loaded else []
                prov_label_config["column"] = st.selectbox(
                    "Coluna para rótulos (Províncias):", [None] + gdf2_columns, key="prov_label_column", disabled=not files_loaded)
                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    prov_label_config["font_size"] = st.slider(
                        "Tamanho da fonte (Províncias):", min_value=8, max_value=30, value=12, step=1, key="prov_font_size")
                with col2:
                    prov_label_config["bold"] = st.checkbox("Texto em negrito (Províncias)", key="bold_prov")
                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    fontcolor_pt1 = st.radio(
                        "Selecione a cor da fonte (Províncias):", options=list(color_mapping_internal.keys()), key="prov_fontcolor_pt1")
                    prov_label_config["font_color"] = color_mapping_internal[fontcolor_pt1]
                with col2:
                    font_options = ["Arial", "Verdana", "Times New Roman", "Courier New", "Georgia", "Comic Sans MS", "Tahoma", "Trebuchet MS"]
                    prov_label_config["font_name"] = st.radio(
                        "Selecione o nome da fonte (Províncias):", options=font_options, key="prov_fontname1")

            mun_label_config = {}
            if exibir_labels_distr:
                mun_label_config["column"] = st.selectbox(
                    "Coluna para rótulos (Municípios):", [None] + gdf_columns, key="mun_label_column", disabled=not files_loaded)
                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    mun_label_config["font_size"] = st.slider(
                        "Tamanho da fonte (Municípios):", min_value=8, max_value=30, value=12, step=1, key="mun_font_size")
                with col2:
                    mun_label_config["bold"] = st.checkbox("Texto em negrito (Municípios)", key="bold_mun")
                col1, col2 = st.columns([0.5, 0.5])
                with col1:
                    fontcolor_pt = st.radio(
                        "Selecione a cor da fonte (Municípios):", options=list(color_mapping_internal.keys()), key="mun_fontcolor_pt")
                    mun_label_config["font_color"] = color_mapping_internal[fontcolor_pt]
                with col2:
                    mun_label_config["font_name"] = st.radio(
                        "Selecione o nome da fonte (Municípios):", options=font_options, key="mun_fontname")

        with st.expander("Selecione as cores", expanded=st.session_state.categorical_column is not None):
            color_mapping = {}
            if files_loaded and st.session_state.categorical_column and st.session_state.categorical_column in st.session_state.data.columns:
                unique_categories = st.session_state.data[st.session_state.categorical_column].dropna().unique()
                if len(unique_categories) > 0:
                    cols = st.columns(min(len(unique_categories), 3))
                    for i, category in enumerate(unique_categories):
                        with cols[i % len(cols)]:
                            color_mapping[category] = st.color_picker(f"Cor para {category}", "#FF0000", key=f"color_{category}")
                else:
                    message_placeholder.warning("A coluna de categorias selecionada não contém valores válidos.")
            else:
                message_placeholder.info("Selecione uma coluna de categorias para configurar as cores.")

        # Debug: Mostrar estado dos inputs
        st.write(f"Arquivos carregados: {files_loaded}")
        st.write(f"Coluna categórica: {st.session_state.categorical_column}")

        submit_button = st.form_submit_button(
            "Gerar Mapa",
            disabled=not (files_loaded and join_column_shapefile and join_column_data and st.session_state.categorical_column)
        )

    # Gerar mapa quando o botão for clicado
    if submit_button:
        with st.spinner("Unindo dados..."):
            try:
                gdf_merged = merge_data(st.session_state.gdf, st.session_state.data, join_column_shapefile, join_column_data)
                message_placeholder.success("Dados unidos com sucesso!")
            except ValueError as e:
                message_placeholder.error(f"Erro ao unir os dados: {e}")
                return
            except Exception as e:
                message_placeholder.error(f"Erro inesperado ao unir os dados: {e}")
                return

        if st.session_state.categorical_column not in gdf_merged.columns:
            message_placeholder.error(f"A coluna de categorias '{st.session_state.categorical_column}' não foi encontrada no shapefile após a união.")
            return

        with st.spinner("Gerando mapa..."):
            m = create_choropleth_map(
                gdf_merged,
                st.session_state.gdf2,
                st.session_state.categorical_column,
                color_mapping,
                join_column_data,
                prov_label_config=prov_label_config,
                mun_label_config=mun_label_config,
                prov_border_width=prov_border_width,
                prov_border_color=prov_border_color,
                mun_border_width=mun_border_width,
                mun_border_color=mun_border_color
            )

        if m:
            add_legend(m, color_mapping, "Categorias")
            map_buffer = io.BytesIO()
            m.save(map_buffer, close_file=False)
            st.session_state.map_buffer = map_buffer.getvalue()
            message_placeholder.success("Mapa gerado com sucesso!")
            try:
                st_folium(m, width=900, height=600, returned_objects=[], key=f"folium_map_{time.time()}")
                message_placeholder.success("Mapa renderizado com sucesso!")
                time.sleep(2)
                message_placeholder.empty()
            except Exception as e:
                message_placeholder.error(f"Erro ao renderizar o mapa: {e}")
                return
        else:
            message_placeholder.error("Falha ao criar o mapa. Verifique os shapefiles e a coluna de categorias.")
            return

    # Opção para baixar o mapa como HTML
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

    # Limpar session_state se não houver arquivos carregados
    if not (shapefile_zip2 or shapefile_zip or excel_file):
        st.session_state.gdf = None
        st.session_state.gdf2 = None
        st.session_state.data = None
        st.session_state.map_buffer = None
        st.session_state.categorical_column = None
        message_placeholder.info("Faça o upload de todos os arquivos necessários.")

choropleth_tab()

# Rodapé
st.sidebar.markdown("""
---
**EasyMap** © 2024 | **Devs.com**  
**Versão:** 1.0.0
""")
```
