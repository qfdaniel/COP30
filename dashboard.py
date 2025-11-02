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
import streamlit.components.v1 as components

# --- 0. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Monitoração do Espectro - COP30",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)
# Coloque este código logo após o st.set-page_config
st.markdown("""
<style>
    /* Nova tentativa usando um seletor mais estável (data-testid) */
    div[data-testid="stElementContainer"] hr {
        margin-top: -0.8rem !important;
        margin-bottom: -0.8rem !important;
    }
</style>
""", unsafe_allow_html=True)
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
        section.main > div:first-child {{
            margin-top: -5rem !important;
        }}
        .block-container {{ padding-top: 2rem !important; padding-bottom: 2rem; }}
        .stImage > img {{ filter: drop-shadow(4px 4px 8px rgba(0, 0, 0, 0.4)); }}
        header[data-testid="stHeader"] {{ background-color: transparent; }}
        h3 {{ font-size: 1.1em !important; }}
        .style-marker, .table-container-style {{ display: none; }}
        section.main hr {{
            margin-top: -0.5rem !important;
            margin-bottom: 0.5rem !important;
        }}
        .style-marker + div[data-testid="stVerticalBlock"] {{
            margin-bottom: 0.1rem !important;
        }}
        [data-testid="stSidebar"] h1 {{ margin-top: -5px; }}
        [data-testid="stSidebar"] .stSelectbox, [data-testid="stSidebar"] .stMultiSelect, [data-testid="stSidebar"] [data-testid="stExpander"] summary, .sidebar-info-box {{ 
            border-radius: 8px; padding: 10px; 
        }}
        [data-testid="stSidebar"] .stButton>button {{ border-radius: 8px; font-weight: bold; transition: all 0.3s ease; }}
        section[data-testid="stSidebar"] button:first-child, button[aria-label="Open sidebar"] {{ border: 2px solid #8D877D; border-radius: 5px; }}
        div[data-testid="stSidebar"] .st-emotion-cache-1pxx5r6, div[data-testid="stSidebar"] .st-emotion-cache-1n6o325 {{ margin-top: -1.5rem !important; }}
        [data-testid="stSidebar"] hr {{
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }}
        [data-testid="stSidebar"] .stSelectbox + hr, [data-testid="stSidebar"] .stMultiSelect + hr, [data-testid="stSidebar"] .stButton + hr {{
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }}
        [data-testid="stSidebar"] .stCaptionContainer + .sidebar-info-box {{
            margin-top: -0.5rem !important;
        }}
        .ag-header-cell-label {{ justify-content: center; text-align: center; font-weight: bold; }}
        .confirm-yes-button .stButton > button {{
            background-color: #4CAF50 !important; color: white !important; border: 1px solid #388E3C !important;
        }}
        .confirm-yes-button .stButton > button:hover {{
            background-color: #66BB6A !important; border-color: #4CAF50 !important; color: white !important;
        }}
        .confirm-no-button .stButton > button {{
            background-color: #DF1B1D !important; color: white !important; border: 1px solid #C62828 !important;
        }}
        .confirm-no-button .stButton > button:hover {{
            background-color: #E57373 !important; border-color: #DF1B1D !important; color: white !important;
        }}
        .table-container-style + div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] {{
            border: 1px solid {border_color}; border-radius: 15px; padding: 15px; box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        }}
    """
    if theme == 'Dark':
        return common_css + f"""
            .style-marker + div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] {{
                border: 2px solid {border_color}; border-radius: 15px; padding: 20px; box-shadow: 0 10px 20px rgba(0,0,0,0.5);
            }}
            .stApp {{ background-color: #1E1E1E; }} 
            h1, h3, .title-subtitle {{ color: #DBDAC9 !important; text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5); }}
            h2 {{ color: #FFFFFF; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5); }}
            button[aria-label="Open sidebar"] svg, button[aria-label="Close sidebar"] svg {{
                fill: #DBDAC9 !important;
            }}
            .kpi-value {{ color: white !important; }}
            [data-testid="stSidebar"] {{ background-image: linear-gradient(to bottom, #2C2C2C, #1E1E1E); }}
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p {{ color: #E0E0E0; }}
            [data-testid="stSidebar"] .stSelectbox, [data-testid="stSidebar"] .stMultiSelect, [data-testid="stSidebar"] [data-testid="stExpander"] summary, .sidebar-info-box {{ 
                background-color: #3C3C3C; border: 1px solid #555555; 
            }}
            .sidebar-info-box * {{ color: #BDBAB3 !important; }}
            [data-testid="stSidebar"] .stSelectbox label, [data-testid="stSidebar"] .stMultiSelect label, [data-testid="stSidebar"] [data-testid="stExpander"] summary p, [data-testid="stSidebar"] .stCheckbox p {{ color: #E0E0E0 !important; }}
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
            [data-testid="stSidebar"] .stSelectbox, [data-testid="stSidebar"] .stMultiSelect, [data-testid="stSidebar"] [data-testid="stExpander"] summary, .sidebar-info-box {{ 
                background-color: #E8D5C4; border: 1px solid #C3A995; 
            }}
            [data-testid="stSidebar"] .stSelectbox label, [data-testid="stSidebar"] .stMultiSelect label, [data-testid="stSidebar"] [data-testid="stExpander"] summary p {{ color: #38322C !important; }}
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

# --- FUNÇÃO DE CARREGAMENTO DE DADOS ATUALIZADA COM AS NOVAS REGRAS ---
@st.cache_data(ttl=30, show_spinner="Buscando novos dados da planilha...")
def carregar_dados():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        client = gspread.authorize(creds)
        planilha = client.open("MONITORAÇÃO - COP30")

        # --- DADOS DO PAINEL ---
        aba_painel = planilha.worksheet("PAINEL")
        dados_painel = aba_painel.get('A1:AL')
        headers = dados_painel.pop(0)
        df_painel = pd.DataFrame(dados_painel, columns=headers)
        
        # --- DADOS DA ABORDAGEM ---
        aba_abordagem = planilha.worksheet("Abordagem")
        dados_abordagem = aba_abordagem.get('I1:W')
        df_abordagem_final = pd.DataFrame()
        
        if len(dados_abordagem) > 1:
            headers_abordagem = dados_abordagem.pop(0)
            df_abordagem_raw = pd.DataFrame(dados_abordagem, columns=headers_abordagem)
            
            df_abordagem_raw.replace('', pd.NA, inplace=True)
            df_abordagem_raw.dropna(how='all', inplace=True)

            if not df_abordagem_raw.empty:
                df_aligned = pd.DataFrame(columns=headers)

                # Mapeamento explícito de Abordagem (I:W) para Painel (A:AL)
                map_letter_to_idx = {chr(ord('I') + i): i for i in range(len(headers_abordagem))}

                def get_col_data(letter):
                    idx = map_letter_to_idx.get(letter)
                    if idx is not None and idx < len(headers_abordagem):
                        return df_abordagem_raw[headers_abordagem[idx]]
                    return pd.Series([None] * len(df_abordagem_raw))

                df_aligned['Data'] = get_col_data('K')
                df_aligned['Fiscal'] = get_col_data('J')
                df_aligned['Frequência (MHz)'] = get_col_data('M')
                df_aligned['Largura (kHz)'] = get_col_data('N')
                df_aligned['Faixa de Frequência Envolvida'] = get_col_data('O')
                df_aligned['Identificação'] = get_col_data('P')
                df_aligned['Autorizado?'] = get_col_data('Q')
                df_aligned['Interferente?'] = get_col_data('V')
                if len(headers) > 10:
                    df_aligned[headers[10]] = get_col_data('R') # UTE?
                df_aligned['Processo SEI UTE'] = get_col_data('S')
                df_aligned['Situação'] = get_col_data('W')
                
                # Tratamento do campo concatenado (T=Responsável, U=Observações)
                responsavel = get_col_data('T').astype(str).fillna('').str.strip()
                observacoes = get_col_data('U').astype(str).fillna('').str.strip()
                detalhes = responsavel.str.cat(observacoes, sep=' - ').str.strip(' -').replace('', '-')
                df_aligned['Detalhes da Ocorrência'] = detalhes
                
                df_aligned['Estação'] = 'Abordagem'
                df_abordagem_final = df_aligned

        # --- COMBINA OS DATAFRAMES ---
        df_return = pd.concat([df_painel, df_abordagem_final], ignore_index=True)

        # --- LIMPEZA E PROCESSAMENTO DOS DADOS COMBINADOS ---
        total_pendentes = 0
        if not df_return.empty:
            df_return.replace('', pd.NA, inplace=True)
            df_return.dropna(subset=['Faixa de Frequência Envolvida'], how='all', inplace=True)
            df_return['Data'] = pd.to_datetime(df_return['Data'], errors='coerce', dayfirst=True)
            if 'Detalhes da Ocorrência' in df_return.columns:
                df_return['Detalhes da Ocorrência'] = df_return['Detalhes da Ocorrência'].fillna('-')
            if 'Situação' in df_return.columns:
                total_pendentes = (df_return['Situação'] == 'Pendente').sum()

        # --- CÁLCULOS DE KPIs ---
        col_f_painel = aba_painel.col_values(6)
        col_m_abordagem = aba_abordagem.col_values(13)
        kpi_emissoes_verificadas = sum(1 for c in col_f_painel[1:] if c) + sum(1 for c in col_m_abordagem[1:] if c)

        col_j_painel = aba_painel.col_values(10)
        col_q_abordagem = aba_abordagem.col_values(17)
        kpi_nao_licenciadas = col_j_painel.count('Não') + col_q_abordagem.count('Não')

        col_o_painel = aba_painel.col_values(15)
        col_v_abordagem = aba_abordagem.col_values(22)
        kpi_interferencias = col_o_painel.count('Sim') + col_v_abordagem.count('Sim')

        fiscais_datas_str = aba_painel.get('W1:AL1')[0]
        fiscais_valores = aba_painel.get('W2:AL2')[0]
        hoje_brasil = datetime.now(pytz.timezone('America/Sao_Paulo'))
        titulo_data = "Fora do período"
        fiscais_hoje = "0"
        if len(fiscais_datas_str) == len(fiscais_valores):
            for i, data_str in enumerate(fiscais_datas_str):
                if str(data_str).strip() == hoje_brasil.strftime('%d/%m/%Y'):
                    fiscais_hoje = fiscais_valores[i]
                    titulo_data = hoje_brasil.strftime('%d/%m')
                    break
        
        bsr_jammers_count, erbs_fake_count = 0, 0
        try:
            bsr_fake_cells = aba_painel.get('U2:V2')[0]
            bsr_jammers_count = int(bsr_fake_cells[0]) if bsr_fake_cells and bsr_fake_cells[0].isdigit() else 0
            erbs_fake_count = int(bsr_fake_cells[1]) if len(bsr_fake_cells) > 1 and bsr_fake_cells[1].isdigit() else 0
        except (IndexError, ValueError):
            bsr_jammers_count, erbs_fake_count = 0, 0
            
        return (df_return, datetime.now(pytz.timezone('America/Sao_Paulo')), titulo_data, fiscais_hoje,
                total_pendentes, bsr_jammers_count, erbs_fake_count, 
                kpi_emissoes_verificadas, kpi_nao_licenciadas, kpi_interferencias)

    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return pd.DataFrame(), None, "Erro", "0", 0, 0, 0, 0, 0, 0
estacoes_info = pd.DataFrame({
    'Estação': ['RFeye002129', 'RFeye002175', 'RFeye002315', 'RFeye002012', 'RFeye002303', 'RFeye002093'],
    'Nome': ['MANGUEIRINHO', 'ALDEIA', 'DOCAS', 'OUTEIRO', 'PARQUE da CIDADE', 'ANATEL'],
    'lat': [-1.382258, -1.446570, -1.448019, -1.278111, -1.413470, -1.427713],
    'lon': [-48.439458, -48.447745, -48.498316, -48.478877, -48.464166, -48.485267],
    'size': 25
})
miaer_info = pd.DataFrame({'Estação': ['Miaer'], 'Nome': ['CENSIPAM'], 'lat': [-1.409319], 'lon': [-48.462516], 'size': 25})
cellpl_info = pd.DataFrame({'Estação': ['CWSM211022'], 'Nome': ['UFPA'], 'lat': [-1.476756], 'lon': [-48.456606], 'size': 25})

# Bloco Novo (Substituição)
# Combina todos os metadados das estações em um único DataFrame
# Linha Nova (Substituição)
# A variável 'all_estacoes_info' já foi criada no início do script.

# Aplica a formatação em todos de uma vez
all_estacoes_info['NomeFormatado'] = all_estacoes_info['Nome'].str.title()
all_estacoes_info['rotulo'] = all_estacoes_info['Estação'] + ' - ' + all_estacoes_info['NomeFormatado']

(df_original, ultima_atualizacao, titulo_data, fiscais_hoje, 
 total_pendentes_original, bsr_jammers_count, erbs_fake_count, 
 kpi_emissoes_verificadas, kpi_nao_licenciadas, kpi_interferencias) = carregar_dados()

if df_original is None: st.warning("Não foi possível carregar os dados da planilha."); st.stop()
if 'reset_key' not in st.session_state: st.session_state.reset_key = 0

def clear_filters():
    keys_to_delete = []
    for key in st.session_state.keys():
        if key.startswith(('date_', 'station_')) or key in [
            'faixa_selecionada', 'frequencia_selecionada', 'interferente_selecionado',
            'licenciamento_selecionado', 'ocorrencia_selecionada', 'initial_data_selection', 
            'station_filter_initialized', 'ute_selecionado'
        ]:
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del st.session_state[key]
    st.session_state.reset_key += 1
    st.rerun()

with st.sidebar:
    st.toggle('Modo Dark', key='theme_toggle', value=(st.session_state.theme == 'Dark'), on_change=toggle_theme)
    st.title("Filtros")
    
    # MODIFICAÇÃO: Adicionado 'Abordagem' à lista de filtros de estação
    # Bloco Novo (Substituição)
    estacoes_lista = sorted(all_estacoes_info['Estação'].unique().tolist()) + ['Abordagem']

    if not df_original.empty:
        df_filtros = df_original[df_original['Data'].notna()].copy()
        
        for key in ['faixa_selecionada', 'frequencia_selecionada', 'interferente_selecionado', 'licenciamento_selecionado', 'ocorrencia_selecionada', 'ute_selecionado']:
            if key not in st.session_state: st.session_state[key] = 'Todas'
        
        if 'station_filter_initialized' not in st.session_state:
            for station in estacoes_lista:
                st.session_state[f'station_{station}'] = True
            st.session_state['station_filter_initialized'] = True
        
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
        
        with st.expander("Estação(ões)", expanded=False):
            for station in estacoes_lista:
                st.checkbox(station, key=f'station_{station}')

        faixas_lista = ['Todas'] + sorted(list(df_original['Faixa de Frequência Envolvida'].dropna().unique()))
        st.selectbox('Faixa de Frequência:', faixas_lista, key='faixa_selecionada')

        if 'Frequência (MHz)' in df_original.columns:
            unique_freqs = sorted(df_original['Frequência (MHz)'].dropna().unique().tolist())
            freq_options = ['Todas'] + unique_freqs
            st.selectbox('Frequências (MHz):', freq_options, key='frequencia_selecionada')
        
        opcoes_interferente = ['Todas', 'Sim', 'Não', 'Indefinido']
        st.selectbox('Interferente?:', opcoes_interferente, key='interferente_selecionado')

        opcoes_licenciamento = ['Todas', 'Licenciado', 'Não licenciado', 'Não licenciável']
        st.selectbox('Licenciamento:', opcoes_licenciamento, key='licenciamento_selecionado')
        
    else:
        st.warning("Tabela de dados está vazia.")

    opcoes_ocorrencia = ['Todas', 'Pendentes', 'Concluídas']
    st.selectbox('Ocorrências:', opcoes_ocorrencia, key='ocorrencia_selecionada')
    
    opcoes_ute = ['Todas', 'Sim', 'Não']
    st.selectbox('Emissões UTE:', opcoes_ute, key='ute_selecionado')

    st.markdown("---")
    normativos_links = {
        "Escolha abaixo": None,
        "PF Interferência em Grandes Eventos": "https://informacoes.anatel.gov.br/legislacao/component/content/article/47-procedimentos-de-fiscalizacao/892-portaria-50632",
        "PF Monitoração em Grandes Eventos": "https://informacoes.anatel.gov.br/legislacao/procedimentos-de-fiscalizacao/891-portaria-50627",
        "Regulamento sobre UTE": "https://informacoes.anatel.gov.br/legislacao/component/content/article/170-resolucoes/2025/2025-resolucao-775",
        "Regulamento sobre BSRs": "https://informacoes.anatel.gov.br/legislacao/resolucoes/2023/1842-resolucao-760",
        "PDFF 2025": "https://informacoes.anatel.gov.br/legislacao/resolucoes/2025/2001-resolucao-772"
    }
    selected_normativo = st.selectbox('Consulta de normativos', list(normativos_links.keys()), index=0)
    if selected_normativo and normativos_links[selected_normativo]:
        st.markdown(f"**Acessar:** [{selected_normativo}]({normativos_links[selected_normativo]})")
    st.markdown("---")
    if st.button("Limpar Filtros", use_container_width=True, key='clear_filters_button'): clear_filters()
    st.markdown("---")
    if st.button("Atualizar Painel", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    if ultima_atualizacao: st.caption(f"Última atualização: {ultima_atualizacao.strftime('%d/%m/%Y às %H:%M')}")
    st.markdown("---")
    if 'confirm_export' not in st.session_state: st.session_state.confirm_export = False
    if 'appanalise_bytes' not in st.session_state: st.session_state.appanalise_bytes = None
    placeholder_sidebar = st.empty()
    st.markdown("---")
    st.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
    _, logo1_col, logo2_col, _ = st.columns([0.5, 1, 1, 0.5])
    with logo1_col: st.image("anatelS.png", width=106)
    with logo2_col: st.image("ods.png", width=106)
    st.markdown('</div>', unsafe_allow_html=True)

df = df_original.copy()
if not df.empty:
    if len(df.columns) > 10:
        coluna_k_nome = df.columns[10]
        df['UTE?'] = df[coluna_k_nome].apply(lambda x: 'Sim' if str(x).strip().upper() in ['TRUE', 'SIM'] else 'Não')
    else:
        df['UTE?'] = 'Não'

    if 'Situação' in df.columns:
        df['Situação'] = df['Situação'].str.strip().str.capitalize()

    datas_selecionadas_list = [data for data, checked in st.session_state.items() if data.startswith('date_') and checked]
    any_date_options = any(key.startswith('date_') for key in st.session_state)
    if any_date_options and not datas_selecionadas_list:
        df = pd.DataFrame(columns=df_original.columns)
    elif datas_selecionadas_list:
        df_non_na = df[df['Data'].notna()]
        datas_para_filtrar = [pd.to_datetime(d.replace('date_', ''), errors='coerce').date() for d in datas_selecionadas_list]
        df = df[df['Data'].dt.date.isin(datas_para_filtrar) | df['Data'].isna()]

    # MODIFICAÇÃO: Lógica de filtro de estação simplificada e corrigida
    estacoes_selecionadas = [s for s in estacoes_lista if st.session_state.get(f'station_{s}', False)]
    if any(st.session_state.get(f'station_{s}', False) for s in estacoes_lista):
        df = df[df['Estação'].isin(estacoes_selecionadas)]
    else:
        # Se nenhuma estação for selecionada, o dataframe fica vazio
        df = pd.DataFrame(columns=df.columns)

    if st.session_state.get('faixa_selecionada', 'Todas') != 'Todas': 
        df = df[df['Faixa de Frequência Envolvida'] == st.session_state.faixa_selecionada]
    if st.session_state.get('frequencia_selecionada', 'Todas') != 'Todas': 
        df = df[df['Frequência (MHz)'] == st.session_state.frequencia_selecionada]
    if st.session_state.get('interferente_selecionado', 'Todas') != 'Todas': 
        df = df[df['Interferente?'] == st.session_state.interferente_selecionado]
    if st.session_state.get('licenciamento_selecionado', 'Todas') != 'Todas':
        selecao = st.session_state.licenciamento_selecionado
        if selecao == 'Não licenciado':
            df = df[df['Autorizado?'].astype(str).str.strip().str.upper() == 'NÃO']
        else:
            df = df[df['Autorizado?'].astype(str).str.strip() == selecao]
    if st.session_state.get('ocorrencia_selecionada', 'Todas') != 'Todas':
        map_status = {'Pendentes': 'Pendente', 'Concluídas': 'Concluído'}
        df = df[df['Situação'] == map_status[st.session_state.ocorrencia_selecionada]]
    if st.session_state.get('ute_selecionado', 'Todas') != 'Todas':
        df = df[df['UTE?'] == st.session_state.ute_selecionado]

if not st.session_state.confirm_export:
    with placeholder_sidebar.container():
        if st.button("Gerar arquivo para AppAnálise", use_container_width=True):
            st.session_state.confirm_export = True
            st.rerun()
if st.session_state.confirm_export:
    with placeholder_sidebar.container():
        st.warning("Confirma a seleção da(s) estação(ões) RFeye?")
        confirm_col1, confirm_col2 = st.columns(2)
        with confirm_col1:
            st.markdown('<div class="confirm-yes-button">', unsafe_allow_html=True)
            if st.button("Sim", use_container_width=True, key="confirm_yes"):
                with st.spinner("Gerando arquivo..."):
                    df_export = df.copy()
                    df_export['Processo SEI UTE'] = df_export['Processo SEI UTE'].fillna('').astype(str).str.strip()
                    df_export['Identificação'] = df_export['Identificação'].fillna('').astype(str).str.strip()
                    df_export['Descricao_formatada'] = df_export.apply(
                        lambda row: f"{row['Identificação']} - Processo SEI UTE {row['Processo SEI UTE']}" if row['Processo SEI UTE'] != '' else row['Identificação'],
                        axis=1
                    )
                    df_export['Frequência (MHz)'] = pd.to_numeric(df_export['Frequência (MHz)'], errors='coerce')
                    df_export['Frequencia_formatada'] = df_export['Frequência (MHz)'].apply(
                        lambda x: f'{x:.6f}'.replace('.', ',') if pd.notna(x) else ''
                    )
                    df_appanalise = pd.DataFrame({
                        'Frequencia': df_export['Frequencia_formatada'],
                        'Largura': df_export['Largura (kHz)'],
                        'Descricao': df_export['Descricao_formatada']
                    })
                    st.session_state.appanalise_bytes = to_excel(df_appanalise)
                st.session_state.confirm_export = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with confirm_col2:
            st.markdown('<div class="confirm-no-button">', unsafe_allow_html=True)
            if st.button("Não", use_container_width=True, key="confirm_no"):
                st.session_state.confirm_export = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
if st.session_state.appanalise_bytes:
    with placeholder_sidebar.container():
        st.download_button(
            label="📥 Baixar Arquivo para AppAnálise",
            data=st.session_state.appanalise_bytes,
            file_name=f"emissoes_appanalise_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True
        )
        st.session_state.appanalise_bytes = None

header_cols = st.columns([0.1, 0.8, 0.1])
with header_cols[0]: st.image("logo.png", width=115)
with header_cols[1]:
    titulo_formatado = f"<i>{titulo_data}</i>" if titulo_data == "Fora do período" else titulo_data
    st.markdown(f"""
    <div style='text-align: center;'>
        <h1 style='margin-bottom: -15px; margin-top: -1px;'>Monitoração do Espectro - COP30</h1>
        <span class='title-subtitle' style='font-size: 1.3rem; font-weight: normal;'>Dia do evento: {titulo_formatado} &nbsp;&nbsp;-&nbsp;&nbsp; Fiscais em atividade: {fiscais_hoje}</span>
    </div>
    """, unsafe_allow_html=True)
with header_cols[2]: st.image("anatel.png", width=105)
st.markdown("---")

if df.empty and not df_original.empty:
    st.info("Nenhum dado encontrado para a seleção atual. Por favor, ajuste os filtros na barra lateral.")
    st.stop()
elif df_original.empty:
    st.info("Nenhum dado carregado da planilha.")
    st.stop()
    
kpi_cols = st.columns(6, gap="small")
kpi_data = [
    {"label": "Emissões verificadas", "value": kpi_emissoes_verificadas, "color": "linear-gradient(135deg, #4CAF50 0%, #9CCC65 100%)", "tooltip": "Total de emissões verificadas, conforme os filtros aplicados (padrão: 'todas')."},
    {"label": "Não Licenciadas", "value": kpi_nao_licenciadas, "color": "linear-gradient(135deg, #4CAF50 0%, #9CCC65 100%)", "tooltip": "Total de emissões 'Não' licenciadas (Total de emissões não licenciadas considerando os filtros aplicados)."},
    {"label": "Verificações Pendentes", "value": total_pendentes_original, "color": f"linear-gradient(135deg, {BASE_PALETTE[4]} 0%, {VARIANT_PALETTE[4]} 100%)", "tooltip": "Total de emissões aguardando alguma identificação/verificação (não afetado por filtros)."},
    {"label": "Interferências (total)", "value": kpi_interferencias, "color": f"linear-gradient(135deg, {BASE_PALETTE[4]} 0%, {VARIANT_PALETTE[4]} 100%)", "tooltip": "Total de interferências registradas no evento (não afetado por filtros)."},
    {"label": "BSRs (Jammers)", "value": int(bsr_jammers_count), "color": f"linear-gradient(135deg, {BASE_PALETTE[4]} 0%, {VARIANT_PALETTE[4]} 100%)", "tooltip": "Contagem total de BSRs/Jammers identificados."},
    {"label": "ERBs Fake", "value": int(erbs_fake_count), "color": f"linear-gradient(135deg, {BASE_PALETTE[4]} 0%, {VARIANT_PALETTE[4]} 100%)", "tooltip": "Contagem total de ERBs Fake identificadas."}
]

for i, data in enumerate(kpi_data):
    with kpi_cols[i]:
        st.markdown(f"""
        <div class="kpi-box" style="background-image: {data['color']};">
            <div class="info-icon-container">
                <span class="info-icon">i</span><span class="tooltip-text">{data['tooltip']}</span>
            </div>
            <div class="kpi-label">{data['label']}</div><div class="kpi-value">{data['value']}</div>
        </div>""", unsafe_allow_html=True)
        
st.markdown('<div style="margin-top: 2.5rem;"></div>', unsafe_allow_html=True)

if not df.empty:
    df_com_nomes = pd.merge(df, all_estacoes_info[['Estação', 'Nome']], on='Estação', how='left')
    if 'Nome' in df_com_nomes.columns:
        df_com_nomes['Nome'].fillna('Abordagem', inplace=True)
    
    top_col1, top_col2, top_col3 = st.columns([0.3, 0.3, 0.4], gap="small")
    with top_col1:
        with st.container():
            st.markdown('<div class="style-marker"></div>', unsafe_allow_html=True)
            st.subheader("Emissões por Região")
            data_estacao = df_com_nomes['Nome'].value_counts().reset_index()
            data_estacao.columns = ['Nome', 'count']
            data_estacao['label'] = data_estacao['Nome'] + ' (' + data_estacao['count'].astype(str) + ')'
            fig_treemap_estacao = px.treemap(data_estacao, path=['label'], values='count', color='Nome', color_discrete_sequence=COP30_PALETTE)
            fig_treemap_estacao.update_layout(margin=dict(t=1, b=10, l=10, r=10), height=400, paper_bgcolor='rgba(141, 135, 121, 0.2)', plot_bgcolor='rgba(0,0,0,0)')
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
            all_estacoes_info = pd.concat([estacoes_info, miaer_info, cellpl_info], ignore_index=True)
            center_lat, center_lon = all_estacoes_info['lat'].mean(), all_estacoes_info['lon'].mean()
            estacoes_filtradas_mapa = [s for s in estacoes_lista if st.session_state.get(f'station_{s}') and s != 'Abordagem']
            default_color, selected_color = "#1A311F", "#14337b"
            all_estacoes_info['map_color'] = default_color
            if estacoes_filtradas_mapa:
                all_estacoes_info.loc[all_estacoes_info['Estação'].isin(estacoes_filtradas_mapa), 'map_color'] = selected_color
            fig_mapa = px.scatter_mapbox(all_estacoes_info, lat="lat", lon="lon", size_max=25, text="rotulo", hover_name="rotulo", zoom=10, height=424, color='map_color', color_discrete_map="identity")
            fig_mapa.update_traces(marker=dict(size=13), textfont_color='#1A311F', textposition='middle right')
            fig_mapa.update_layout(mapbox_style="carto-positron", mapbox_center={"lat": center_lat, "lon": center_lon}, margin={"r":0, "t":0, "l":0, "b":0}, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', uniformtext=dict(minsize=6, mode='show'),
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
                fig_estacao_dia.update_layout(legend_title='', margin={"r":19, "t":10, "l":0, "b":10}, paper_bgcolor='rgba(141, 135, 121, 0.2)', plot_bgcolor='rgba(0,0,0,0)', height=424, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
                st.plotly_chart(fig_estacao_dia, use_container_width=True)
            else: st.info("Nenhuma emissão com data válida na seleção.")
    st.markdown('<div class="page-break-before"></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="table-container-style"></div>', unsafe_allow_html=True)
        # AJUSTE FINAL: Coluna 'Detalhes' removida e 'Faixa de Frequência' encurtada.
        colunas_para_exibir = {
            'Data': 'Data', 
            'Nome': 'Região', 
            'Estação': 'Estação',
            'Frequência (MHz)': 'Frequência (MHz)', 
            'Largura (kHz)': 'Largura (kHz)', 
            'Faixa de Frequência Envolvida': 'Faixa', # Encurtado
            'Autorizado?': 'Autorizado?', 
            'UTE?': 'UTE?', 
            'Identificação': 'Tipo de Emissão',
            'Interferente?': 'Interferente?', 
            'Fiscal': 'Fiscal',
            'Situação': 'Situação'
        }
        colunas_existentes = [col for col in colunas_para_exibir.keys() if col in df.columns]
        if 'Fiscal' not in colunas_existentes and 'fiscal_warning' not in st.session_state:
            st.session_state.fiscal_warning = True
            st.sidebar.warning("A coluna 'Fiscal' não foi encontrada. Verifique o nome do cabeçalho.")
        if 'Largura (kHz)' not in colunas_existentes and 'largura_warning' not in st.session_state:
            st.session_state.largura_warning = True
            st.sidebar.warning("A coluna 'Largura (kHz)' (coluna G) não foi encontrada. Verifique o nome do cabeçalho.")
        df_tabela = df.loc[:, colunas_existentes].rename(columns=colunas_para_exibir)
        if 'Data' in df_tabela.columns:
            df_tabela['Data'] = pd.to_datetime(df_tabela['Data'], errors='coerce')
            df_tabela.sort_values(by='Data', ascending=False, inplace=True)
            df_tabela['Data'] = df_tabela['Data'].dt.strftime('%d/%m/%Y')
        if 'Região' in df_tabela.columns:
            df_tabela['Região'] = pd.merge(df, all_estacoes_info[['Estação', 'Nome']], on='Estação', how='left')['Nome'].fillna('Abordagem').str.title()

        df_para_exportar = df_tabela.copy()
        df_xlsx = to_excel(df_para_exportar)
        col_titulo, col_botao = st.columns([0.8, 0.2])
        with col_titulo: st.subheader("Histórico geral de identificações")
        with col_botao: 
            st.download_button(label="📥 Exportar (.xlsx)", data=df_xlsx, file_name='historico_cop30.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
        gb = GridOptionsBuilder.from_dataframe(df_tabela)
        gb.configure_default_column(flex=1, cellStyle={'text-align': 'center'}, sortable=True, filter=True, resizable=True)
        gridOptions = gb.build()
        AgGrid(df_tabela, gridOptions=gridOptions, theme='streamlit' if st.session_state.theme == 'Light' else 'alpine-dark', allow_unsafe_jscode=True, height=400, use_container_width=True)







