import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def limpar_valor_caixa(texto):
    if not texto: return None
    # Remove tudo que não é número, vírgula, ponto ou sinal de menos
    # Mantém o 'D' ou 'C' para identificar débito/crédito
    t = str(texto).upper().strip()
    
    # Identifica se é saída (Débito)
    e_saida = '-' in t or 'D' in t
    
    # Remove letras para converter em número
    apenas_numeros = re.sub(r'[^\d,.]', '', t)
    
    try:
        if ',' in apenas_numeros and '.' in apenas_numeros:
            apenas_numeros = apenas_numeros.replace('.', '').replace(',', '.')
        elif ',' in apenas_numeros:
            apenas_numeros = apenas_numeros.replace(',', '.')
        
        valor_float = float(apenas_numeros)
        return -valor_float if e_saida else valor_float
    except:
        return None

# --- INTERFACE ---
st.set_page_config(page_title="Conversor Universal v4", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #E3F2FD !important; }
    h1 { color: #1565C0 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Conversor de Extrato (Modo Força Bruta)")
st.info("Este modo tenta ler linha por linha, ignorando tabelas invisíveis.")

nome_banco = st.text_input("Banco", "Caixa Econômica")

arquivo_pdf = st.file_uploader("Selecione o PDF da Caixa", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    # Regex para datas brasileiras
    regex_data = r'(\d{2}/\d{2}/\d{4}|\d{2}/\d{2}/\d{2})'
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            # Pegamos o texto bruto, mas com uma técnica de manter o layout original
            texto_bruto = pagina.extract_text(layout=True)
            if not texto_bruto: continue
            
            linhas = texto_bruto.split('\n')
            for linha in linhas:
                # 1. Procura uma data na linha
                match_data = re.search(regex_data, linha)
                if match_data:
                    data_str = match_data.group(1)
                    
                    # 2. Tenta achar algo que pareça um valor no final da linha (ex: 1.234,55 ou 100,00 D)
                    # Busca números com vírgula no final da linha
                    match_valor = re.findall(r'(\d+[\d.,]*\s?[DC-]?)$', linha.strip())
                    
                    if match_valor:
                        valor_bruto = match_valor[-1]
                        
                        # 3. O histórico é o que está entre a data e o valor
                        historico = linha.replace(data_str, "").replace(valor_bruto, "").strip()
                        
                        # Limpezas extras
                        if historico.endswith("-"): historico = historico[:-1].strip()
                        
                        v_final = limpar_valor_caixa(valor_bruto)
                        
                        if v_final is not None and v_final != 0:
                            dados_lista.append({
                                'Data': data_str,
                                'Histórico': historico.upper(),
                                'Valor': v_final
                            })

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        st.success(f"Encontramos {len(df)} lançamentos!")
        st.dataframe(df)
        
        # Gerador de Excel (mesmo padrão visual anterior)
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
            worksheet.set_column('C:C', 50)
            worksheet.set_column('D:H', 25)

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

        st.download_button("📥 Baixar Planilha", output.getvalue(), f"Extrato_{nome_banco}.xlsx")
    else:
        st.error("Ainda não conseguimos ler este arquivo.")
        st.write("Dica: Se o seu PDF for uma foto ou digitalizado, este robô não consegue ler. Ele precisa ser o PDF original do Internet Banking.")
