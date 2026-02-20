import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def processar_valor_unico(texto_valor):
    if not texto_valor: return None
    t = str(texto_valor).upper().replace(" ", "").replace("R$", "")
    # Regra: Se tiver '-' ou 'D', é negativo. Se tiver 'C' ou for positivo, mantém.
    e_saida = '-' in t or 'D' in t
    
    # Pega apenas números, vírgula e ponto
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

# --- CONFIGURAÇÃO STREAMLIT ---
st.set_page_config(page_title="Robô de Extratos Profissional", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #E3F2FD !important; }
    h1 { color: #1565C0 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 Conversor de Extrato (Universal)")

col1, col2 = st.columns(2)
with col1:
    nome_empresa = st.text_input("Empresa", "Minha Empresa")
with col2:
    nome_banco = st.text_input("Banco", "Caixa Econômica")

arquivo_pdf = st.file_uploader("Selecione o arquivo PDF", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    regex_data = r'(\d{2}/\d{2}(?:/\d{4})?)'

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            # TENTATIVA 1: Ler como Tabela (Ideal para Caixa)
            tabelas = pagina.extract_tables()
            if tabelas:
                for tabela in tabelas:
                    for linha in tabela:
                        # Filtra células vazias e junta a linha para análise
                        linha_texto = " ".join([str(c) for c in linha if c])
                        match_data = re.search(regex_data, linha_texto)
                        
                        if match_data and len(linha) >= 2:
                            data_str = match_data.group(1)
                            # Pega o último valor da linha da tabela
                            valor_bruto = str(linha[-1])
                            # Histórico é o que sobra entre a data e o valor
                            historico = " ".join([str(c) for c in linha[1:-1] if c]).strip()
                            
                            historico = historico.replace(data_str, "").strip()
                            if historico.endswith("-"): historico = historico[:-1].strip()
                            
                            v_final = processar_valor_unico(valor_bruto)
                            if v_final is not None:
                                dados_lista.append({'Data': data_str, 'Histórico': historico.upper(), 'Valor': v_final})

            # TENTATIVA 2: Se a tabela falhar, lê como texto (Santander/Itau)
            if not dados_lista:
                texto = pagina.extract_text()
                if texto:
                    for linha in texto.split('\n'):
                        match_data = re.search(regex_data, linha)
                        if match_data:
                            data_str = match_data.group(1)
                            partes = linha.replace(data_str, "").strip().split()
                            if len(partes) >= 2:
                                valor_bruto = partes[-1]
                                hist = " ".join(partes[:-1]).strip()
                                if hist.endswith("-"): hist = hist[:-1].strip()
                                v_final = processar_valor_unico(valor_bruto)
                                if v_final is not None:
                                    dados_lista.append({'Data': data_str, 'Histórico': hist.upper(), 'Valor': v_final})

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        st.success(f"Sucesso! {len(df)} lançamentos encontrados.")
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

            # LAYOUT EXCEL
            worksheet.hide_gridlines(2)
            worksheet.merge_range('B2:D2', f"BANCO: {nome_banco} | EMPRESA: {nome_empresa}", fmt_cabecalho)
            worksheet.set_column('B:B', 12)
            worksheet.set_column('C:C', 50)
            worksheet.set_column('D:H', 20)

            # Cabeçalho com Notas Maiores
            prop = {'width': 280, 'height': 80}
            titulos = ["Data", "Histórico", "Valor", "Débito", "Crédito", "Complemento", "Descrição"]
            for col_num, titulo in enumerate(titulos):
                col_idx = col_num + 1
                worksheet.write(3, col_idx, titulo, fmt_cabecalho)
                if titulo in ["Débito", "Crédito"]:
                    worksheet.write_comment(3, col_idx, 'Coloque aqui o código reduzido do plano de contas do seu sistema.', prop)
                elif titulo == "Complemento":
                    worksheet.write_comment(3, col_idx, 'DICA: Digite sempre em MAIÚSCULAS.', prop)
                elif titulo == "Descrição":
                    worksheet.write_comment(3, col_idx, 'Fórmula sugerida: =MAIÚSCULA(CONCAT(G4; " "; C4))', prop)

            for i, row in df.iterrows():
                r = i + 4
                worksheet.write(r, 1, row['Data'], fmt_data)
                worksheet.write(r, 2, row['Histórico'], fmt_grade)
                v = row['Valor']
                worksheet.write_number(r, 3, v, fmt_vermelho if v < 0 else fmt_verde)
                for c in range(4, 8): worksheet.write(r, c, "", fmt_grade)

        st.download_button("📥 Baixar Planilha Final", output.getvalue(), f"Extrato_{nome_banco}.xlsx")
