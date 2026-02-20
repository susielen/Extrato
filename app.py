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

# --- Interface Streamlit ---
st.set_page_config(page_title="Robô de Extratos", layout="centered")
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
                                'Data': data_str,
                                'Histórico': historico,
                                'Valor': valor_final,
                                'Débito': "",
                                'Crédito': "",
                                'Complemento': "",
                                'Descrição': ""
                            })

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        st.divider()
        st.write("### ✅ Processamento concluído")
        st.dataframe(df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Escrevemos os dados começando na coluna B (índice 1)
            df.to_excel(writer, index=False, startrow=3, startcol=1, sheet_name='Extrato')
            
            workbook = writer.book
            worksheet = writer.sheets['Extrato']
            
            # --- Formatos ---
            fmt_negrito = workbook.add_format({'bold': True, 'border': 1})
            fmt_grade = workbook.add_format({'border': 1})
            fmt_verde = workbook.add_format({'font_color': '#008000', 'num_format': '#,##0.00', 'border': 1})
            fmt_vermelho = workbook.add_format({'font_color': '#FF0000', 'num_format': '#,##0.00', 'border': 1})
            fmt_cabecalho = workbook.add_format({'bold': True, 'bg_color': '#EAEAEA', 'border': 1})

            # 1. Margem: Coluna A bem estreita e vazia
            worksheet.set_column('A:A', 2) 
            
            # 2. Títulos (agora na coluna B)
            worksheet.write('B1', f"EMPRESA: {nome_empresa}", fmt_negrito)
            worksheet.write('B2', f"BANCO: {nome_banco}", fmt_negrito)

            # 3. Esconder grades de fundo
            worksheet.hide_gridlines(2)

            # 4. Ajuste de Colunas (B em diante)
            worksheet.set_column('B:B', 12) # Data
            worksheet.set_column('C:C', 45) # Histórico
            worksheet.set_column('D:D', 15) # Valor
            worksheet.set_column('E:H', 15) # Extras

            # 5. Formatar cabeçalho da tabela manualmente na linha 4 (índice 3), coluna B (índice 1)
            colunas = ["Data", "Histórico", "Valor", "Débito", "Crédito", "Complemento", "Descrição"]
            for col_num, titulo in enumerate(colunas):
                worksheet.write(3, col_num + 1, titulo, fmt_cabecalho)

            # 6. Preencher dados com bordas e cores
            for i, row in df.iterrows():
                row_idx = i + 4
                worksheet.write(row_idx, 1, row['Data'], fmt_grade)
                worksheet.write(row_idx, 2, row['Histórico'], fmt_grade)
                
                valor = row['Valor']
                fmt_v = fmt_vermelho if valor < 0 else fmt_verde
                worksheet.write_number(row_idx, 3, valor, fmt_v)
                
                # Colunas vazias com grade
                for col_extra in range(4, 8):
                    worksheet.write(row_idx, col_extra, "", fmt_grade)

        st.download_button(
            label="📥 Baixar Planilha Final com Margem",
            data=output.getvalue(),
            file_name=f"Extrato_{nome_empresa}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
