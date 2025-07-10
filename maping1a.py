import streamlit as st
import folium
from streamlit_folium import st_folium
from utils1a import load_shapefile, load_data_file, create_choropleth_map, add_legend
import io
import pandas as pd
import time
import streamlit.components.v1 as components

import branca
from folium.plugins import Fullscreen, MeasureControl, MousePosition, Draw
from branca.element import Template, MacroElement

## Configuração da página
st.set_page_config(
    page_title="DataOnMap",
    page_icon="dataonmapicon.png",
    layout="wide",
    initial_sidebar_state="auto"
)
#####################
#import streamlit as st
import base64

# Função para converter a imagem em base64
def get_image_base64(path):
    with open(path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return f"data:image/jpg;base64,{encoded}"

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
            top: -10px;     /* Eleva a imagem */
            left: 63%;      /* Ajuste horizontal até ficar sobre o "p" */
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 2px solid #1ABC9C;
            box-shadow: 0 0 8px #1ABC9C;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{
                box-shadow: 0 0 8px #1ABC9C;
            }}
            50% {{
                box-shadow: 0 0 20px #1ABC9C;
            }}
            100% {{
                box-shadow: 0 0 8px #1ABC9C;
            }}
        }}
    </style>

    <div class='header-container'>
        <h1 style='color: #2C3E50; font-weight: bold; margin: 0;'>📍 <span style='color: #1ABC9C;'>DataOnMap</span></h1>
        <img class="logo-image" src="{image_base64}" alt="Logo redonda brilhante">
    </div>
    <h4 style='text-align: center; color: #7F8C8D;'>Simplificando a elaboração de mapas coropléticos</h4>
""", unsafe_allow_html=True)





#####################################################
with st.expander("Faça clique aqui para ver as instruções 👇"):
    st.markdown("""
    **Atenção:**  
    Para usar este aplicativo, precisa de dois arquivos compactados do tipo *.zip*:  
    - Um com o shapefile das províncias.  
    - Outro com o shapefile dos municípios.  
    
    **Também é necessário:**  
    Uma tabela de dados nos formatos **.xlsx, .xls, .txt ou .csv**, com os dados a mapear.  
    A coluna dos dados a mapear deve ser formatada de forma categórica, para criar intervalos/categorias.  
    
    ---
    
    ### Passos para elaborar mapas:
    1. Faça a leitura dos shapefiles das províncias, municípios e da tabela de dados que contém os dados a mapear.  
       - *NB*: O shapefile dos municípios e a tabela de dados devem ter uma coluna comum para junção.  
    
    2. Selecione as colunas comuns no shapefile e na tabela de dados.  
    
    3. Selecione a coluna de filtros e rótulos, e faça a seleção/filtragem das categorias que deseja mostrar.  
    
    4. Escolha as cores para cada categoria.  
    
    5. Marque a opção de mostrar rótulos (se necessário) e ajuste as configurações.  
    
    **NB**: O mapa permite escolher mostrar os limites das províncias/municípios e o tipo de fundo.
    ---
    ### Para fazer a leitura dos dados, procure por **Leitura de dados** no canto superior esquerdo da tela, bem abaixo do texto **Configurações**
    """)
##########################################################




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

# Função para a aba Map
def choropleth_tab():
    #st.subheader(":rainbow[Mapa Coroplético]")
    message_placeholder = st.empty()

    # Carregamento de arquivos na barra lateral
    with st.sidebar.expander("⚙ Leitura de dados "):
        shapefile_zip2 = st.file_uploader("Shapefile das Províncias (.zip)", type=["zip"])
        shapefile_zip = st.file_uploader("Shapefile dos Municípios (.zip)", type=["zip"])
        excel_file = st.file_uploader("Tabela de Dados", type=["xlsx", "xls", "txt", "csv"])

        # Seleção de planilha para arquivos Excel
        sheet_name = None
        if excel_file and excel_file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
            try:
                xl = pd.ExcelFile(excel_file)
                sheet_names = xl.sheet_names
                if sheet_names:
                    sheet_name = st.selectbox("Selecione a planilha:", sheet_names)
                else:
                    message_placeholder.error("O arquivo Excel não contém planilhas válidas.")
                    return
            except Exception as e:
                message_placeholder.error(f"Erro ao ler as planilhas do arquivo Excel: {e}")
                return

    # Verificar se todos os arquivos foram carregados
    if shapefile_zip2 and shapefile_zip and excel_file:
        message_placeholder.info("Carregando arquivos...")
        gdf2 = load_shapefile(shapefile_zip2)
        gdf = load_shapefile(shapefile_zip)
        data = load_data_file(excel_file, sheet_name=sheet_name)
        if isinstance(data, tuple):
            message_placeholder.error("Erro interno: A função de carregamento de dados retornou uma tupla em vez de um DataFrame. Verifique a função 'load_data_file'.")
            return

        message_placeholder.empty()

        if gdf is None or gdf2 is None or data is None:
            message_placeholder.error("Erro ao carregar os arquivos. Verifique se os shapefiles contêm arquivos .shp, .shx, .dbf e se a tabela de dados está no formato correto (xlsx, xls, csv ou txt).")
            return

        # Seleção de colunas para união e categorias
        with st.sidebar.expander(" 🔗 Selecione as colunas de União e dados"):
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
        with st.sidebar.expander("🏷 Rótulos de dados"):
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
        map_buffer = None  # Inicializar map_buffer localmente
        with st.sidebar.expander("🎨 Selecione as cores"):
            if categorical_column and categorical_column in data.columns:
                unique_categories = data[categorical_column].dropna().unique()
                if len(unique_categories) > 0:
                    cols = st.columns(min(len(unique_categories), 3))
                    for i, category in enumerate(unique_categories):
                        with cols[i % len(cols)]:
                            color_mapping[category] = st.color_picker(f"Cor para {category}", "#FF0000", key=f"color_{category}")
                else:
                    message_placeholder.warning("A coluna de categorias selecionada não contém valores válidos. Selecione uma coluna com dados.")
            else:
                message_placeholder.info("Selecione uma coluna de categorias para configurar as cores.")

        # Botão para gerar o mapa
        col1, col2=st.columns(2)
        with col1:
            if st.sidebar.button("Gerar Mapa"):
                st.progress(2, text="Validação das configurações obrigatórias...")
                #message_placeholder.success("Validação as configurações obrigatórias ✔")
                # Validar configurações obrigatórias
                if not (shapefile_zip2 and shapefile_zip and excel_file):
                    message_placeholder.error("Faça o upload de todos os arquivos necessários (shapefiles e tabela de dados).")
                    return
                if not (join_column_shapefile and join_column_data):
                    message_placeholder.error("Selecione as colunas de união para o shapefile e a tabela de dados.")
                    return
                if not join_column_shapefile or join_column_shapefile is None:
                    message_placeholder.error("Selecione a coluna do shapefile que tem valores para união.")
                    return
                    
                if not join_column_data or join_column_data is None:
                    message_placeholder.error("Selecione a coluna da tabela de dados que tem valores para união.")
                    return
                if not categorical_column:
                    message_placeholder.error("Selecione a coluna de categorias.")
                    return
    
                # Realizar a união dos dados
                #message_placeholder.info("União dados...")
                st.progress(10, text="União de dados.")
                #message_placeholder.success("União de dados ✔")
                try:
                    gdf = gdf.merge(data, left_on=join_column_shapefile, right_on=join_column_data, how="left")
                    time.sleep(5)
                    message_placeholder.success("Dados unidos com sucesso!")
                except ValueError as e:
                    message_placeholder.error(f"Erro ao unir os dados: {e}. Verifique se as colunas selecionadas contêm valores compatíveis (ex.: mesmo tipo de dado).")
                    return
                except Exception as e:
                    message_placeholder.error(f"Erro inesperado ao unir os dados: {e}")
                    return
    
                # Verificar se a coluna categórica existe no gdf após a união
                if categorical_column not in gdf.columns:
                    message_placeholder.error(f"A coluna de categorias '{categorical_column}' não foi encontrada no shapefile após a união.")
                    return
    
                # Criar o mapa
                #message_placeholder.info("Gerando mapa...")
                st.progress(50, text="Construção do mapa...")
                #message_placeholder.success("Dados unidos com sucesso!")
                
                m = create_choropleth_map(
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
                message_placeholder.empty()
    
                if m:
                    message_placeholder.success("Mapa gerado com sucesso!")
                    st.progress(60, text="Adição da legenda...")
                    add_legend(m, color_mapping, categorical_column)
                    # Gerar o buffer para download
                    map_buffer = io.BytesIO()
                    m.save(map_buffer, close_file=False)
                    map_buffer = map_buffer.getvalue()
                    message_placeholder.success("Legenda gerada com sucesso")
                    # Renderizar o mapa
                    #message_placeholder.info("Preparando o mapa para download...")
                    st.progress(80, text="Geração do buffer para download...")
                    try:
                        #st_folium(m, width=900, height=600, returned_objects=[], key="folium_map")
                        st.progress(100, text="Mapa finalizado. Pise no botão **Baixar** abaixo para fazer download do mapa")
                        
                        #map_html = m._repr_html_()
                        #st.components.v1.html(map_html, height=600, scrolling=True)
                        if map_buffer:
                            st.download_button(
                            label="📥Baixar Mapa como HTML",
                            data=map_buffer,
                            file_name="mapa.html",
                            mime="text/html",
                            key="download_mapq")
    
                        message_placeholder.success("Todos elementos foram adicionados ao mapa com sucesso!")

                        time.sleep(5)
                        message_placeholder.empty()
                        # Exportação do mapa com nome personalizado
                        #if map_buffer and st.checkbox("Salvar mapa"):
                            #nome = st.text_input("Nome do mapa:", "meu_mapa")
                            #if nome:
                                #st.download_button(
                                    #label="Baixar Mapa como HTML",
                                    #data=map_buffer,
                                    #file_name=f"{nome}.html",
                                    #mime="text/html",
                                    #key="download_map_custom"
                                #)
                            #else:
                                #message_placeholder.warning("Insira um nome para o mapa.")
                    except Exception as e:
                        message_placeholder.error(f"Erro ao renderizar o mapa: {e}")
                        return
                else:
                    message_placeholder.error("Falha ao criar o mapa. Verifique se os shapefiles contêm geometrias válidas e se a coluna de categorias contém dados.")
                    return


    
            # Opção para baixar o mapa como HTML
            #if map_buffer:
                #st.download_button(
                    #label="Baixar Mapa como HTML",
                    #data=map_buffer,
                    #file_name="mapa.html",
                    #mime="text/html",
                    #key="download_map"
                #)
    
            elif shapefile_zip2 and shapefile_zip and excel_file:
                #message_placeholder.info("Pise no botão **Fazer Mapa** para construir o mapa.") 
                message_placeholder.info("Faça o upload de todos os arquivos necessários (shapefiles e tabela de dados).")
            
            
            else:
                message_placeholder.info("Faça o upload de todos os arquivos necessários (shapefiles e tabela de dados).")
            
            
            

                # Executar a aba Map
                #m = folium.Map(location=[-11.2, 17.8], zoom_start=6, tiles=None)
                
                # Adicionar camadas de fundo
                #folium.TileLayer("OpenStreetMap", name="Ruas", attr="pav@ngola.com", show=False).add_to(m)
                #folium.TileLayer("CartoDB positron", name="Cartografia", attr="Tiles © CartoDB").add_to(m)
                #white_tile = branca.utilities.image_to_url([[1, 1], [1, 1]])
                #folium.TileLayer(tiles=white_tile, attr="@PAVANGOLA", name="Fundo Branco").add_to(m)
                #folium.TileLayer(" ", attr="@PAVANGOLA", name="Fundo Cinza").add_to(m)
                
                # Adicionar controles
                #folium.LayerControl(position="topleft", collapsed=True).add_to(m)
                #Fullscreen(position="topleft").add_to(m)
                #MousePosition(position="topright", separator=" | ").add_to(m)
                #m.add_child(MeasureControl(position="topleft", secondary_length_unit='kilometers'))
                #st_folium(m, width=1600, height=1300)


# Abas da interface
tab1, tab2 = st.tabs(["🗺", "🌍Mapa Coroplético"])

with tab1:
    # Mapa base interativo
    m = folium.Map(location=[-11.2, 17.8], zoom_start=6, tiles=None)

    # Camadas de fundo
    folium.TileLayer("OpenStreetMap", name="Ruas", attr="pav@ngola.com", show=False).add_to(m)
    folium.TileLayer("CartoDB positron", name="Cartografia", attr="Tiles © CartoDB").add_to(m)

    # Controles
    folium.LayerControl(position="topleft", collapsed=True).add_to(m)
    Fullscreen(position="topleft").add_to(m)
    MousePosition(position="topright", separator=" | ").add_to(m)
    m.add_child(MeasureControl(position="topleft", secondary_length_unit='kilometers'))

    # Adiciona a ferramenta de desenho
    draw = Draw(
        export=True,
        filename="meu_desenho.geojson",
        position="topleft",
        draw_options={
            'polyline': True,
            'polygon': True,
            'circle': False,
            'rectangle': True,
            'marker': True,
            'circlemarker': False
        },
        edit_options={'edit': True, 'remove': True}
    )
    draw.add_to(m)
    
    # Exibir o mapa no Streamlit
    map_data = st_folium(
        m,
        width=1200,
        height=800,
        returned_objects=["all_drawings"]  # ou "last_active_drawing"
    )
    
    # Mostrar os dados desenhados
    st.subheader("Dados desenhados (GeoJSON)")
    st.write(map_data.get("all_drawings"))

    # Exibe o mapa
    st_folium(m, width=1600, height=1300)

with tab2:
    # Aqui você chama a função que cria o mapa coroplético
    choropleth_tab()
#choropleth_tab()




st.sidebar.markdown("""
---
**SimpMap** | [**SCIDaR**](https://scidar.org) | © 2024
---
**Versão:** 1.0.0
""")
st.sidebar.subheader(":rainbow[Mapa Coroplético]")

#st.sidebar.link_button("SCIDaR", "https://scidar.org")
#st.sidebar.image("https://scidar.org/wp-content/uploads/2021/02/cropped-Big_no-bg-1-1.png", caption="", use_container_width=True)
