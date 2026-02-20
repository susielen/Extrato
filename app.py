import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
import csv

def limpar_valor_universal(texto):
    if not texto: return None
    # Remove aspas e limpa espaços
    t = str(texto).upper().replace('"', '').strip()
    # Para o fornecedor o credito é positivo e o debito negativo
    e_saida = 'D' in t or '-' in t
    
    # Mantém apenas números e separadores
    num = re.sub(r'[^\d,.]', '', t)
    try:
        if ',' in num and '.' in num: num = num.replace('.', '').replace(',', '.')
        elif ',' in num: num = num.replace(',', '.')
        res = float(num)
        return -res if e_saida else res
    except:
        return None

# --- CSS PARA AZUL TOTAL ---
st.set_page_config(page_title="Robô de Extratos Profissional", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #E3F2FD !important; }
    h1 { color: #1565C0 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Robô de Extratos (Versão Definitiva)")

nome_banco = st.text_input("Nome do Banco", "Caixa / Santander")
arquivo_pdf = st.file_uploader("Selecione o PDF", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    regex_data = r'(\d{2}/\d{2}/\d{4})'

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto_bruto = pagina.extract_text()
            if not texto_bruto: continue
            
            # --- LÓGICA ESPECIAL PARA CAIXA (CSV DENTRO DE PDF) ---
            if '","' in texto_bruto:
                # Usamos o leitor de CSV para não errar por causa das vírgulas nos valores
                f = io.StringIO(texto_bruto)
                reader = csv.reader(f, delimiter=',', quotechar='"')
                for linha in reader:
                    if len(linha) > 0:
                        # Procura data na primeira coluna
                        match_data = re.search(regex_data, linha[0])
                        if match_data:
                            data_f = match_data.group(1)
                            historico = linha[2].strip().upper() if len(linha) > 2 else ""
                            # O valor na Caixa que enviou está na coluna 5 (índice 5)
                            valor_bruto = linha[5] if len(linha) > 5 else ""
                            
                            v_final = limpar_valor_universal(valor_bruto)
                            if v_final is not None and v_final != 0 and "SALDO" not in historico:
                                dados_lista.append({'Data': data_f, 'Histórico': historico, 'Valor': v_final})

            # --- LÓGICA PARA SANTANDER E OUTROS (TEXTO) ---
            else:
                for linha in texto_bruto.split('\n'):
                    match_data = re.search(regex_data, linha)
                    if match_data:
                        data_f = match_data.group(1)
                        partes = linha.replace(data_f, "").strip().split()
                        if len(partes) >= 2:
                            valor_bruto = partes[-1]
                            historico = " ".join(partes[:-1]).strip().upper()
                            if historico.endswith("-"): historico = historico[:-1].strip()
                            v_final = limpar_valor_universal(valor_bruto)
                            if v_final is not None and v_final != 0:
                                dados_lista.append({'Data': data_f, 'Histórico': historico, 'Valor': v_final})

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        st.success(f"Encontramos {len(df)} lançamentos!")
        st.dataframe(df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, startrow=3, startcol=1, sheet_name='Extrato')
            workbook, worksheet = writer.book, writer.sheets['Extrato']
            
            fmt_grade = workbook.add_format({'border': 1})
            fmt_data = workbook.add_format({'border': 1, 'align': 'center'})
            fmt_verde = workbook.add_format({'font_color': '#008000', 'num_format': '#,##0.00', 'border': 1})
            fmt_vermelho = workbook.add_format({'font_color': '#FF0000', 'num_format': '#,##0.00', 'border': 1})
            fmt_cabecalho = workbook.add_format({'bold': True, 'bg_color': '#EAEAEA', 'border': 1, 'align': 'center'})

            worksheet.hide_gridlines(2)
            worksheet.merge_range('B2:C2', f"BANCO: {nome_banco}", fmt_cabecalho)
            worksheet.set_column('B:B', 12) # Centralizado
            worksheet.set_column('C:C', 45) # Maiúsculo
            worksheet.set_column('D:D', 15)
            worksheet.set_column('E:H', 25)

            prop = {'width': 280, 'height': 80}
            titulos = ["Data", "Histórico", "Valor", "Débito", "Crédito", "Complemento", "Descrição"]
            for col_num, titulo in enumerate(titulos):
                col_idx = col_num + 1
                worksheet.write(3, col_idx, titulo, fmt_cabecalho)
                if titulo in ["Débito", "Crédito"]:
                    worksheet.write_comment(3, col_idx, 'Código reduzido do plano de contas.', prop)
                elif titulo == "Complemento":
                    worksheet.write_comment(3, col_idx, 'DICA: Digite sempre em MAIÚSCULAS.', prop)
                elif titulo == "Descrição":
                    worksheet.write_comment(3, col_idx, 'Fórmula: =MAIÚSCULA(CONCAT(G4; " "; C4))', prop)

            for i, row in df.iterrows():
                r = i + 4
                worksheet.write(r, 1, row['Data'], fmt_data) # Data Centralizada
                worksheet.write(r, 2, row['Histórico'], fmt_grade)
                v = row['Valor']
                worksheet.write_number(r, 3, v, fmt_vermelho if v < 0 else fmt_verde)
                for c in range(4, 8): worksheet.write(r, c, "", fmt_grade)

        st.download_button("📥 Baixar Planilha Final", output.getvalue(), "Extrato_Padronizado.xlsx")
    else:
        st.error("Não foi possível ler os dados. Verifique se o PDF é o original do banco.")
