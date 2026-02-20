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
                                'Descrição': ""
                            })

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        st.divider()
        st.write("### Prévia dos Dados")
        st.dataframe(df)

        output = io.BytesIO()
        # Criando o Excel do zero com apenas UMA aba
        workbook = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Escreve os dados na aba 'Extrato'
            df.to_excel(writer, index=False, startrow=3, sheet_name='Extrato')
            
            workbook = writer.book
            worksheet = writer.sheets['Extrato']
            
            # Formatos específicos
            fmt_verde = workbook.add_format({'font_color': '#008000', 'num_format': '#,##0.00'})
            fmt_vermelho = workbook.add_format({'font_color': '#FF0000', 'num_format': '#,##0.00'})
            fmt_texto = workbook.add_format()

            # Escreve o cabeçalho manualmente na aba 'Extrato'
            worksheet.write('A1', f"EMPRESA: {nome_empresa}")
            worksheet.write('A2', f"BANCO: {nome_banco}")

            # Ajuste de Colunas
            worksheet.set_column('B:B', 45) # Histórico
            worksheet.set_column('C:C', 15) # Valor
            worksheet.set_column('D:F', 15) # Extras

            # Processando linha por linha para Cores e Fórmulas
            for i, row in df.iterrows():
                row_idx = i + 4 # Começa na linha 5 do Excel (índice 4)
                
                # 1. Pinta o valor (Verde ou Vermelho) SEM cor de fundo
                valor = row['Valor']
                formato = fmt_vermelho if valor < 0 else fmt_verde
                worksheet.write_number(row_idx, 2, valor, formato) # Coluna C (índice 2)

                # 2. Escreve a fórmula na coluna F (índice 5) SEM o @
                # O segredo é usar write_formula diretamente
                formula = f'=CONCAT(B{row_idx + 1})'
                worksheet.write_formula(row_idx, 5, formula)

        st.download_button(
            label="📥 Baixar Excel Corrigido",
            data=output.getvalue(),
            file_name=f"Extrato_{nome_empresa}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
