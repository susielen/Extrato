import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def processar_valor_unico(texto_valor):
    if not texto_valor: return None
    # Limpa aspas e espaços que a Caixa coloca
    t = str(texto_valor).upper().replace('"', '').replace(" ", "").replace("R$", "")
    # Regra: para o fornecedor credito é positivo (+) e debito é negativo (-)
    e_saida = '-' in t or 'D' in t
    apenas_numeros = re.sub(r'[^\d,]', '', t)
    try:
        valor_float = float(apenas_numeros.replace(',', '.'))
        return -valor_float if e_saida else valor_float
    except:
        return None

# --- CONFIGURAÇÃO E CSS ---
st.set_page_config(page_title="Robô de Extratos", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #E3F2FD !important; }
    h1 { color: #1565C0 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Conversor de Extrato Bancário")
nome_banco = st.text_input("Nome do Banco", "Caixa / Santander")
arquivo_pdf = st.file_uploader("Selecione o arquivo PDF", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    # Regex para data: aceita 02/06/2025 ou 02/06/25
    regex_data = r'(\d{2}/\d{2}(?:/\d{2,4})?)'

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if not texto: continue
            
            # Limpeza especial: remove as aspas e organiza as quebras de linha
            texto_limpo = texto.replace('"', '')
            linhas = texto_limpo.split('\n')
            
            for linha in linhas:
                match_data = re.search(regex_data, linha.strip())
                if match_data:
                    data_str = match_data.group(1)
                    
                    # Se tiver vírgulas (padrão Caixa), dividimos por elas
                    if ',' in linha and len(linha.split(',')) > 3:
                        partes = [p.strip() for p in linha.split(',')]
                        historico = partes[2].upper() if len(partes) > 2 else "HISTORICO NAO ENCONTRADO"
                        # O valor na Caixa geralmente é o penúltimo ou último campo com C/D
                        valor_bruto = ""
                        for p in reversed(partes):
                            if 'C' in p.upper() or 'D' in p.upper():
                                valor_bruto = p
                                break
                    else:
                        # Padrão Santander (espaços)
                        resto = linha.replace(data_str, "").strip()
                        partes = resto.split()
                        if len(partes) >= 2:
                            valor_bruto = partes[-1]
                            historico = " ".join(partes[:-1]).strip().upper()
                            if historico.endswith("-"): historico = historico[:-1].strip()
                        else: continue

                    valor_final = processar_valor_unico(valor_bruto)
                    
                    # Filtra SALDO DIA e valores zerados
                    if valor_final is not None and valor_final != 0 and "SALDO" not in str(historico):
                        dados_lista.append({
                            'Data': data_str, 
                            'Histórico': historico, 
                            'Valor': valor_final,
                            'Débito': "", 'Crédito': "", 'Complemento': "", 'Descrição': ""
                        })

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        st.divider()
        st.dataframe(df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, startrow=3, startcol=1, sheet_name='Extrato')
            workbook, worksheet = writer.book, writer.sheets['Extrato']
            
            # FORMATOS
            fmt_grade = workbook.add_format({'border': 1})
            fmt_data = workbook.add_format({'border': 1, 'align': 'center'})
            fmt_verde = workbook.add_format({'font_color': '#008000', 'num_format': '#,##0.00', 'border': 1})
            fmt_vermelho = workbook.add_format({'font_color': '#FF0000', 'num_format': '#,##0.00', 'border': 1})
            fmt_cabecalho = workbook.add_format({'bold': True, 'bg_color': '#EAEAEA', 'border': 1, 'align': 'center'})

            worksheet.hide_gridlines(2)
            worksheet.merge_range('B2:C2', f"BANCO: {nome_banco}", fmt_cabecalho)
            worksheet.set_column('B:B', 12) 
            worksheet.set_column('C:C', 45) 
            worksheet.set_column('D:D', 15) 
            worksheet.set_column('E:H', 25) 

            titulos = ["Data", "Histórico", "Valor", "Débito", "Crédito", "Complemento", "Descrição"]
            for col_num, titulo in enumerate(titulos):
                col_idx = col_num + 1
                worksheet.write(3, col_idx, titulo, fmt_cabecalho)

            for i, row in df.iterrows():
                row_idx = i + 4
                worksheet.write(row_idx, 1, row['Data'], fmt_data)
                worksheet.write(row_idx, 2, row['Histórico'], fmt_grade)
                v = row['Valor']
                worksheet.write_number(row_idx, 3, v, fmt_vermelho if v < 0 else fmt_verde)
                for col_extra in range(4, 8):
                    worksheet.write(row_idx, col_extra, "", fmt_grade)

        st.download_button(label="📥 Baixar Planilha Final", data=output.getvalue(), file_name=f"Extrato_{nome_banco}.xlsx")
