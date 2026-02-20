import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def processar_valor_universal(texto_valor):
    if not texto_valor: return None, None
    t = str(texto_valor).upper().replace(" ", "").replace("R$", "")
    e_debito = '-' in t or 'D' in t
    apenas_numeros = re.sub(r'[^\d,]', '', t)
    try:
        valor_float = float(apenas_numeros.replace(',', '.'))
        return valor_float, "DEBITO" if e_debito else "CREDITO"
    except:
        return None, None

# --- Interface Streamlit ---
st.set_page_config(page_title="Conversor de Extrato", layout="centered")
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
                        valor, tipo = processar_valor_universal(valor_bruto)
                        if valor is not None:
                            dados_lista.append({
                                'Data_Obj': pd.to_datetime(data_str, dayfirst=True, errors='coerce'),
                                'Data': data_str,
                                'Histórico': historico,
                                'Débito': valor if tipo == "DEBITO" else None,
                                'Crédito': valor if tipo == "CREDITO" else None
                            })

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        df = df.sort_values('Data_Obj').drop(columns=['Data_Obj'])
        
        # Adicionando colunas extras vazias
        df['Conta Débito'] = ""
        df['Conta Crédito'] = ""
        df['Descrição'] = "" # Será preenchido com fórmula no Excel

        st.divider()
        st.write("### Prévia do Extrato")
        st.dataframe(df, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame([[f"EMPRESA: {nome_empresa}"], [f"BANCO: {nome_banco}"]]).to_excel(writer, index=False, header=False, startrow=0)
            
            # Os dados começam na linha 4 (índice 3 do Excel)
            df.to_excel(writer, index=False, startrow=3, sheet_name='Extrato')
            
            workbook = writer.book
            worksheet = writer.sheets['Extrato']
            fmt_moeda = workbook.add_format({'num_format': '#,##0.00'})
            
            # Ajuste de colunas: Data(A), Histórico(B), Débito(C), Crédito(D), Conta Débito(E), Conta Crédito(F), Descrição(G)
            worksheet.set_column('C:D', 15, fmt_moeda)
            worksheet.set_column('B:B', 40)
            worksheet.set_column('E:G', 20)

            # Inserindo a fórmula CONCAT na coluna Descrição (Coluna G)
            # Como o cabeçalho está na linha 4, os dados começam na linha 5
            for i in range(len(df)):
                row_num = i + 5 # Ajuste para linha do Excel
                # Fórmula ex: =CONCAT(B5;C5;D5)
                formula = f'=CONCAT(B{row_num},C{row_num},D{row_num})'
                worksheet.write_formula(f'G{row_num}', formula)

        st.download_button(
            label="📥 Baixar Planilha Excel com Fórmulas",
            data=output.getvalue(),
            file_name=f"Extrato_{nome_empresa}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("Nenhum dado encontrado.")
