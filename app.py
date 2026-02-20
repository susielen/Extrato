import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def limpar_valor(v):
    if not v: return None
    v = str(v).upper().strip()
    # Verifica se é débito
    saida = '-' in v or 'D' in v
    # Limpa tudo que não é número ou pontuação
    num = re.sub(r'[^\d,.]', '', v)
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

st.title("🤖 Super Conversor de Extratos")
st.write("Versão otimizada para extratos difíceis (Caixa/BB)")

nome_banco = st.text_input("Nome do Banco", "Caixa Econômica")
arquivo_pdf = st.file_uploader("Selecione o PDF", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    # Regex para pegar qualquer data: 01/01/2026 ou 01/01/26
    regex_data = r'(\d{2}/\d{2}(?:/\d{2,4})?)'

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            # Extração por "Words" (Pega a posição de cada palavra na folha)
            palavras = pagina.extract_words(x_tolerance=3, y_tolerance=3)
            
            # Agrupar palavras que estão na mesma linha (mesmo 'top')
            linhas_dict = {}
            for p in palavras:
                top = round(p['top'], 0) # Arredonda para agrupar palavras na mesma altura
                if top not in linhas_dict:
                    linhas_dict[top] = []
                linhas_dict[top].append(p)
            
            # Processar cada linha encontrada
            for top in sorted(linhas_dict.keys()):
                linha_palavras = sorted(linhas_dict[top], key=lambda x: x['x0'])
                texto_linha = " ".join([p['text'] for p in linha_palavras])
                
                # Procura a data
                match_data = re.search(regex_data, texto_linha)
                if match_data:
                    data_f = match_data.group(1)
                    
                    # O valor geralmente é a última palavra da linha
                    valor_bruto = linha_palavras[-1]['text']
                    
                    # O histórico é o que sobrou entre a data e o valor
                    hist_partes = [p['text'] for p in linha_palavras if p['text'] != data_f and p['text'] != valor_bruto]
                    historico = " ".join(hist_partes).strip().upper()
                    
                    if historico.endswith("-"): historico = historico[:-1].strip()
                    
                    v_convertido = limpar_valor(valor_bruto)
                    
                    # Só adiciona se tiver um valor válido e não for 0
                    if v_convertido is not None and v_convertido != 0:
                        dados_lista.append({
                            'Data': data_f,
                            'Histórico': historico,
                            'Valor': v_convertido
                        })

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        st.success(f"Encontramos {len(df)} linhas!")
        st.dataframe(df)

        # GERAÇÃO DO EXCEL (Com todas as suas regras de design)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, startrow=3, startcol=1, sheet_name='Extrato')
            workbook, worksheet = writer.book, writer.sheets['Extrato']
            
            # Formatos
            fmt_grade = workbook.add_format({'border': 1})
            fmt_data = workbook.add_format({'border': 1, 'align': 'center'})
            fmt_verde = workbook.add_format({'font_color': '#008000', 'num_format': '#,##0.00', 'border': 1})
            fmt_vermelho = workbook.add_format({'font_color': '#FF0000', 'num_format': '#,##0.00', 'border': 1})
            fmt_cabecalho = workbook.add_format({'bold': True, 'bg_color': '#EAEAEA', 'border': 1, 'align': 'center'})

            worksheet.hide_gridlines(2)
            worksheet.merge_range('B2:C2', f"BANCO: {nome_banco}", fmt_cabecalho)
            worksheet.set_column('B:B', 12)
            worksheet.set_column('C:C', 50)
            worksheet.set_column('D:D', 15)
            worksheet.set_column('E:H', 25)

            # Notas Grandes
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
                    worksheet.write_comment(3, col_idx, 'Fórmula: =MAIÚSCULA(CONCAT(G4; " "; C4))', prop)

            for i, row in df.iterrows():
                r = i + 4
                worksheet.write(r, 1, row['Data'], fmt_data)
                worksheet.write(r, 2, row['Histórico'], fmt_grade)
                v = row['Valor']
                worksheet.write_number(r, 3, v, fmt_vermelho if v < 0 else fmt_verde)
                for c in range(4, 8): worksheet.write(r, c, "", fmt_grade)

        st.download_button("📥 Baixar Planilha Profissional", output.getvalue(), f"Extrato_{nome_banco}.xlsx")
    else:
        st.error("O robô não detectou dados. O seu PDF pode estar 'protegido' ou ser uma imagem.")
