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
st.set_page_config(page_title="Robô de Extratos", layout="centered")

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
                        
                        # Limpeza do histórico
                        historico = " ".join(partes[:-1]).strip()
                        if historico.endswith("-"):
                            historico = historico[:-1].strip()
                        historico = historico.upper()
                        
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
            fmt_data = workbook.add_format({'border': 1, 'align': 'center'})
            fmt_verde = workbook.add_format({'font_color': '#008000', 'num_format': '#,##0.00', 'border': 1})
            fmt_vermelho = workbook.add_format({'font_color': '#FF0000', 'num_format': '#,##0.00', 'border': 1})
            fmt_cabecalho = workbook.add_format({
                'bold': True, 'bg_color': '#EAEAEA', 'border': 1,
                'font_color': '#000000', 'align': 'center', 'valign': 'vcenter'
            })

            # 1. Margens e Título do Banco
            worksheet.set_row(0, 15)       
            worksheet.set_column('A:A', 2) 
            worksheet.hide_gridlines(2)
            worksheet.merge_range('B2:C2', f"BANCO: {nome_banco}", fmt_cabecalho)

            # 2. Ajuste de Colunas
            worksheet.set_column('B:B', 12) 
            worksheet.set_column('C:C', 45) 
            worksheet.set_column('D:D', 15) 
            worksheet.set_column('E:H', 25) 

            # 3. Cabeçalho com Notas
            titulos = ["Data", "Histórico", "Valor", "Débito", "Crédito", "Complemento", "Descrição"]
            for col_num, titulo in enumerate(titulos):
                col_idx = col_num + 1
                worksheet.write(3, col_idx, titulo, fmt_cabecalho)
                
                if titulo == "Débito" or titulo == "Crédito":
                    worksheet.write_comment(3, col_idx, 'Escritório, coloque aqui o código reduzido do plano de contas que você utiliza no seu sistema.')
                elif titulo == "Complemento":
                    worksheet.write_comment(3, col_idx, 'Coloque aqui o início do seu histórico ou um histórico padrão. Por exemplo: PAGAMENTO DE OU RECEBIMENTO DE')
                elif titulo == "Descrição":
                    worksheet.write_comment(3, col_idx, 'Coloque aqui a seguinte fórmula: =CONCAT(selecione_complemento; selecione_historico) e depois arraste para as celulas abaixo')

            # 4. Dados (Descrição Vazia com Grade)
            for i, row in df.iterrows():
                row_idx = i + 4
                worksheet.write(row_idx, 1, row['Data'], fmt_data)
                worksheet.write(row_idx, 2, row['Histórico'], fmt_grade)
                
                v = row['Valor']
                fmt_v = fmt_vermelho if v < 0 else fmt_verde
                worksheet.write_number(row_idx, 3, v, fmt_v)
                
                # Colunas de E até H (Débito, Crédito, Complemento, Descrição) vazias com grade
                for col_extra in range(4, 8):
                    worksheet.write(row_idx, col_extra, "", fmt_grade)

        st.download_button(
            label="📥 Baixar Planilha Final",
            data=output.getvalue(),
            file_name=f"Extrato_{nome_banco}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
