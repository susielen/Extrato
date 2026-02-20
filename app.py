import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def processar_valor_unico(texto_valor):
    if not texto_valor: return None
    t = str(texto_valor).upper().replace(" ", "").replace("R$", "")
    # Regra: Débito (-) e Crédito (+)
    e_saida = '-' in t or 'D' in t
    apenas_numeros = re.sub(r'[^\d,]', '', t)
    try:
        valor_float = float(apenas_numeros.replace(',', '.'))
        return -valor_float if e_saida else valor_float
    except:
        return None

# --- CSS PARA AZUL TOTAL NO STREAMLIT ---
st.set_page_config(page_title="🧾Extratos", page_icon="📇", layout="centered")

st.markdown("""
    <style>
    .stApp, header[data-testid="stHeader"], [data-testid="stToolbar"] {
        background-color: #E3F2FD !important;
    }
    .stTextInput>div>div>input {
        background-color: #FFFFFF !important;
        border: 1px solid #1565C0;
    }
    h1 { color: #1565C0 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Conversor de Extrato Bancário")

nome_banco = st.text_input("Nome do Banco", "Banco Santander")

arquivo_pdf = st.file_uploader("Selecione o arquivo PDF", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if not texto: continue
            for linha in texto.split('\n'):
                match_data = re.search(r'^(\d{2}/\d{2}(?:/\d{4})?)', linha.strip())
                if match_data:
                    data_str = match_data.group(1)
                    resto = linha.replace(data_str, "").strip()
                    partes = resto.split()
                    if len(partes) >= 2:
                        valor_bruto = partes[-1]
                        historico = " ".join(partes[:-1])
                        valor_final = processar_valor_unico(valor_bruto)
                        if valor_final is not None:
                            dados_lista.append({
                                'Data': data_str, 'Histórico': historico, 'Valor': valor_final,
                                'Débito': "", 'Crédito': "", 'Complemento': "", 'Descrição': ""
                            })

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        st.divider()
        st.dataframe(df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, startrow=3, startcol=1, sheet_name='Extrato')
            
            workbook = writer.book
            worksheet = writer.sheets['Extrato']
            
            # --- FORMATOS ---
            fmt_grade = workbook.add_format({'border': 1})
            fmt_verde = workbook.add_format({'font_color': '#008000', 'num_format': '#,##0.00', 'border': 1})
            fmt_vermelho = workbook.add_format({'font_color': '#FF0000', 'num_format': '#,##0.00', 'border': 1})
            
            # Formato para os Títulos da Tabela
            fmt_cabecalho = workbook.add_format({
                'bold': True, 
                'bg_color': '#EAEAEA', 
                'border': 1,
                'font_color': '#000000',
                'align': 'center',
                'valign': 'vcenter'
            })

            # Formato específico para o Banco (B e C mesclados e centralizados)
            fmt_banco_titulo = workbook.add_format({
                'bold': True, 
                'bg_color': '#EAEAEA', 
                'border': 1,
                'font_color': '#000000',
                'align': 'center',   # Centraliza horizontalmente
                'valign': 'vcenter'  # Centraliza verticalmente
            })

            # 1. Margens
            worksheet.set_row(0, 15)       
            worksheet.set_column('A:A', 2) 
            worksheet.hide_gridlines(2)

            # 2. Título do Banco (Mesclado apenas em B2:C2 e Centralizado)
            worksheet.merge_range('B2:C2', f"BANCO: {nome_banco}", fmt_banco_titulo)

            # 3. Ajuste de Colunas
            worksheet.set_column('B:B', 12)
            worksheet.set_column('C:C', 45)
            worksheet.set_column('D:D', 15)
            worksheet.set_column('E:H', 15)

            # 4. Cabeçalho da Tabela
            titulos = ["Data", "Histórico", "Valor", "Débito", "Crédito", "Complemento", "Descrição"]
            for col_num, titulo in enumerate(titulos):
                worksheet.write(3, col_num + 1, titulo, fmt_cabecalho)

            # 5. Dados
            for i, row in df.iterrows():
                row_idx = i + 4
                worksheet.write(row_idx, 1, row['Data'], fmt_grade)
                worksheet.write(row_idx, 2, row['Histórico'], fmt_grade)
                v = row['Valor']
                worksheet.write_number(row_idx, 3, v, fmt_vermelho if v < 0 else fmt_verde)
                for c in range(4, 8): 
                    worksheet.write(row_idx, c, "", fmt_grade)

        st.download_button(
            label="📥 Baixar Planilha Final",
            data=output.getvalue(),
            file_name=f"Extrato_{nome_banco}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
