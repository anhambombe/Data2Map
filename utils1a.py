import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import Fullscreen, MeasureControl, MousePosition
import tempfile
import zipfile
import os
from branca.element import Template, MacroElement
import branca

@st.cache_resource(hash_funcs={tempfile._TemporaryFileWrapper: lambda x: x.name})
def load_shapefile(zip_file):
    """
    Carrega um shapefile a partir de um arquivo ZIP.

    Args:
        zip_file: Arquivo ZIP contendo o shapefile (.shp, .shx, .dbf).

    Returns:
        tuple: (gpd.GeoDataFrame or None, status_message, message_type)
            - GeoDataFrame com os dados do shapefile, ou None se houver erro.
            - status_message: Mensagem descrevendo o resultado.
            - message_type: "info", "warning", ou "error".
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "shapefile.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_file.read())
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)
            shapefile_path = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")]
            if not shapefile_path:
                return None, "O arquivo ZIP não contém um shapefile (.shp).", "error"
            gdf = gpd.read_file(shapefile_path[0])
            gdf[gdf.columns.difference(['geometry'])] = gdf[gdf.columns.difference(['geometry'])].astype(str)
            if gdf.crs is None:
                gdf.set_crs(epsg=4326, inplace=True)
                return gdf, "Shapefile sem CRS definido. Usando EPSG:4326 como padrão.", "warning"
            if not gdf.geometry.is_valid.all():
                gdf.geometry = gdf.geometry.make_valid()
                return gdf, "Geometrias inválidas detectadas. Corrigidas automaticamente.", "warning"
            if gdf.geometry.isna().any():
                return None, "Alguns registros no shapefile não possuem geometrias válidas.", "error"
            return gdf, "Shapefile carregado com sucesso.", "info"
    except zipfile.BadZipFile:
        return None, "O arquivo ZIP está corrompido ou não é válido.", "error"
    except gpd.io.file.fiona.errors.FionaValueError:
        return None, "Erro ao ler o shapefile. Verifique se todos os arquivos (.shp, .shx, .dbf) estão presentes.", "error"
    except Exception as e:
        return None, f"Erro inesperado ao processar o shapefile: {e}", "error"

@st.cache_resource
def load_data_file(file, sheet_name=None):
    """
    Carrega dados de arquivos Excel, CSV ou TXT.

    Args:
        file: Arquivo de entrada (xlsx, xls, csv, txt).
        sheet_name: Nome da planilha a ser lida (para arquivos Excel). Se None, lê a primeira planilha.

    Returns:
        tuple: (pd.DataFrame or None, status_message, message_type)
            - DataFrame com os dados, ou None em caso de erro.
            - status_message: Mensagem descrevendo o resultado.
            - message_type: "info", "warning", ou "error".
    """
    if file.type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
        try:
            data = pd.read_excel(file, sheet_name=sheet_name, dtype=str)
            if data.empty:
                return None, "O arquivo Excel está vazio.", "error"
            return data, "Arquivo Excel carregado com sucesso.", "info"
        except ValueError as e:
            return None, f"Erro ao carregar a planilha '{sheet_name}': {e}", "error"
        except Exception as e:
            return None, f"Erro inesperado ao carregar arquivo Excel: {e}", "error"
    elif file.type == "text/csv":
        try:
            data = pd.read_csv(file, dtype=str)
            if data.empty:
                return None, "O arquivo CSV está vazio.", "error"
            return data, "Arquivo CSV carregado com sucesso.", "info"
        except ValueError as e:
            return None, f"Erro ao carregar arquivo CSV: {e}", "error"
    elif file.type == "text/plain":
        try:
            separator = st.session_state.get("txt_separator", ",")
            data = pd.read_csv(file, sep=separator, engine='python', dtype=str)
            if data.empty:
                return None, "O arquivo TXT está vazio.", "error"
            return data, "Arquivo TXT carregado com sucesso.", "info"
        except ValueError as e:
            return None, f"Erro ao carregar arquivo TXT: {e}", "error"
    else:
        return None, "Formato de arquivo não suportado. Use xlsx, xls, csv ou txt.", "error"

def create_choropleth_map(_gdf, _gdf2, categorical_column, color_mapping, tooltip_field, prov_label_config=None, mun_label_config=None, prov_border_width=1.0, prov_border_color="#000000", mun_border_width=0.5, mun_border_color="#808080"):
    """
    Cria um mapa coroplético com base nos dados fornecidos, com opção de adicionar rótulos personalizados e configurar limites.

    Args:
        _gdf: GeoDataFrame dos municípios.
        _gdf2: GeoDataFrame das províncias.
        categorical_column: Coluna categórica para coloração.
        color_mapping: Dicionário mapeando categorias para cores.
        tooltip_field: Campo para exibir no tooltip.
        prov_label_config: Configurações de rótulos para províncias (column, font_size, font_color, font_name, bold).
        mun_label_config: Configurações de rótulos para municípios (column, font_size, font_color, font_name, bold).
        prov_border_width: Largura dos limites das províncias.
        prov_border_color: Cor dos limites das províncias.
        mun_border_width: Largura dos limites dos municípios.
        mun_border_color: Cor dos limites dos municípios.

    Returns:
        tuple: (folium.Map or None, status_message, message_type)
            - Mapa gerado, ou None em caso de erro.
            - status_message: Mensagem descrevendo o resultado.
            - message_type: "info", "warning", ou "error".
    """
    try:
        if _gdf.empty or _gdf2.empty:
            return None, "Os shapefiles estão vazios. Verifique os dados carregados.", "error"
        if categorical_column not in _gdf.columns:
            return None, f"A coluna '{categorical_column}' não foi encontrada no shapefile.", "error"
        if tooltip_field not in _gdf.columns:
            return None, f"A coluna de tooltip '{tooltip_field}' não foi encontrada no shapefile.", "error"
        if prov_label_config and prov_label_config.get("column") and prov_label_config["column"] not in _gdf2.columns:
            return None, f"A coluna de rótulos '{prov_label_config['column']}' não foi encontrada no shapefile de províncias.", "error"
        if mun_label_config and mun_label_config.get("column") and mun_label_config["column"] not in _gdf.columns:
            return None, f"A coluna de rótulos '{mun_label_config['column']}' não foi encontrada no shapefile de municípios.", "error"
        warnings = []
        if _gdf.crs != "EPSG:4326":
            _gdf = _gdf.to_crs("EPSG:4326")
            warnings.append("Convertendo shapefile de municípios para EPSG:4326.")
        if _gdf2.crs != "EPSG:4326":
            _gdf2 = _gdf2.to_crs("EPSG:4326")
            warnings.append("Convertendo shapefile de províncias para EPSG:4326.")
        if not _gdf.geometry.is_valid.all():
            _gdf.geometry = _gdf.geometry.make_valid()
            warnings.append("Geometrias inválidas no shapefile de municípios. Corrigidas automaticamente.")
        if not _gdf2.geometry.is_valid.all():
            _gdf2.geometry = _gdf2.geometry.make_valid()
            warnings.append("Geometrias inválidas no shapefile de províncias. Corrigidas automaticamente.")
        if _gdf.geometry.isna().any() or _gdf2.geometry.isna().any():
            return None, "Alguns registros nos shapefiles não possuem geometrias válidas.", "error"
        minx, miny, maxx, maxy = _gdf.total_bounds
        latitude_central = (miny + maxy) / 2
        longitude_central = (minx + maxx) / 2
        m = folium.Map(location=[latitude_central, longitude_central], zoom_start=6, tiles=None)
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
        if prov_label_config and prov_label_config.get("column"):
            label_group_prov = folium.FeatureGroup("Rótulos Províncias", show=True).add_to(m)
            for _, row in _gdf2.iterrows():
                if pd.notna(row[prov_label_config["column"]]) and pd.notna(row.geometry):
                    centroid = row.geometry.centroid
                    font_weight = "bold" if prov_label_config.get("bold", False) else "normal"
                    html = f'<div style="font-size: {prov_label_config["font_size"]}px; color: {prov_label_config["font_color"]}; font-family: {prov_label_config["font_name"]}; font-weight: {font_weight}; text-align: center;">{row[prov_label_config["column"]]}</div>'
                    folium.Marker(
                        location=[centroid.y, centroid.x],
                        popup=folium.Popup(f"{row[prov_label_config['column']]}", parse_html=True),
                        icon=folium.DivIcon(html=html)
                    ).add_to(label_group_prov)
        if mun_label_config and mun_label_config.get("column"):
            label_group_mun = folium.FeatureGroup("Rótulos Municípios", show=True).add_to(m)
            for _, row in _gdf.iterrows():
                if pd.notna(row[mun_label_config["column"]]) and pd.notna(row.geometry):
                    centroid = row.geometry.centroid
                    font_weight = "bold" if mun_label_config.get("bold", False) else "normal"
                    html = f'<div style="font-size: {mun_label_config["font_size"]}px; color: {mun_label_config["font_color"]}; font-family: {mun_label_config["font_name"]}; font-weight: {font_weight}; text-align: center;">{row[mun_label_config["column"]]}</div>'
                    folium.Marker(
                        location=[centroid.y, centroid.x],
                        popup=folium.Popup(f"{row[mun_label_config['column']]}", parse_html=True),
                        icon=folium.DivIcon(html=html)
                    ).add_to(label_group_mun)
        folium.TileLayer("OpenStreetMap", name="Ruas", attr="pav@ngola.com", show=False).add_to(m)
        folium.TileLayer("CartoDB positron", name="Fundo Cartográfico", attr="Tiles © CartoDB").add_to(m)
        white_tile = branca.utilities.image_to_url([[1, 1], [1, 1]])
        folium.TileLayer(tiles=white_tile, attr="@PAVANGOLA", name="Fundo Branco").add_to(m)
        folium.TileLayer("CartoDB dark_matter", name="Fundo Cinza", attr="Tiles © CartoDB").add_to(m)
        folium.LayerControl(position="topleft", collapsed=True).add_to(m)
        Fullscreen(position="topleft").add_to(m)
        MousePosition(position="topright", separator=" | ").add_to(m)
        m.add_child(MeasureControl(position="topleft", secondary_length_unit='kilometers'))
        if warnings:
            return m, "Mapa criado com avisos: " + "; ".join(warnings), "warning"
        return m, "Mapa criado com sucesso.", "info"
    except KeyError as e:
        return None, f"Erro: Coluna não encontrada no shapefile: {e}", "error"
    except Exception as e:
        return None, f"Erro ao criar o mapa: {e}", "error"

def add_legend(m, color_mapping, title="Legenda"):
    """
    Adiciona uma legenda ao mapa com base no mapeamento de cores.

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
