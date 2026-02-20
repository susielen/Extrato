import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def limpar_geral(texto):
    if not texto: return ""
    # Remove aspas, quebras de linha (\n, \r) e espaços extras
    return str(texto).replace('"', '').replace('\n', '').replace('\r', '').strip()

def converter_valor_caixa(valor_texto):
    t = limpar_geral(valor_texto).upper()
    if not t or t == "0,00 C" or t == "0,00 D": return 0.0
    
    # Regra do fornecedor: D é saída (-), C é entrada (+)
    saida = 'D' in t or '-' in t
    
    # Mantém só números e separadores
    num = re.sub(r'[^\d,.]', '', t)
    try:
        if ',' in num and '.' in num: num = num.replace('.', '').replace(',', '.')
        elif ',' in num: num = num.replace(',', '.')
        res = float(num)
        return -res if saida else res
    except:
        return None

# --- INTERFACE ---
st.set_page_config(page_title="Robô de Extratos Profissional", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #E3F2FD !important; }
    h1 { color: #1565C0 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Conversor de Extrato (Versão Corrigida)")

nome_banco = st.text_input("Nome do Banco", "Caixa Econômica")
arquivo_pdf = st.file_uploader("Selecione o PDF", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    # Regex para pegar a data no formato DD/MM/AAAA
    regex_data = r'(\d{2}/\d{2}/\d{4})'

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto_bruto = pagina.extract_text()
            if not texto_bruto: continue
            
            # Divide o texto por aspas seguidas de vírgula para isolar os campos
            linhas = texto_bruto.split('\n')
            for linha in linhas:
                # Verifica se a linha tem uma data
                match_data = re.search(regex_data, linha)
                if match_data:
                    data_f = match_data.group(1)
                    
                    # Divide a linha pelas aspas e vírgulas: ","
                    partes = linha.split('","')
                    
                    if len(partes) >= 5:
                        # Histórico costuma ser a 3ª parte (índice 2)
                        historico = limpar_geral(partes[2]).upper()
                        
                        # O Valor no seu arquivo da Caixa está na penúltima posição
                        # Vamos varrer as partes de trás para frente procurando o 'C' ou 'D'
                        valor_bruto = ""
                        for p in reversed(partes):
                            limpo = limpar_geral(p)
                            if ' C' in limpo or ' D' in limpo:
                                valor_bruto = limpo
                                break
                        
                        v_final = converter_valor_caixa(valor_bruto)
                        
                        # Filtra SALDO DIA e valores zerados
                        if v_final is not None and v_final != 0 and "SALDO" not in historico:
                            dados_lista.append({
                                'Data': data_f,
                                'Histórico': historico,
                                'Valor': v_final
                            })

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        st.success(f"Encontramos {len(df)} lançamentos!")
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

            # DESIGN
            worksheet.hide_gridlines(2)
            worksheet.merge_range('B2:C2', f"BANCO: {nome_banco}", fmt_cabecalho)
            worksheet.set_column('B:B', 12)
            worksheet.set_column('C:C', 45)
            worksheet.set_column('D:D', 15)
            worksheet.set_column('E:H', 25)

            # NOTAS
            prop = {'width': 280, 'height': 80}
            titulos = ["Data", "Histórico", "Valor", "Débito", "Crédito", "Complemento", "Descrição"]
            for col_num, titulo in enumerate(titulos):
                col_idx = col_num + 1
                worksheet.write(3, col_idx, titulo, fmt_cabecalho)
                if titulo in ["Débito", "Crédito"]:
                    worksheet.write_comment(3, col_idx, 'Código reduzido do plano de contas.', prop)
                elif titulo == "Complemento":
                    worksheet.write_comment(3, col_idx, 'DICA: Use MAIÚSCULAS.', prop)
                elif titulo == "Descrição":
                    worksheet.write_comment(3, col_idx, 'Fórmula: =MAIÚSCULA(CONCAT(G4; " "; C4))', prop)

            for i, row in df.iterrows():
                r = i + 4
                worksheet.write(r, 1, row['Data'], fmt_data)
                worksheet.write(r, 2, row['Histórico'], fmt_grade)
                v = row['Valor']
                worksheet.write_number(r, 3, v, fmt_vermelho if v < 0 else fmt_verde)
                for c in range(4, 8): worksheet.write(r, c, "", fmt_grade)

        st.download_button("📥 Baixar Planilha Final", output.getvalue(), f"Extrato_{nome_banco}.xlsx")
    else:
        st.error("O robô ainda não conseguiu ler. Isso acontece porque o PDF está codificado de uma forma muito difícil.")
