import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import Fullscreen, MeasureControl, MousePosition, LocateControl, Draw, MiniMap
import folium.plugins
from folium.features import FeatureGroup, CustomIcon
import tempfile
import zipfile
import os
from branca.element import Template, MacroElement
import branca
import html

#@st.cache_resource
@st.cache_data
def load_shapefile(zip_file):
    """
    Carrega um shapefile a partir de um arquivo ZIP.

    Args:
        zip_file: Arquivo ZIP contendo o shapefile (.shp e arquivos associados).

    Returns:
        gpd.GeoDataFrame: GeoDataFrame com os dados do shapefile, ou None em caso de erro.
    """
    message_placeholder = st.empty()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "shapefile.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_file.read())
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)
            shapefile_path = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")]
            if not shapefile_path:
                message_placeholder.error("O arquivo ZIP não contém um shapefile (.shp). Verifique o conteúdo do arquivo.")
                return None
            message_placeholder.info("Carregando shapefile...")
            gdf = gpd.read_file(shapefile_path[0])
            gdf[gdf.columns.difference(['geometry'])] = gdf[gdf.columns.difference(['geometry'])].astype(str)
            # Verificar e definir CRS
            if gdf.crs is None:
                message_placeholder.warning("Shapefile sem CRS definido. Definindo como EPSG:4326...")
                gdf.set_crs(epsg=4326, inplace=True)
            message_placeholder.empty()
            return gdf
    except zipfile.BadZipFile:
        message_placeholder.error("O arquivo ZIP está corrompido ou não é válido.")
        return None
    except gpd.io.file.fiona.errors.FionaValueError:
        message_placeholder.error("Erro ao ler o shapefile. Verifique se todos os arquivos (.shp, .shx, .dbf) estão presentes.")
        return None
    except Exception as e:
        message_placeholder.error(f"Erro inesperado ao processar o shapefile: {e}")
        return None

#@st.cache_resource
@st.cache_data
def load_data_file(file, sheet_name=None):
    """
    Carrega dados de arquivos Excel, CSV ou TXT.

    Args:
        file: Arquivo de entrada (xlsx, xls, csv, txt).
        sheet_name: Nome da planilha a ser lida (para arquivos Excel). Se None, lê a primeira planilha.

    Returns:
        pd.DataFrame: DataFrame com os dados, ou None em caso de erro.
    """
    message_placeholder = st.empty()
    if file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
        try:
            message_placeholder.info("Carregando arquivo Excel...")
            data = pd.read_excel(file, sheet_name=sheet_name, dtype=str)
            message_placeholder.empty()
            return data
        except ValueError as e:
            message_placeholder.error(f"Erro ao carregar a planilha '{sheet_name}': {e}")
            return None
        except Exception as e:
            message_placeholder.error(f"Erro inesperado ao carregar arquivo Excel: {e}")
            return None
    elif file.type == "text/csv":
        try:
            message_placeholder.info("Carregando arquivo CSV...")
            data = pd.read_csv(file, dtype=str, low_memory=False)
            message_placeholder.empty()
            return data
        except ValueError as e:
            message_placeholder.error(f"Erro ao carregar arquivo CSV: {e}")
            return None
    elif file.type == "text/plain":
        try:
            message_placeholder.info("Carregando arquivo TXT...")
            data = pd.read_csv(file, sep=None, engine='python', dtype=str, low_memory=False)
            message_placeholder.empty()
            return data
        except ValueError as e:
            message_placeholder.error(f"Erro ao carregar arquivo TXT: {e}")
            return None
    else:
        message_placeholder.error("Formato de arquivo não suportado. Use xlsx, xls, csv ou txt.")
        return None

#@st.cache_resource
def create_choropleth_map(_gdf, _gdf2, categorical_column, color_mapping, tooltip_field, prov_label_config=None, mun_label_config=None, prov_border_width=1.0, prov_border_color="#000000", mun_border_width=0.5, mun_border_color="#808080"):
    """
    Cria um mapa coroplético com base nos dados fornecidos, com opção de adicionar rótulos personalizados e configurar limites.

    Args:
        _gdf: GeoDataFrame dos municípios (não hashável).
        _gdf2: GeoDataFrame das províncias (não hashável).
        categorical_column: Coluna categórica para coloração.
        color_mapping: Dicionário mapeando categorias para cores.
        tooltip_field: Campo para exibir no tooltip.
        prov_label_config: Dicionário com configurações de rótulos para províncias (column, font_size, font_color, font_name, bold).
        mun_label_config: Dicionário com configurações de rótulos para municípios (column, font_size, font_color, font_name, bold).
        prov_border_width: Largura dos limites das províncias.
        prov_border_color: Cor dos limites das províncias.
        mun_border_width: Largura dos limites dos municípios.
        mun_border_color: Cor dos limites dos municípios.

    Returns:
        folium.Map: Mapa gerado, ou None em caso de erro.
    """
    message_placeholder = st.empty()
    try:
        # Verificar se os GeoDataFrames não estão vazios
        if _gdf.empty or _gdf2.empty:
            message_placeholder.error("Os shapefiles estão vazios. Verifique os dados carregados.")
            return None

        # Verificar se a coluna categórica existe
        if categorical_column not in _gdf.columns:
            message_placeholder.error(f"A coluna '{categorical_column}' não foi encontrada no shapefile.")
            return None

        # Verificar se a coluna de tooltip existe
        if tooltip_field not in _gdf.columns:
            message_placeholder.error(f"A coluna de tooltip '{tooltip_field}' não foi encontrada no shapefile.")
            return None

        # Validar configurações de rótulos
        if prov_label_config and prov_label_config.get("column") and prov_label_config["column"] not in _gdf2.columns:
            message_placeholder.error(f"A coluna de rótulos '{prov_label_config['column']}' não foi encontrada no shapefile de províncias.")
            return None
        if mun_label_config and mun_label_config.get("column") and mun_label_config["column"] not in _gdf.columns:
            message_placeholder.error(f"A coluna de rótulos '{mun_label_config['column']}' não foi encontrada no shapefile de municípios.")
            return None

        # Reprojetar para EPSG:4326, se necessário
        if _gdf.crs != "EPSG:4326":
            message_placeholder.info("Convertendo shapefile de municípios para EPSG:4326...")
            _gdf = _gdf.to_crs("EPSG:4326")
        if _gdf2.crs != "EPSG:4326":
            message_placeholder.info("Convertendo shapefile de províncias para EPSG:4326...")
            _gdf2 = _gdf2.to_crs("EPSG:4326")

        # Validar geometrias
        if not _gdf.geometry.is_valid.all():
            message_placeholder.warning("Algumas geometrias no shapefile de municípios são inválidas. Tentando corrigir...")
            _gdf.geometry = _gdf.geometry.buffer(0)
        if not _gdf2.geometry.is_valid.all():
            message_placeholder.warning("Algumas geometrias no shapefile de províncias são inválidas. Tentando corrigir...")
            _gdf2.geometry = _gdf2.geometry.buffer(0)

        # Verificar se há geometrias não nulas
        if _gdf.geometry.isna().any() or _gdf2.geometry.isna().any():
            message_placeholder.error("Alguns registros nos shapefiles não possuem geometrias válidas.")
            return None

        # Centralizar o mapa
        minx, miny, maxx, maxy = _gdf.total_bounds
        latitude_central = (miny + maxy) / 2
        longitude_central = (minx + maxx) / 2

        # Criar o mapa
        message_placeholder.info("Construindo mapa...")
        m = folium.Map(location=[latitude_central, longitude_central], zoom_start=6, tiles=None, control_scale=True)

        # Adicionar camada de províncias
        prov = folium.FeatureGroup("Províncias", show=True).add_to(m)
        folium.GeoJson(
            _gdf2,
            style_function=lambda feature: {
                'color': prov_border_color,
                'fillColor': 'none',
                'weight': prov_border_width,
                'fillOpacity': 1
            }
        ).add_to(prov)

        # Adicionar camada de municípios com cores
        distr = folium.FeatureGroup("Municípios", show=True).add_to(m)
        for _, row in _gdf.iterrows():
            if pd.notna(row[categorical_column]) and pd.notna(row.geometry):
                color = color_mapping.get(row[categorical_column], "gray")
                folium.GeoJson(
                    data=row.geometry,
                    style_function=lambda feature, color=color: {
                        "fillColor": color,
                        "color": mun_border_color,
                        "weight": mun_border_width,
                        "fillOpacity": 1
                    },
                    tooltip=f"{row[tooltip_field]}"
                ).add_to(distr)

        # Adicionar rótulos para províncias
        
        if prov_label_config and prov_label_config.get("column"):
            label_group_prov = folium.FeatureGroup("Rótulos Províncias", show=True).add_to(m)
            for _, row in _gdf2.iterrows():
                if pd.notna(row[prov_label_config["column"]]) and pd.notna(row.geometry):
                    centroid = row.geometry.centroid
                    font_weight = "bold" if prov_label_config.get("bold", False) else "normal"
        
                    # Escapa os caracteres especiais/acentos
                    texto_label = html.escape(str(row[prov_label_config["column"]]))
        
                    html_div = f'''
                        <div style="
                            font-size: {prov_label_config["font_size"]}px;
                            color: {prov_label_config["font_color"]};
                            font-family: {prov_label_config["font_name"]};
                            font-weight: {font_weight};
                            text-align: center;">
                            {texto_label}
                        </div>
                    '''
        
                    folium.Marker(
                        location=[centroid.y, centroid.x],
                        popup=folium.Popup(f"{row[prov_label_config['column']]}", parse_html=True),
                        icon=folium.DivIcon(html=html_div)
                    ).add_to(label_group_prov)


        # Adicionar rótulos para municípios
        
        # Adicionar rótulos para municípios
        if mun_label_config and mun_label_config.get("column"):
            label_group_mun = folium.FeatureGroup("Rótulos Municípios", show=True).add_to(m)
            for _, row in _gdf.iterrows():
                if pd.notna(row[mun_label_config["column"]]) and pd.notna(row.geometry):
                    centroid = row.geometry.centroid
                    font_weight = "bold" if mun_label_config.get("bold", False) else "normal"
                    
                    # Escapa corretamente acentos e símbolos HTML
                    texto_label = html.escape(str(row[mun_label_config["column"]]))
        
                    html_div = f'''
                        <div style="
                            font-size: {mun_label_config["font_size"]}px;
                            color: {mun_label_config["font_color"]};
                            font-family: {mun_label_config["font_name"]};
                            font-weight: {font_weight};
                            text-align: center;">
                            {texto_label}
                        </div>
                    '''
                    
                    folium.Marker(
                        location=[centroid.y, centroid.x],
                        popup=folium.Popup(f"{row[mun_label_config['column']]}", parse_html=True),
                        icon=folium.DivIcon(html=html_div)
                    ).add_to(label_group_mun)


        # Adicionar camadas de fundo
        # Adicionar camadas de fundo
        folium.TileLayer("OpenStreetMap", name="Ruas", attr="pav@ngola.com", show=False).add_to(m)
        folium.TileLayer("CartoDB positron", name="Fundo Cartográfico", attr="Tiles © CartoDB").add_to(m)
        white_tile = branca.utilities.image_to_url([[1, 1], [1, 1]])
        folium.TileLayer(tiles=white_tile, attr="@PAVANGOLA", name="Fundo Branco").add_to(m)
        folium.TileLayer(" ", attr="@PAVANGOLA", name="Fundo Cinza").add_to(m)

        
        #########
        folium.TileLayer(tiles = 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Maps',
            overlay = False,
            control = True
        ).add_to(m)
        folium.TileLayer(tiles = 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr = 'Google',
            name = 'Google Satellite',
            overlay = True,
            control = True
        ).add_to(m)
        ########################

        folium.TileLayer(tiles = 'https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
                attr = 'Google',
                name = 'Google Terrain',
                overlay = True,
                control = True
            ).add_to(m)
        folium.TileLayer(tiles = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
                attr = 'Google',
                name = 'Google Satellite',
                overlay = True,
                control = True
            ).add_to(m)
        folium.TileLayer(tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr = 'Esri',
                name = 'Esri Satellite',
                overlay = True,
                control = True
            ).add_to(m)
        ################################
 

        ##################

        # Adicionar controles
        folium.LayerControl(position="topleft", collapsed=True).add_to(m)
        Fullscreen(position="topleft").add_to(m)
        MousePosition(position="topright", separator=" | ").add_to(m)
        m.add_child(MeasureControl(position="topleft", secondary_length_unit='kilometers'))
        
        #folium.plugins.Geocoder(position="topleft").add_to(m)
        # Geocoder configurado
        folium.plugins.Geocoder(
            position="topleft",
            collapsed=True,        # toggle (caixa recolhida)
            add_marker=False,       # adiciona marcador no resultado
            placeholder="Digite um local...",
            popup_on_found=True,
            zoom=12
        ).add_to(m)

        # Adicionar o controle de desenho
        Draw(
            export=True,
            filename="my_data.geojson",
            show_geometry_on_click=False,
            position="topright",
            draw_options={
                "polyline": {"allowIntersection": False},  # Linhas não podem se cruzar
                "circle": {},  # Permitir desenhar círculos
                "rectangle": {},  # Permitir desenhar retângulos
                "polygon": {"allowIntersection": False},  # Polígonos sem interseção
                "marker": {},  # Permitir adicionar marcadores
            },
            edit_options={"poly": {"allowIntersection": False}}  # Editar sem interseções
        ).add_to(m)
        LocateControl(position="topright", strings={"title": "See you current location", "popup": "Your position"} ).add_to(m)
        minimap = MiniMap(toggle_display=True, position="bottomright")
        minimap.add_to(m)
        folium.LayerControl(position="topleft", collapsed=True).add_to(m)
        
        folium.LayerControl(position="topleft", collapsed=True).add_to(m)

        message_placeholder.empty()
        return m
    except KeyError as e:
        message_placeholder.error(f"Erro: Coluna não encontrada no shapefile: {e}")
        return None
    except Exception as e:
        message_placeholder.error(f"Erro ao criar o mapa: {e}")
        return None

def add_legend(m, color_mapping, title):
    """
    Adiciona uma legenda ao mapa com base no mapeamento de cores .

    Args:
        m: Mapa Folium.
        color_mapping: Dicionário mapeando categorias para cores.
        title: Título da legenda.
    """
    template = """
    {% macro html(this, kwargs) %}
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; background-color: white; padding: 10px; border: 2px solid black;">
        <h4>{{ this.title }}</h4>
        {% for category, color in this.color_mapping.items() %}
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="width: 20px; height: 20px; background-color: {{ color }}; margin-right: 10px;"></div>
            <span>{{ category }}</span>
        </div>
        {% endfor %}
    </div>
    {% endmacro %}
    """
    macro = MacroElement()
    macro._template = Template(template)
    macro.title = title
    macro.color_mapping = color_mapping
    m.get_root().add_child(macro)
