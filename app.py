import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def processar_valor_unico(texto_valor):
    if not texto_valor: return None
    t = str(texto_valor).upper().replace(" ", "").replace("R$", "")
    e_saida = '-' in t or 'D' in t
    apenas_numeros = re.sub(r'[^\d,]', '', t)
    try:
        valor_float = float(apenas_numeros.replace(',', '.'))
        return -valor_float if e_saida else valor_float
    except:
        return None

# --- CSS PARA DEIXAR TUDO AZUL (INCLUINDO CABEÇALHO) ---
st.set_page_config(page_title="Robô de Extratos", layout="centered")

st.markdown("""
    <style>
    /* Fundo principal da aplicação */
    .stApp {
        background-color: #E3F2FD !important;
    }
    /* Cor do cabeçalho (Header) do Streamlit */
    header[data-testid="stHeader"] {
        background-color: #E3F2FD !important;
    }
    /* Estilização dos campos de entrada para não quebrarem o visual */
    .stTextInput>div>div>input {
        background-color: #FFFFFF !important;
        border: 1px solid #1565C0;
    }
    /* Título em azul escuro para contraste */
    h1 {
        color: #1565C0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Conversor de Extrato Bancário")

col_emp, col_ban = st.columns(2)
nome_empresa = col_emp.text_input("Empresa", "Minha Empresa")
nome_banco = col_ban.text_input("Banco", "Banco")

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
        # O segredo para remover a Sheet1 é criar o Writer e já definir a aba Extrato no primeiro comando
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Forçamos a escrita na aba Extrato. O XlsxWriter não criará a Sheet1 se fizermos assim:
            df.to_excel(writer, index=False, startrow=3, startcol=1, sheet_name='Extrato')
            
            workbook = writer.book
            worksheet = writer.sheets['Extrato']
            
            # Formatos
            fmt_negrito = workbook.add_format({'bold': True, 'border': 1})
            fmt_grade = workbook.add_format({'border': 1})
            fmt_verde = workbook.add_format({'font_color': '#008000', 'num_format': '#,##0.00', 'border': 1})
            fmt_vermelho = workbook.add_format({'font_color': '#FF0000', 'num_format': '#,##0.00', 'border': 1})
            fmt_cabecalho = workbook.add_format({'bold': True, 'bg_color': '#EAEAEA', 'border': 1})

            # Layout Excel
            worksheet.set_column('A:A', 2) 
            worksheet.write('B1', f"EMPRESA: {nome_empresa}", fmt_negrito)
            worksheet.write('B2', f"BANCO: {nome_banco}", fmt_negrito)
            worksheet.hide_gridlines(2)

            worksheet.set_column('B:B', 12)
            worksheet.set_column('C:C', 45)
            worksheet.set_column('D:D', 15)
            worksheet.set_column('E:H', 15)

            titulos = ["Data", "Histórico", "Valor", "Débito", "Crédito", "Complemento", "Descrição"]
            for col_num, titulo in enumerate(titulos):
                worksheet.write(3, col_num + 1, titulo, fmt_cabecalho)

            # Preenchimento de dados
            for i, row in df.iterrows():
                row_idx = i + 4
                worksheet.write(row_idx, 1, row['Data'], fmt_grade)
                worksheet.write(row_idx, 2, row['Histórico'], fmt_grade)
                v = row['Valor']
                worksheet.write_number(row_idx, 3, v, fmt_vermelho if v < 0 else fmt_verde)
                for c in range(4, 8): worksheet.write(row_idx, c, "", fmt_grade)

        st.download_button(
            label="📥 Baixar Planilha Final",
            data=output.getvalue(),
            file_name=f"Extrato_{nome_banco}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )        
