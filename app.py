import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

# --- FUNÇÃO MÁGICA DE LIMPEZA (ABRE AS CAIXAS TRANCADAS) ---
def formatar_valor_universal(texto):
    if not texto: return None
    # Remove aspas, quebras de linha e espaços
    t = str(texto).replace('"', '').replace('\n', '').replace('\r', '').upper().strip()
    
    # Regra do fornecedor: Débito (D) é negativo, Crédito (C) é positivo
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

# --- INTERFACE AZUL PROFISSIONAL ---
st.set_page_config(page_title="Super Robô Contábil", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #E3F2FD !important; }
    h1, h2, h3 { color: #1565C0 !important; }
    .stSelectbox label { color: #000; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Super Robô Multi-Bancos v16")

# Lista de Bancos conforme sua necessidade
lista_bancos = [
    "Caixa Econômica", "Santander", "Itaú", "Sicredi", "Sicoob", 
    "Mercado Pago", "Banco Inter", "XP Investimentos", "PagSeguro", "Banco do Brasil"
]

c1, c2 = st.columns([1, 2])
with c1:
    banco_alvo = st.selectbox("Selecione o Banco:", lista_bancos)
with c2:
    arquivo_pdf = st.file_uploader(f"Suba o PDF do {banco_alvo}", type=["pdf"])

if arquivo_pdf:
    dados_final = []
    # Regex para data (00/00/0000)
    regex_data = r'(\d{2}/\d{2}/\d{4})'

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            # Extração bruta de texto
            texto_bruto = pagina.extract_text()
            if not texto_bruto: continue
            
            # --- TRATAMENTO ESPECIAL CAIXA ---
            if banco_alvo == "Caixa Econômica":
                # O PDF da Caixa é um "CSV disfarçado". Vamos limpar as aspas antes de tudo.
                linhas = texto_bruto.split('\n')
                for linha in linhas:
                    # Se a linha tem data, ela é um lançamento
                    if re.search(regex_data, linha):
                        # Divide a linha por "," mas ignora as aspas
                        partes = [p.replace('"', '').strip() for p in linha.split('","')]
                        
                        if len(partes) >= 3:
                            data_f = re.search(regex_data, partes[0]).group(1)
                            # No seu arquivo, o histórico é a 3ª parte (índice 2)
                            historico = partes[2].replace('\n', ' ').strip().upper()
                            
                            # O valor costuma ser a 6ª parte (índice 5)
                            valor_raw = partes[5] if len(partes) > 5 else ""
                            
                            # Se não achou o valor na coluna 5, caça o "C" ou "D" na linha toda
                            if 'C' not in valor_raw and 'D' not in valor_raw:
                                busca_v = re.findall(r'(\d+[\d.,]*\s?[CD])', linha)
                                if busca_v: valor_raw = busca_v[0]

                            v_num = formatar_valor_universal(valor_raw)
                            
                            if v_num is not None and v_num != 0 and "SALDO" not in historico:
                                dados_final.append({'Data': data_f, 'Histórico': historico, 'Valor': v_num})

            # --- TRATAMENTO PARA OUTROS BANCOS ---
            else:
                for linha in texto_bruto.split('\n'):
                    match_data = re.search(regex_data, linha)
                    if match_data:
                        data_f = match_data.group(1)
                        # Remove a data e pega o que sobrou
                        corpo = linha.replace(data_f, "").strip()
                        partes = corpo.split()
                        if len(partes) >= 2:
                            valor_bruto = partes[-1]
                            historico = " ".join(partes[:-1]).strip().upper()
                            if historico.endswith("-"): historico = historico[:-1].strip()
                            
                            v_num = formatar_valor_universal(valor_bruto)
                            if v_num is not None and v_num != 0:
                                dados_final.append({'Data': data_f, 'Histórico': historico, 'Valor': v_num})

    if dados_final:
        df = pd.DataFrame(dados_final)
        st.success(f"✅ Sucesso! Lidos {len(df)} lançamentos do {banco_alvo}.")
        st.dataframe(df, use_container_width=True)

        # GERAÇÃO DO EXCEL (MESMO PADRÃO QUE VOCÊ USA)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, startrow=3, startcol=1, sheet_name='Extrato')
            workbook = writer.book
            worksheet = writer.sheets['Extrato']
            
            # FORMATOS
            fmt_cabecalho = workbook.add_format({'bold': True, 'bg_color': '#1565C0', 'font_color': 'white', 'border': 1, 'align': 'center'})
            fmt_data = workbook.add_format({'border': 1, 'align': 'center'})
            fmt_grade = workbook.add_format({'border': 1})
            fmt_verde = workbook.add_format({'font_color': '#008000', 'num_format': '#,##0.00', 'border': 1})
            fmt_vermelho = workbook.add_format({'font_color': '#FF0000', 'num_format': '#,##0.00', 'border': 1})

            # AJUSTE DE COLUNAS
            worksheet.set_column('B:B', 12) # Data
            worksheet.set_column('C:C', 45) # Histórico
            worksheet.set_column('D:D', 15) # Valor
            worksheet.set_column('E:H', 25) # Extra

            # CABEÇALHO PERSONALIZADO
            titulos = ["Data", "Histórico", "Valor", "Débito", "Crédito", "Complemento", "Descrição"]
            for col_num, titulo in enumerate(titulos):
                worksheet.write(3, col_num + 1, titulo, fmt_cabecalho)

            # PREENCHIMENTO
            for i, row in df.iterrows():
                r = i + 4
                worksheet.write(r, 1, row['Data'], fmt_data)
                worksheet.write(r, 2, row['Histórico'], fmt_grade)
                v = row['Valor']
                worksheet.write_number(r, 3, v, fmt_vermelho if v < 0 else fmt_verde)
                for c in range(4, 8): worksheet.write(r, c, "", fmt_grade)

        st.download_button(f"📥 Baixar Planilha {banco_alvo}", output.getvalue(), f"Extrato_{banco_alvo}.xlsx")
    else:
        st.error("Ops! Não conseguimos ler os valores. Verifique se escolheu o banco certo no menu.")
