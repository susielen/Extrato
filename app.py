import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def limpar_valor_caixa(texto):
    if not texto: return None
    t = str(texto).upper().strip()
    # Identifica saída (D) ou entrada (C)
    # No seu arquivo: "1.183,78 D" -> Negativo | "1.183,78 C" -> Positivo
    e_saida = 'D' in t or '-' in t
    
    # Remove letras e deixa apenas os números e separadores
    num = re.sub(r'[^\d,.]', '', t)
    try:
        if ',' in num and '.' in num:
            num = num.replace('.', '').replace(',', '.')
        elif ',' in num:
            num = num.replace(',', '.')
        res = float(num)
        return -res if e_saida else res
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

st.title("🤖 Conversor de Extrato Caixa & Santander")

nome_banco = st.text_input("Nome do Banco", "Caixa Econômica")
arquivo_pdf = st.file_uploader("Selecione o arquivo PDF", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    # Regex para pegar a data (DD/MM/AAAA) mesmo que tenha hora depois
    regex_data = r'(\d{2}/\d{2}/\d{4})'

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            # Extração focada em tabelas para o layout da Caixa
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # Filtra apenas linhas que começam com data
                    primeira_celula = str(linha[0])
                    match_data = re.search(regex_data, primeir_celula)
                    
                    if match_data:
                        data_f = match_data.group(1)
                        # No modelo Caixa: o Valor é a penúltima coluna e o Saldo a última
                        # Vamos pegar o Valor (geralmente índice -2 ou -1 dependendo da linha)
                        valor_bruto = ""
                        for celula in reversed(linha):
                            if celula and ('C' in str(celula) or 'D' in str(celula)):
                                valor_bruto = celula
                                break
                        
                        # Histórico (Geralmente na coluna 2 ou 3)
                        historico = str(linha[2]) if len(linha) > 2 else ""
                        if not historico or historico == 'None':
                            historico = str(linha[1])
                            
                        # Limpezas
                        historico = historico.strip().upper()
                        if historico.endswith("-"): historico = historico[:-1].strip()
                        
                        v_final = limpar_valor_caixa(valor_bruto)
                        
                        # Evita pegar "Saldo Dia" com valor 0
                        if v_final is not None and v_final != 0:
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
            worksheet.set_column('B:B', 12) # Data Centralizada
            worksheet.set_column('C:C', 45) # Histórico Maiúsculo
            worksheet.set_column('D:D', 15) # Valor Colorido
            worksheet.set_column('E:H', 25) # Colunas com Notas

            # NOTAS GRANDES
            prop = {'width': 280, 'height': 80}
            titulos = ["Data", "Histórico", "Valor", "Débito", "Crédito", "Complemento", "Descrição"]
            for col_num, titulo in enumerate(titulos):
                col_idx = col_num + 1
                worksheet.write(3, col_idx, titulo, fmt_cabecalho)
                if titulo in ["Débito", "Crédito"]:
                    worksheet.write_comment(3, col_idx, 'Escritório, coloque aqui o código reduzido do plano de contas.', prop)
                elif titulo == "Complemento":
                    worksheet.write_comment(3, col_idx, 'DICA: Digite sempre em MAIÚSCULAS.', prop)
                elif titulo == "Descrição":
                    worksheet.write_comment(3, col_idx, 'Use a fórmula: =MAIÚSCULA(CONCAT(G4; " "; C4))', prop)

            for i, row in df.iterrows():
                r = i + 4
                worksheet.write(r, 1, row['Data'], fmt_data) # Data Centralizada
                worksheet.write(r, 2, row['Histórico'], fmt_grade)
                v = row['Valor']
                worksheet.write_number(r, 3, v, fmt_vermelho if v < 0 else fmt_verde)
                for c in range(4, 8): worksheet.write(r, c, "", fmt_grade)

        st.download_button("📥 Baixar Planilha Final", output.getvalue(), f"Extrato_{nome_banco}.xlsx")
    else:
        st.error("Dados não encontrados. Verifique se o PDF é o extrato original da Caixa.")
