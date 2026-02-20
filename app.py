import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def limpar_valor_geral(texto):
    if not texto: return None
    t = str(texto).upper().replace('"', '').replace('\n', '').strip()
    # Para o fornecedor o credito é positivo e o debito negativo
    e_saida = 'D' in t or '-' in t
    
    num = re.sub(r'[^\d,.]', '', t)
    try:
        if ',' in num and '.' in num: num = num.replace('.', '').replace(',', '.')
        elif ',' in num: num = num.replace(',', '.')
        res = float(num)
        return -res if e_saida else res
    except:
        return None

# --- CSS PARA AZUL TOTAL ---
st.set_page_config(page_title="Robô de Extratos Multi-Banco", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #E3F2FD !important; }
    h1 { color: #1565C0 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Robô de Extratos (Santander & Caixa)")

nome_banco = st.text_input("Nome do Banco", "Santander / Caixa")
arquivo_pdf = st.file_uploader("Selecione o PDF", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    regex_data = r'(\d{2}/\d{2}/\d{4}|\d{2}/\d{2}/\d{2}|\d{2}/\d{2})'

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto_bruto = pagina.extract_text()
            if not texto_bruto: continue
            
            linhas = texto_bruto.split('\n')
            for linha in linhas:
                match_data = re.search(regex_data, linha)
                if match_data:
                    data_f = match_data.group(1)
                    
                    # --- CAMINHO 1: SE FOR O FORMATO DA CAIXA (COM VÍRGULAS E ASPAS) ---
                    if '","' in linha or '",' in linha:
                        partes = [p.replace('"', '').strip() for p in linha.split(',')]
                        if len(partes) >= 3:
                            historico = partes[2].upper()
                            valor_bruto = ""
                            for p in reversed(partes):
                                if ' C' in p.upper() or ' D' in p.upper():
                                    valor_bruto = p
                                    break
                            v_final = limpar_valor_geral(valor_bruto)
                        else: v_final = None
                    
                    # --- CAMINHO 2: SE FOR O FORMATO DO SANTANDER (TEXTO CORRIDO) ---
                    else:
                        resto = linha.replace(data_f, "").strip()
                        partes = resto.split()
                        if len(partes) >= 2:
                            valor_bruto = partes[-1]
                            historico = " ".join(partes[:-1]).strip().upper()
                            if historico.endswith("-"): historico = historico[:-1].strip()
                            v_final = limpar_valor_geral(valor_bruto)
                        else: v_final = None

                    # Adiciona se for um lançamento válido
                    if v_final is not None and v_final != 0 and "SALDO" not in str(historico):
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
                worksheet.write(r, 1, row['Data'], fmt_data)
                worksheet.write(r, 2, row['Histórico'], fmt_grade)
                v = row['Valor']
                worksheet.write_number(r, 3, v, fmt_vermelho if v < 0 else fmt_verde)
                for c in range(4, 8): worksheet.write(r, c, "", fmt_grade)

        st.download_button("📥 Baixar Planilha Final", output.getvalue(), "Extrato_Final.xlsx")
    else:
        st.error("Não foi possível ler este arquivo. Verifique se ele é um PDF original.")
