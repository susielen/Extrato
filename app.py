import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def limpar_valor_caixa(texto):
    if not texto: return None
    # Remove aspas, espaços e limpa o texto
    t = str(texto).replace('"', '').upper().strip()
    if not t or t == "0,00 C" or t == "0,00 D": return 0.0
    
    # Regra: D para negativo, C para positivo
    e_saida = 'D' in t or '-' in t
    
    # Pega apenas os números e separadores
    num = re.sub(r'[^\d,.]', '', t)
    try:
        if ',' in num and '.' in num: num = num.replace('.', '').replace(',', '.')
        elif ',' in num: num = num.replace(',', '.')
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

st.title("🤖 Conversor Universal (Caixa Especial)")

nome_banco = st.text_input("Nome do Banco", "Caixa Econômica")
arquivo_pdf = st.file_uploader("Selecione o PDF da Caixa", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    # Regex para pegar a data dentro ou fora de aspas
    regex_data = r'(\d{2}/\d{2}/\d{4})'

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto_bruto = pagina.extract_text()
            if not texto_bruto: continue
            
            linhas = texto_bruto.split('\n')
            for linha in linhas:
                # 1. Procura a data
                match_data = re.search(regex_data, linha)
                if match_data:
                    data_f = match_data.group(1)
                    
                    # 2. Limpa a linha (remove aspas e divide por vírgulas ou aspas)
                    # O formato do seu PDF é: "Data","Doc","Historico",,,"Valor","Saldo"
                    partes = [p.strip().replace('"', '') for p in linha.split('","')]
                    
                    if len(partes) >= 3:
                        # No seu arquivo, o histórico costuma ser a 3ª parte
                        historico = partes[2].strip().upper()
                        
                        # O valor costuma ser a penúltima ou antepenúltima parte
                        # Vamos procurar o campo que contém 'C' ou 'D'
                        valor_bruto = ""
                        for p in partes:
                            if ' C' in p or ' D' in p:
                                valor_bruto = p
                                break
                        
                        # Se não achou nas partes separadas, tenta na linha toda
                        if not valor_bruto:
                            match_v = re.findall(r'(\d+[\d.,]*\s?[DC])', linha)
                            if match_v: valor_bruto = match_v[0]

                        v_final = limpar_valor_caixa(valor_bruto)
                        
                        # Filtra "SALDO DIA" e valores zerados para não sujar a planilha
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

        st.download_button("📥 Baixar Planilha Final", output.getvalue(), f"Extrato_{nome_banco}.xlsx")
    else:
        st.error("Ainda não conseguimos extrair os dados. Verifique se o PDF não está protegido por senha.")
