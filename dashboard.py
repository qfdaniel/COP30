import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from datetime import datetime, date
import pytz
from st_aggrid import AgGrid, GridOptionsBuilder
import json
import io

# --- 0. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Monitoração Remota - COP30",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 1. GERENCIAMENTO DE TEMA E ESTILOS (CSS) ---

BASE_PALETTE = ["#1A311F", "#14337b", "#80B525", "#8D877D", "#DF1B1D", "#DBDAC9"]
VARIANT_PALETTE = ["#4A6D55", "#4464A7", "#608A1B", "#BDBAB3", "#E85C5D", "#B3B2A5"]
COP30_PALETTE = BASE_PALETTE + VARIANT_PALETTE

def toggle_theme():
    if st.session_state.get('theme_toggle', False):
        st.session_state.theme = 'Dark'
    else:
        st.session_state.theme = 'Light'

if 'theme' not in st.session_state:
    st.session_state.theme = 'Light'

def get_theme_css(theme):
    border_color = "#1A311F"
    
    report_button_css = """
    section.main .primary-button .stButton > button {
        border-radius: 8px !important; font-weight: bold !important; border: 1px solid #14337b !important;
        background-color: #14337b !important; color: white !important; transition: all 0.3s ease;
    }
    section.main .primary-button .stButton > button:hover {
        background-color: #2a4e9b !important; border-color: #2a4e9b !important; color: white !important;
    }
    """
    
    print_css = """
    @media print {
        @page { size: landscape; margin: 15mm; }
        body, .stApp { background: white !important; color: black !important; }
        section[data-testid="stSidebar"], header[data-testid="stHeader"], .primary-button { display: none !important; }
        .main .block-container, section.main { width: 100% !important; padding: 0 !important; margin: 0 !important; overflow: visible !important; }
        h1, h2, h3, p, .stMarkdown, .kpi-label, .kpi-value { color: black !important; text-shadow: none !important; }
        .style-marker + div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] { border: 1px solid #AAAAAA !important; box-shadow: none !important; }
        .kpi-box { background-image: none !important; background-color: #EEEEEE !important; border: 1px solid #CCCCCC; }
        .page-break-before { break-before: page; }
    }
    """
    
    kpi_css = """
    .kpi-box {
        position: relative;
        border-radius: 10px; padding: 15px; box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        text-align: center; height: 128px; display: flex; flex-direction: column;
        justify-content: center; align-items: center;
    }
    .kpi-label {
        font-weight: bold; font-size: 1.1em;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.4);
        line-height: 1.2; margin-bottom: 8px; color: white;
    }
    .kpi-value {
        font-weight: bold !important; font-size: 3.0em;
        line-height: 1.1;
    }
    .info-icon-container {
        position: absolute; bottom: 8px; right: 8px;
    }
    .info-icon {
        display: inline-block; width: 16px; height: 16px; line-height: 16px;
        text-align: center; border-radius: 50%; background-color: rgba(255, 255, 255, 0.5);
        color: #1A311F; font-size: 11px; font-weight: bold; cursor: pointer;
    }
    .tooltip-text {
        visibility: hidden; width: 220px; background-color: #333; color: #fff;
        text-align: center; border-radius: 6px; padding: 8px;
        position: absolute; z-index: 1; bottom: 125%; left: 50%;
        margin-left: -110px; opacity: 0; transition: opacity 0.3s;
        font-size: 0.9em;
    }
    .info-icon-container:hover .tooltip-text {
        visibility: visible; opacity: 1;
    }
    """
    
    return f"<style>{print_css}{report_button_css}{kpi_css}{get_full_css(theme)}</style>"

def get_full_css(theme):
    border_color = "#1A311F"
    common_css = f"""
        .block-container {{ padding-top: 0rem; padding-bottom: 2rem; }}
        .stImage > img {{ filter: drop-shadow(4px 4px 8px rgba(0, 0, 0, 0.4)); }}
        [data-testid="stSidebar"] .sidebar-logo img {{ filter: drop-shadow(3px 3px 5px rgba(0,0,0,0.4)); }}
        header[data-testid="stHeader"] {{ background-color: transparent; }}
        h3 {{ font-size: 1.1em !important; }}
        .style-marker {{ display: none; }}
        
        /* ALTERAÇÃO 1: Reduz espaço entre o título e a linha divisória abaixo dele */
        section.main hr {{
            margin-top: -0.5rem !important;
            margin-bottom: 0.5rem !important;
        }}

        /* ALTERAÇÃO 3: Reduz o espaço ABAIXO dos containers dos gráficos e da tabela */
        .style-marker + div[data-testid="stVerticalBlock"] {{
            margin-bottom: 0.1rem !important;
        }}

        [data-testid="stSidebar"] h1 {{ margin-top: -5px; }}
        [data-testid="stSidebar"] .stSelectbox, [data-testid="stSidebar"] [data-testid="stExpander"] summary, .sidebar-info-box {{ 
            border-radius: 8px; padding: 10px; 
        }}
        [data-testid="stSidebar"] .stButton>button {{ border-radius: 8px; font-weight: bold; transition: all 0.3s ease; }}
        section[data-testid="stSidebar"] button:first-child, button[aria-label="Open sidebar"] {{ border: 2px solid #8D877D; border-radius: 5px; }}
        div[data-testid="stSidebar"] .st-emotion-cache-1pxx5r6, div[data-testid="stSidebar"] .st-emotion-cache-1n6o325 {{ margin-top: -1.5rem !important; }}
        [data-testid="stSidebar"] hr {{
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }}
        [data-testid="stSidebar"] .stSelectbox + hr, [data-testid="stSidebar"] .stButton + hr {{
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }}
        [data-testid="stSidebar"] .stCaptionContainer + .sidebar-info-box {{
            margin-top: -0.5rem !important;
        }}
        .ag-header-cell-label {{ justify-content: center; font-weight: bold; }}
    """
    if theme == 'Dark':
        return common_css + f"""
            .style-marker + div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] {{
                border: 2px solid {border_color}; border-radius: 15px; padding: 20px; box-shadow: 0 10px 20px rgba(0,0,0,0.5);
            }}
            .stApp {{ background-color: #1E1E1E; }} 
            h1, h3, .title-subtitle span {{ color: #DBDAC9 !important; text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5); }}
            h2 {{ color: #FFFFFF; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); }}
            button[aria-label="Open sidebar"] svg, button[aria-label="Close sidebar"] svg {{
                fill: #DBDAC9 !important;
            }}
            .kpi-value {{ color: white !important; }}
            [data-testid="stSidebar"] {{ background-image: linear-gradient(to bottom, #2C2C2C, #1E1E1E); }}
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p {{ color: #E0E0E0; }}
            [data-testid="stSidebar"] .stSelectbox, [data-testid="stSidebar"] [data-testid="stExpander"] summary, .sidebar-info-box {{ 
                background-color: #3C3C3C; border: 1px solid #555555; 
            }}
            .sidebar-info-box * {{ color: #BDBAB3 !important; }}
            [data-testid="stSidebar"] .stSelectbox label, [data-testid="stSidebar"] [data-testid="stExpander"] summary p, [data-testid="stSidebar"] .stCheckbox p {{ color: #E0E0E0 !important; }}
            [data-testid="stSidebar"] [data-testid="stExpander"] summary svg {{ fill: #E0E0E0 !important; }}
            [data-testid="stSidebar"] .st-emotion-cache-s492w3 {{ border: 1px solid #555555; background-color: #2C2C2C; color: #E0E0E0; }}
            [data-testid="stSidebar"] small {{ color: #DF1B1D !important; font-weight: bold; }}
            [data-testid="stSidebar"] .stButton>button {{ background-color: #3C3C3C; color: #E0E0E0; border: 1px solid #555555; }}
            [data-testid="stSidebar"] .stButton>button:hover {{ background-color: #0047AB; color: white; border-color: #0047AB; }}
            .ag-theme-alpine-dark .ag-row-even {{ background-color: #2A3F2A !important; }}
        """
    else:
        return common_css + f"""
            .style-marker + div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] {{
                border: 2px solid {border_color}; border-radius: 15px; padding: 20px; box-shadow: 0 10px 20px rgba(0,0,0,0.25);
            }}
            .stApp {{ background-color: #DBDAC9; }} h1, h2, h3 {{ color: #1A311F; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2); }}
            .kpi-value {{ color: #1A311F !important; }}
            [data-testid="stSidebar"] {{ background-image: linear-gradient(to bottom, #F5EFE6, #E8D5C4); }}
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p, [data-testid="stSidebar"] .stCheckbox p {{ color: #38322C; }}
            [data-testid="stSidebar"] .stSelectbox, [data-testid="stSidebar"] [data-testid="stExpander"] summary, .sidebar-info-box {{ 
                background-color: #E8D5C4; border: 1px solid #C3A995; 
            }}
            [data-testid="stSidebar"] .stSelectbox label, [data-testid="stSidebar"] [data-testid="stExpander"] summary p {{ color: #38322C !important; }}
            [data-testid="stSidebar"] [data-testid="stExpander"] summary svg {{ fill: #38322C; }}
            [data-testid="stSidebar"] .st-emotion-cache-s492w3 {{ border: 1px solid #C3A995; background-color: #F5EFE6; color: #38322C; }}
            [data-testid="stSidebar"] small {{ color: #DF1B1D !important; font-weight: bold; }}
            [data-testid="stSidebar"] .stButton>button {{ background-color: #E8D5C4; color: #38322C; border: 1px solid #C3A995; }}
            [data-testid="stSidebar"] .stButton>button:hover {{ background-color: #0047AB; color: white; border-color: #0047AB; }}
            .ag-theme-streamlit .ag-row-even {{ background-color: #E6F5E6 !important; }}
        """

st.markdown(get_theme_css(st.session_state.theme), unsafe_allow_html=True)

@st.cache_data
def to_excel(df: pd.DataFrame):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    return output.getvalue()

@st.cache_data(ttl=300, show_spinner="Buscando novos dados da planilha...")
def carregar_dados():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # --- ALTERAÇÃO PARA STREAMLIT CLOUD ---
        # Acesso às credenciais do Google Sheets via st.secrets
        # O conteúdo do seu google_credentials.json deve ser copiado
        # e colado no painel do Streamlit Cloud como um 'secret'
        # com o nome 'google_credentials'.
        creds_json = json.loads(st.secrets["google_credentials"])
        creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
        
        client = gspread.authorize(creds)
        planilha = client.open("MONITORAÇÃO - COP30")
        aba_painel = planilha.worksheet("PAINEL")
        
        intervalo_tabela = 'A1:AL' 
        dados_lista = aba_painel.get(intervalo_tabela)
        headers = dados_lista.pop(0)
        df = pd.DataFrame(dados_lista, columns=headers)

        total_pendentes = 0
        bsr_jammers_count = 0
        erbs_fake_count = 0
        if not df.empty:
            df = df[df['Faixa de Frequência Envolvida'].astype(str).str.strip() != '']
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)
            if 'Detalhes da Ocorrência' in df.columns: df['Detalhes da Ocorrência'].replace('', '-', inplace=True)
            else: df['Detalhes da Ocorrência'] = '-'
            if 'Situação' in df.columns: total_pendentes = (df['Situação'] == 'Pendente').sum()
        
        fiscais_datas_str = aba_painel.get('W1:AL1')[0]
        fiscais_valores = aba_painel.get('W2:AL2')[0]
        
        fiscais_por_dia = {}
        if len(fiscais_datas_str) == len(fiscais_valores):
            for i, data_str in enumerate(fiscais_datas_str):
                try:
                    data_normalizada = pd.to_datetime(data_str, dayfirst=True).strftime('%d/%m/%Y')
                    fiscais_por_dia[data_normalizada] = fiscais_valores[i]
                except (ValueError, TypeError): continue
        
        try:
            bsr_fake_cells = aba_painel.get('U2:V2')[0]
            bsr_jammers_count = int(bsr_fake_cells[0]) if bsr_fake_cells[0].isdigit() else 0
            erbs_fake_count = int(bsr_fake_cells[1]) if bsr_fake_cells[1].isdigit() else 0
        except (IndexError, ValueError):
            bsr_jammers_count, erbs_fake_count = 0, 0
        
        hoje_completo_str = date.today().strftime('%d/%m/%Y')
        hoje_curto_str = date.today().strftime('%d/%m')
        
        fiscais_hoje = fiscais_por_dia.get(hoje_completo_str, "0")
        
        titulo_data = hoje_curto_str if hoje_completo_str in fiscais_por_dia else "Fora do período"
            
        return df, datetime.now(pytz.timezone('America/Sao_Paulo')), titulo_data, fiscais_hoje, total_pendentes, bsr_jammers_count, erbs_fake_count
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return pd.DataFrame(), None, "Erro", "0", 0, 0, 0

estacoes_info = pd.DataFrame({
    'Estação': ['RFeye002129', 'RFeye002175', 'RFeye002315', 'RFeye002012', 'RFeye002303', 'RFeye002093'],
    'Nome': ['MANGUEIRINHO', 'ALDEIA', 'DOCAS', 'OUTEIRO', 'PARQUE da CIDADE', 'ANATEL'],
    'lat': [-1.382258, -1.446570, -1.448019, -1.278111, -1.413470, -1.427713],
    'lon': [-48.439458, -48.447745, -48.498316, -48.478877, -48.464166, -48.485267],
    'size': 25
})
miaer_info = pd.DataFrame({'Estação': ['Miaer'], 'Nome': ['CENSIPAM'], 'lat': [-1.409319], 'lon': [-48.462516], 'size': 25})
for df_info in [estacoes_info, miaer_info]:
    df_info['NomeFormatado'] = df_info['Nome'].str.title()
    df_info['rotulo'] = df_info['Estação'] + ' - ' + df_info['NomeFormatado']

df_original, ultima_atualizacao, titulo_data, fiscais_hoje, total_pendentes_original, bsr_jammers_count, erbs_fake_count = carregar_dados()
if df_original is None: st.warning("Não foi possível carregar os dados da planilha."); st.stop()
if 'reset_key' not in st.session_state: st.session_state.reset_key = 0

def clear_filters():
    keys_to_delete = []
    for key in st.session_state.keys():
        if key.startswith('date_') or key in [
            'faixa_selecionada', 'frequencia_selecionada', 'severidade_selecionada',
            'estacao_selecionada', 'ocorrencia_selecionada', 'initial_data_selection'
        ]:
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del st.session_state[key]
    st.session_state.reset_key += 1
    st.rerun()

with st.sidebar:
    st.toggle('Modo Dark', key='theme_toggle', value=(st.session_state.theme == 'Dark'), on_change=toggle_theme)
    st.title("Filtros")
    if not df_original.empty:
        df_filtros = df_original.copy().dropna(subset=['Data'])
        for key in ['faixa_selecionada', 'frequencia_selecionada', 'severidade_selecionada', 'estacao_selecionada', 'ocorrencia_selecionada']:
            if key not in st.session_state: st.session_state[key] = 'Todas'
        
        datas_disponiveis = sorted(df_filtros['Data'].dt.date.unique())
        if 'initial_data_selection' not in st.session_state:
            for data in datas_disponiveis: st.session_state[f"date_{data}"] = True
            st.session_state['initial_data_selection'] = True

        with st.expander("Dias do evento", expanded=False):
            if st.button("Selecionar todos", use_container_width=True, key=f"select_all_{st.session_state.reset_key}"):
                for data in datas_disponiveis: st.session_state[f"date_{data}"] = True
                st.rerun()
            if st.button("Desmarcar todos", use_container_width=True, key=f"deselect_all_{st.session_state.reset_key}"):
                for data in datas_disponiveis: st.session_state[f"date_{data}"] = False
                st.rerun()
            st.markdown("---")
            for data in datas_disponiveis:
                st.checkbox(data.strftime('%d/%m/%Y'), key=f"date_{data}")
        
        faixas_lista = ['Todas'] + sorted(list(df_original['Faixa de Frequência Envolvida'].unique()))
        st.session_state['faixa_selecionada'] = st.selectbox('Faixa de Frequência:', faixas_lista, key=f'faixa_select_{st.session_state.reset_key}', index=faixas_lista.index(st.session_state.get('faixa_selecionada', 'Todas')) if st.session_state.get('faixa_selecionada', 'Todas') in faixas_lista else 0)
        
        if 'Frequência (MHz)' in df_original.columns:
            unique_freqs = sorted(df_original['Frequência (MHz)'].dropna().unique().tolist())
            freq_options = ['Todas'] + unique_freqs
            st.session_state['frequencia_selecionada'] = st.selectbox('Frequências (MHz):', freq_options, key=f'frequencia_select_{st.session_state.reset_key}', index=freq_options.index(st.session_state.get('frequencia_selecionada', 'Todas')) if st.session_state.get('frequencia_selecionada', 'Todas') in freq_options else 0)
        
        unique_severidades = df_original['Severidade?'].dropna().unique()
        non_empty_severidades = [s for s in unique_severidades if str(s).strip()]
        severidades_lista = ['Todas'] + sorted(non_empty_severidades)
        st.session_state['severidade_selecionada'] = st.selectbox('Severidade:', severidades_lista, key=f'severidade_select_{st.session_state.reset_key}', index=severidades_lista.index(st.session_state.get('severidade_selecionada', 'Todas')) if st.session_state.get('severidade_selecionada', 'Todas') in severidades_lista else 0)
    else:
        st.warning("Tabela de dados está vazia.")

    estacoes_lista = ['Todas'] + sorted([e for e in estacoes_info['Estação'].unique() if e != 'Miaer'])
    st.session_state['estacao_selecionada'] = st.selectbox('Estação:', estacoes_lista, key=f'estacao_select_{st.session_state.reset_key}', index=estacoes_lista.index(st.session_state.get('estacao_selecionada', 'Todas')) if st.session_state.get('estacao_selecionada', 'Todas') in estacoes_lista else 0)
    opcoes_ocorrencia = ['Todas', 'Pendentes', 'Concluídas']
    st.session_state['ocorrencia_selecionada'] = st.selectbox('Ocorrências:', opcoes_ocorrencia, key=f'ocorrencia_select_{st.session_state.reset_key}', index=opcoes_ocorrencia.index(st.session_state.get('ocorrencia_selecionada', 'Todas')) if st.session_state.get('ocorrencia_selecionada', 'Todas') in opcoes_ocorrencia else 0)

    st.markdown("---")
    normativos_links = {
        "Escolha abaixo": None,
        "PF Interferência em Grandes Eventos": "https://informacoes.anatel.gov.br/legislacao/component/content/article/47-procedimentos-de-fiscalizacao/892-portaria-50632",
        "PF Monitoração em Grandes Eventos": "https://informacoes.anatel.gov.br/legislacao/procedimentos-de-fiscalizacao/891-portaria-50627",
        "Regulamento sobre UTE": "https://informacoes.anatel.gov.br/legislacao/component/content/article/170-resolucoes/2025/2025-resolucao-775",
        "Regulamento sobre BSRs": "https://informacoes.anatel.gov.br/legislacao/resolucoes/2023/1842-resolucao-760",
        "PDFF 2025": "https://informacoes.anatel.gov.br/legislacao/resolucoes/2025/2001-resolucao-772"
    }
    
    selected_normativo = st.selectbox(
        'Consulta de normativos',
        list(normativos_links.keys()),
        index=0
    )

    if selected_normativo and normativos_links[selected_normativo]:
        st.markdown(f"**Acessar:** [{selected_normativo}]({normativos_links[selected_normativo]})")
    st.markdown("---")
    
    if st.button("Limpar Filtros", use_container_width=True, key='clear_filters_button'): clear_filters()
    st.markdown("---")
    if st.button("Atualizar Painel", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    if ultima_atualizacao: st.caption(f"Última atualização: {ultima_atualizacao.strftime('%d/%m/%Y às %H:%M')}")
    
    st.markdown("""
    <div class="sidebar-info-box" style="margin-top: 0.5rem;">
        <b>Equipe:</b><br>
        Daniel Quintão - UO021<br>
        Darlan Silva - GR09<br>
        Halysson Barbosa - UO091<br>
        Leandro Marques - GR02<br>
        Marcelo Loschi - GR04<br>
        Raffaello Bruno - UO062<br>
        Thiago Alves - GR07<br>
        Wilton Machado - GR08
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
    _, logo1_col, logo2_col, _ = st.columns([0.5, 1, 1, 0.5])
    with logo1_col:
        st.image("anatelS.png", width=106)
    with logo2_col:
        st.image("ods.png", width=106)
    st.markdown('</div>', unsafe_allow_html=True)

df = df_original.copy()
if not df.empty:
    datas_selecionadas_list = [data for data, checked in st.session_state.items() if data.startswith('date_') and checked]
    any_date_options = any(key.startswith('date_') for key in st.session_state)
    
    if any_date_options and not datas_selecionadas_list:
        df = pd.DataFrame(columns=df.columns)
    elif datas_selecionadas_list:
        datas_para_filtrar = [pd.to_datetime(data.replace('date_', ''), errors='coerce') for data in datas_selecionadas_list]
        df = df.loc[df['Data'].isin(datas_para_filtrar)]

    if st.session_state.get('estacao_selecionada', 'Todas') != 'Todas': df = df[df['Estação'] == st.session_state['estacao_selecionada']]
    if st.session_state.get('faixa_selecionada', 'Todas') != 'Todas': df = df[df['Faixa de Frequência Envolvida'] == st.session_state['faixa_selecionada']]
    if st.session_state.get('frequencia_selecionada', 'Todas') != 'Todas': df = df[df['Frequência (MHz)'] == st.session_state['frequencia_selecionada']]
    if st.session_state.get('severidade_selecionada', 'Todas') != 'Todas': df = df[df['Severidade?'] == st.session_state['severidade_selecionada']]
    if st.session_state.get('ocorrencia_selecionada', 'Todas') != 'Todas':
        map_status = {'Pendentes': 'Pendente', 'Concluídas': 'Concluída'}
        df = df[df['Situação'] == map_status[st.session_state['ocorrencia_selecionada']]]

header_cols = st.columns([0.1, 0.8, 0.1])
with header_cols[0]: st.image("logo.png", width=135)
with header_cols[1]:
    titulo_formatado = f"<i>{titulo_data}</i>" if titulo_data == "Fora do período" else titulo_data
    st.markdown(f"""
    <div style='text-align: center;'>
        <h1 style='margin-bottom: -7px; margin-top: -1px;'>Monitoração Remota do Espectro - COP30</h1>
        <span class='title-subtitle' style='font-size: 1.3rem; font-weight: normal;'>Dia do evento: {titulo_formatado} &nbsp;&nbsp;-&nbsp;&nbsp; Fiscais em atividade: {fiscais_hoje}</span>
    </div>
    """, unsafe_allow_html=True)
with header_cols[2]: st.image("anatel.png", width=105)
st.markdown("---")

if df.empty:
    st.info("Nenhum dado encontrado para a seleção atual. Por favor, ajuste os filtros na barra lateral.")
    st.stop()
    
ute_count = 0
if 'UTE?' in df_original.columns:
    ute_count = (df_original['UTE?'].astype(str).str.strip().str.lower() == 'true').sum()
else:
    st.sidebar.warning("Coluna 'UTE?' (coluna K) não encontrada na planilha.")

kpi_cols = st.columns(6, gap="small")
kpi_data = [
    {"label": "Emissões verificadas", "value": len(df), "color": "linear-gradient(135deg, #4CAF50 0%, #9CCC65 100%)", "tooltip": "Total de emissões detectadas e analisadas dentro do período e filtros selecionados."},
    {"label": "Emissões UTE", "value": ute_count, "color": "linear-gradient(135deg, #4CAF50 0%, #9CCC65 100%)", "tooltip": "Contagem de emissões classificadas como UTE em todo o período."},
    {"label": "Não Licenciadas", "value": len(df[df['Autorizado?'] == 'FALSE']), "color": "linear-gradient(135deg, #4CAF50 0%, #9CCC65 100%)", "tooltip": "Contagem de emissões não autorizadas dentro dos filtros selecionados."},
    {"label": "Verificações Pendentes", "value": total_pendentes_original, "color": f"linear-gradient(135deg, {BASE_PALETTE[4]} 0%, {VARIANT_PALETTE[4]} 100%)", "tooltip": "Total de emissões com situação 'Pendente' em todo o período (não afetado por filtros)."},
    {"label": "BSRs (Jammers)", "value": bsr_jammers_count, "color": f"linear-gradient(135deg, {BASE_PALETTE[4]} 0%, {VARIANT_PALETTE[4]} 100%)", "tooltip": "Contagem de BSRs ou Jammers detectados."},
    {"label": "ERBs Fake", "value": erbs_fake_count, "color": f"linear-gradient(135deg, {BASE_PALETTE[4]} 0%, {VARIANT_PALETTE[4]} 100%)", "tooltip": "Contagem de ERBs Falsas detectadas."}
]
for i, data in enumerate(kpi_data):
    with kpi_cols[i]:
        st.markdown(f"""
        <div class="kpi-box" style="background-image: {data['color']};">
            <div class="info-icon-container">
                <span class="info-icon">i</span>
                <span class="tooltip-text">{data['tooltip']}</span>
            </div>
            <div class="kpi-label">{data['label']}</div>
            <div class="kpi-value">{data['value']}</div>
        </div>
        """, unsafe_allow_html=True)
    
# ALTERAÇÃO 2: Adiciona um espaçador vertical entre os KPIs e os gráficos.
# Você pode ajustar o valor '2.5rem' para aumentar ou diminuir o espaço.
st.markdown('<div style="margin-top: 2.5rem;"></div>', unsafe_allow_html=True)

if not df.empty:
    df_com_nomes = pd.merge(df, estacoes_info[['Estação', 'Nome']], on='Estação', how='left')
    top_col1, top_col2, top_col3 = st.columns([0.3, 0.3, 0.4], gap="small")
    with top_col1:
        with st.container():
            st.markdown('<div class="style-marker"></div>', unsafe_allow_html=True)
            st.subheader("Emissões por Região")
            data_estacao = df_com_nomes['Nome'].value_counts().reset_index()
            data_estacao.columns = ['Nome', 'count']
            data_estacao['label'] = data_estacao['Nome'] + ' (' + data_estacao['count'].astype(str) + ')'
            fig_treemap_estacao = px.treemap(data_estacao, path=['label'], values='count', color='Nome', color_discrete_sequence=COP30_PALETTE)
            fig_treemap_estacao.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=400, paper_bgcolor='rgba(141, 135, 121, 0.2)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_treemap_estacao, use_container_width=True)
    with top_col2:
        with st.container():
            st.markdown('<div class="style-marker"></div>', unsafe_allow_html=True)
            st.subheader("Emissões por Faixa")
            bar_data_faixa = df['Faixa de Frequência Envolvida'].value_counts().reset_index()
            bar_data_faixa.columns = ['Faixa', 'count']
            fig_donut_faixa = px.pie(bar_data_faixa, names='Faixa', values='count', color_discrete_sequence=COP30_PALETTE, hole=0.4)
            fig_donut_faixa.update_traces(texttemplate='%{label}<br>%{value} (%{percent})', textposition='inside', textfont_size=12)
            fig_donut_faixa.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=400, paper_bgcolor='rgba(141, 135, 121, 0.2)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_donut_faixa, use_container_width=True)
    with top_col3:
        with st.container():
            st.markdown('<div class="style-marker"></div>', unsafe_allow_html=True)
            st.subheader("Emissões por tipo")
            if 'Identificação' in df.columns:
                identificacao_data = df['Identificação'].dropna()
                identificacao_data = identificacao_data[identificacao_data.astype(str).str.strip() != '']
                if not identificacao_data.empty:
                    data_source = identificacao_data.value_counts().reset_index()
                    data_source.columns = ['Identificação', 'count']
                    data_source['label'] = data_source['Identificação'] + ' (' + data_source['count'].astype(str) + ')'
                    fig_chart = px.bar(data_source, x='count', y='Identificação', orientation='h', color='Identificação', color_discrete_sequence=COP30_PALETTE, text='label')
                    fig_chart.update_layout(yaxis_title='', yaxis=dict(showticklabels=False), xaxis=dict(visible=False), showlegend=False, margin=dict(t=10, b=10, l=0, r=10), height=400, paper_bgcolor='rgba(141, 135, 121, 0.2)', plot_bgcolor='rgba(0,0,0,0)')
                    fig_chart.update_traces(textposition='auto')
                    st.plotly_chart(fig_chart, use_container_width=True)
                else: st.info("Não há dados de 'Identificação' para a seleção atual.")
            else: st.warning("Coluna 'Identificação' não encontrada. Verifique o nome da Coluna I na planilha.")

    bottom_cols = st.columns([0.45, 0.55], gap="small")
    with bottom_cols[0]:
        with st.container():
            st.markdown('<div class="style-marker"></div>', unsafe_allow_html=True)
            st.subheader("Mapa das Estações")
            all_estacoes_info = pd.concat([estacoes_info, miaer_info], ignore_index=True)
            center_lat, center_lon = all_estacoes_info['lat'].mean(), all_estacoes_info['lon'].mean()
            fig_mapa = px.scatter_mapbox(all_estacoes_info, lat="lat", lon="lon", size_max=25, text="rotulo", hover_name="rotulo", zoom=10, height=424)
            fig_mapa.update_traces(marker=dict(size=13, color="#1A311F"), textfont_color='#1A311F', textposition='middle right')
            fig_mapa.update_layout(mapbox_style="carto-positron", mapbox_center={"lat": center_lat, "lon": center_lon}, margin={"r":0, "t":0, "l":0, "b":0}, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  uniformtext=dict(minsize=6, mode='show'),
                                  mapbox_layers=[
                                      {"source": json.loads('{"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[-48.46271165940957,-1.410547386930189], [-48.46354296701018,-1.410203920775152], [-48.46452300205883,-1.410589379729715], [-48.46481338341509,-1.410947294928633], [-48.46480901688122,-1.411743890008883], [-48.46476950492082,-1.412718397847341], [-48.46501339404546,-1.413220476289419], [-48.46505954643188,-1.413593356218595], [-48.46299946948039,-1.415682109733712], [-48.46223745889785,-1.41493726617121], [-48.46193440440009,-1.41506754383678], [-48.46160981147195,-1.415618320052126], [-48.46236515358898,-1.41646519254085], [-48.46029976924051,-1.418538693038281], [-48.45921609865986,-1.417408620572469], [-48.4612069857882,-1.41539858384322], [-48.45963018655848,-1.413805502459938], [-48.46271165940957,-1.410547386930189]]]}}]}'), "type": "fill", "color": "rgba(0, 255, 0, 0.5)"},
                                      {"source": json.loads('{"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[-48.45959464675182,-1.413824160742325], [-48.46115955268121,-1.41541976951611], [-48.45902894923615,-1.417522902260756], [-48.45638287288467,-1.420317822531534], [-48.45765406178806,-1.422206297114926], [-48.45764136955441,-1.422452385058413], [-48.45687501383681,-1.423154480079293], [-48.45559653463967,-1.422811508724929], [-48.454740001063,-1.42206627992075], [-48.4541426707238,-1.421661972091132], [-48.45383496756163,-1.419824290338865], [-48.45959464675182,-1.413824160742325]]]}}]}'), "type": "fill", "color": "rgba(0, 0, 255, 0.5)"}
                                  ])
            st.plotly_chart(fig_mapa, use_container_width=True)
    with bottom_cols[1]:
        with st.container():
            st.markdown('<div class="style-marker"></div>', unsafe_allow_html=True)
            st.subheader("Emissões identificadas por Estação/dia")
            df_chart = df.dropna(subset=['Data']).copy()
            if not df_chart.empty:
                df_chart['Data'] = df_chart['Data'].dt.date
                emissoes_por_estacao_dia = df_chart.groupby(['Data', 'Estação']).size().reset_index(name='Nº de Emissões')
                fig_estacao_dia = px.bar(emissoes_por_estacao_dia, x='Data', y='Nº de Emissões', color='Estação', template="plotly_white", color_discrete_sequence=COP30_PALETTE, text='Nº de Emissões')
                fig_estacao_dia.update_traces(textposition='inside', textfont_size=12)
                fig_estacao_dia.update_xaxes(tickformat="%d/%m", title_text='')
                fig_estacao_dia.update_yaxes(title_text='', dtick=1)
                fig_estacao_dia.update_layout(
                    legend_title='', 
                    margin={"r":19, "t":10, "l":0, "b":10}, 
                    paper_bgcolor='rgba(141, 135, 121, 0.2)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    height=424,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.2,
                        xanchor="center",
                        x=0.5
                    )
                )
                st.plotly_chart(fig_estacao_dia, use_container_width=True)
            else: st.info("Nenhuma emissão com data válida na seleção.")
    
    st.markdown('<div class="page-break-before"></div>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="style-marker"></div>', unsafe_allow_html=True)
        colunas_para_exibir = {'Data': 'Data', 'Nome': 'Região', 'Estação': 'Estação','Frequência (MHz)': 'Frequência (MHz)', 'Largura (kHz)': 'Largura (kHz)', 'Faixa de Frequência Envolvida': 'Faixa de Frequência','Autorizado?': 'Autorizado?', 'Severidade?': 'Severidade', 'Detalhes da Ocorrência': 'Detalhes','Fiscal': 'Fiscal','Situação': 'Situação'}
        colunas_existentes = [col for col in colunas_para_exibir.keys() if col in df_com_nomes.columns]
        if 'Fiscal' not in colunas_existentes and 'fiscal_warning' not in st.session_state:
            st.session_state.fiscal_warning = True
            st.sidebar.warning("A coluna 'Fiscal' não foi encontrada. Verifique o nome do cabeçalho.")
        if 'Largura (kHz)' not in colunas_existentes and 'largura_warning' not in st.session_state:
            st.session_state.largura_warning = True
            st.sidebar.warning("A coluna 'Largura (kHz)' (coluna G) não foi encontrada. Verifique o nome do cabeçalho.")
            
        df_tabela = df_com_nomes[colunas_existentes].rename(columns=colunas_para_exibir)
        if 'Data' in df_tabela.columns:
            df_tabela['Data'] = pd.to_datetime(df_tabela['Data'], errors='coerce')
            df_tabela.sort_values(by='Data', ascending=False, inplace=True)
            df_tabela['Data'] = df_tabela['Data'].dt.strftime('%d/%m/%Y')
        if 'Região' in df_tabela.columns: df_tabela['Região'] = df_tabela['Região'].str.title()
        if 'Detalhes' in df_tabela.columns: df_tabela['Detalhes'] = df_tabela['Detalhes'].replace('', '-').fillna('-')
        df_para_exportar = df_tabela.copy()
        df_xlsx = to_excel(df_para_exportar)
        col_titulo, col_botao = st.columns([0.75, 0.25])
        with col_titulo: st.subheader("Histórico geral de identificações")
        with col_botao: st.download_button(label="📥 Exportar para Excel (.xlsx)", data=df_xlsx, file_name='historico_cop30.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
        gb = GridOptionsBuilder.from_dataframe(df_tabela)
        gb.configure_default_column(flex=1, cellStyle={'text-align': 'center'}, sortable=True, filter=True, resizable=True)
        gridOptions = gb.build()
        AgGrid(df_tabela, gridOptions=gridOptions, theme='streamlit' if st.session_state.theme == 'Light' else 'alpine-dark', allow_unsafe_jscode=True, height=400, use_container_width=True)
        
        st.markdown("---")
        
        if 'confirm_export' not in st.session_state: st.session_state.confirm_export = False
        if 'appanalise_bytes' not in st.session_state: st.session_state.appanalise_bytes = None

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            st.markdown('<div class="primary-button">', unsafe_allow_html=True)
            if st.button("Gerar Relatório Diário - Monitoração Remota COP30", use_container_width=True):
                st.components.v1.html("<script>window.print()</script>", height=0)
            st.markdown('</div>', unsafe_allow_html=True)

        with btn_col2:
            placeholder = st.empty()
            if not st.session_state.confirm_export:
                with placeholder.container():
                    st.markdown('<div class="primary-button">', unsafe_allow_html=True)
                    if st.button("Gerar arquivo de emissões para AppAnálise", use_container_width=True):
                        st.session_state.confirm_export = True
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            
            if st.session_state.confirm_export:
                with placeholder.container():
                    st.warning("Confirma que selecionou a(s) estação(ões) RFeye desejada(s)?")
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("Sim", use_container_width=True, type="primary"):
                            with st.spinner("Gerando arquivo..."):
                                source_cols = ['Frequência (MHz)', 'Largura (kHz)', 'Identificação', 'Processo SEI UTE']
                                target_cols = {'Frequência (MHz)': 'Frequencia', 'Largura (kHz)': 'Largura', 'Identificação': 'Identificação', 'Processo SEI UTE': 'Processo SEI UTE'}
                                cols_to_pull = [col for col in source_cols if col in df.columns]
                                
                                if not cols_to_pull:
                                    st.error("Nenhuma das colunas para o AppAnálise foi encontrada.")
                                    st.session_state.appanalise_bytes = None
                                else:
                                    df_appanalise = df[cols_to_pull].rename(columns=target_cols)
                                    st.session_state.appanalise_bytes = to_excel(df_appanalise)
                            
                            st.session_state.confirm_export = False
                            st.rerun()

                    with confirm_col2:
                        if st.button("Não", use_container_width=True):
                            st.session_state.confirm_export = False
                            st.rerun()

            if st.session_state.appanalise_bytes:
                st.download_button(
                    label="📥 Baixar Arquivo para AppAnálise (.xlsx)",
                    data=st.session_state.appanalise_bytes,
                    file_name=f"emissoes_appanalise_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                st.session_state.appanalise_bytes = None
else:
    st.warning("Nenhum dado encontrado para a seleção atual.")