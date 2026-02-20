import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

# --- FUNÇÕES DE LIMPEZA ---
def limpar_valor(texto, banco):
    if not texto: return None
    t = str(texto).upper().replace('"', '').replace('R$', '').replace(' ', '').strip()
    
    # Regra que você me ensinou: Para o fornecedor Credito (+) e Debito (-)
    # Alguns bancos usam 'D', outros o sinal '-'
    e_saida = 'D' in t or '-' in t
    
    # Mantém apenas números e a vírgula/ponto
    num = re.sub(r'[^\d,.]', '', t)
    try:
        if ',' in num and '.' in num: num = num.replace('.', '').replace(',', '.')
        elif ',' in num: num = num.replace(',', '.')
        res = float(num)
        return -res if e_saida else res
    except:
        return None

# --- CONFIGURAÇÃO DA TELA (TUDO AZUL) ---
st.set_page_config(page_title="Robô Contábil Multi-Bancos", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #E3F2FD !important; }
    h1, h2, h3 { color: #1565C0 !important; }
    .stSelectbox label { color: #1565C0 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Robô de Extratos Inteligente")

# --- MENU DE SELEÇÃO DE BANCO ---
lista_bancos = [
    "Santander", "Caixa Econômica", "Itaú", "Sicredi", "Sicoob", 
    "Mercado Pago", "Banco Inter", "XP Investimentos", "PagSeguro", "Banco do Brasil"
]

col1, col2 = st.columns([1, 2])
with col1:
    banco_selecionado = st.selectbox("Para qual banco vamos converter agora?", lista_bancos)
with col2:
    arquivo_pdf = st.file_uploader(f"Arraste o PDF do {banco_selecionado} aqui", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    # Padrão de data comum (DD/MM/AAAA ou DD/MM)
    regex_data = r'(\d{2}/\d{2}(?:/\d{2,4})?)'

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto_bruto = pagina.extract_text()
            if not texto_bruto: continue
            
            # --- LÓGICA POR BANCO ---
            linhas = texto_bruto.split('\n')
            
            for linha in linhas:
                match_data = re.search(regex_data, linha)
                if match_data:
                    data_f = match_data.group(1)
                    
                    # 1. LÓGICA CAIXA (ASPAS E VÍRGULAS)
                    if banco_selecionado == "Caixa Econômica":
                        partes = [p.replace('"', '').strip() for p in linha.split(',')]
                        if len(partes) >= 5:
                            historico = partes[2].upper()
                            valor_bruto = ""
                            for p in reversed(partes):
                                if 'C' in p.upper() or 'D' in p.upper():
                                    valor_bruto = p; break
                            v_final = limpar_valor(valor_bruto, "Caixa")
                        else: continue

                    # 2. LÓGICA ITAÚ / SANTANDER / BB / INTER (TEXTO EM COLUNAS)
                    else:
                        resto = linha.replace(data_f, "").strip()
                        partes = resto.split()
                        if len(partes) >= 2:
                            valor_bruto = partes[-1]
                            historico = " ".join(partes[:-1]).strip().upper()
                            # Remove hifens de fechamento comuns no Santander
                            if historico.endswith("-"): historico = historico[:-1].strip()
                            v_final = limpar_valor(valor_bruto, banco_selecionado)
                        else: continue

                    # Filtro de segurança: ignora SALDO e valores zerados
                    if v_final is not None and v_final != 0 and "SALDO" not in str(historico):
                        dados_lista.append({
                            'Data': data_f,
                            'Histórico': historico,
                            'Valor': v_final,
                            'Débito': "", 'Crédito': "", 'Complemento': "", 'Descrição': ""
                        })

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        st.success(f"✅ {len(df)} lançamentos do {banco_selecionado} processados!")
        st.dataframe(df, use_container_width=True)

        # --- EXPORTAÇÃO EXCEL ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, startrow=3, startcol=1, sheet_name='Extrato')
            workbook = writer.book
            worksheet = writer.sheets['Extrato']
            
            # Formatos
            fmt_data = workbook.add_format({'border': 1, 'align': 'center'})
            fmt_grade = workbook.add_format({'border': 1})
            fmt_verde = workbook.add_format({'font_color': '#008000', 'num_format': '#,##0.00', 'border': 1})
            fmt_vermelho = workbook.add_format({'font_color': '#FF0000', 'num_format': '#,##0.00', 'border': 1})
            fmt_cabecalho = workbook.add_format({'bold': True, 'bg_color': '#1565C0', 'font_color': 'white', 'border': 1, 'align': 'center'})

            # Cabeçalho
            worksheet.merge_range('B2:D2', f"EXTRATO: {banco_selecionado.upper()}", fmt_cabecalho)
            worksheet.set_column('B:B', 12) # Data
            worksheet.set_column('C:C', 45) # Histórico
            worksheet.set_column('D:D', 15) # Valor
            worksheet.set_column('E:H', 25) # Colunas do Escritório

            # Títulos das Colunas
            tits = ["Data", "Histórico", "Valor", "Débito", "Crédito", "Complemento", "Descrição"]
            for col_num, titulo in enumerate(tits):
                worksheet.write(3, col_num + 1, titulo, fmt_cabecalho)

            # Escrevendo os dados
            for i, row in df.iterrows():
                r = i + 4
                worksheet.write(r, 1, row['Data'], fmt_data)
                worksheet.write(r, 2, row['Histórico'], fmt_grade)
                v = row['Valor']
                worksheet.write_number(r, 3, v, fmt_vermelho if v < 0 else fmt_verde)
                for c in range(4, 8): worksheet.write(r, c, "", fmt_grade)

        st.download_button(
            label=f"📥 Baixar Planilha do {banco_selecionado}",
            data=output.getvalue(),
            file_name=f"Extrato_{banco_selecionado}.xlsx"
        )
