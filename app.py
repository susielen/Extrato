import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def limpar_texto_caixa(texto):
    if not texto: return ""
    # Remove aspas e quebras de linha que o PDF da Caixa insere no meio das palavras
    return str(texto).replace('"', '').replace('\n', ' ').replace('\r', '').strip()

def processar_valor_universal(valor_texto):
    t = limpar_texto_caixa(valor_texto).upper()
    if not t or t == "0,00" or "SALDO" in t: return None
    
    # Regra que você me passou: Credito é positivo, Debito é negativo
    # No seu arquivo da Caixa: "0,01 C" ou "100,00 D"
    e_saida = 'D' in t or '-' in t
    
    # Mantém apenas números e a pontuação
    num = re.sub(r'[^\d,.]', '', t)
    try:
        if ',' in num and '.' in num: num = num.replace('.', '').replace(',', '.')
        elif ',' in num: num = num.replace(',', '.')
        res = float(num)
        return -res if e_saida else res
    except:
        return None

# --- CONFIGURAÇÃO VISUAL (AZUL E ORGANIZADO) ---
st.set_page_config(page_title="Robô de Extratos Profissional", layout="centered")
st.markdown("<style>.stApp {background-color: #E3F2FD;}</style>", unsafe_allow_html=True)

st.title("🤖 Conversor de Extratos v12")
st.info("Compatível com Santander e o modelo CSV/PDF da Caixa.")

arquivo_pdf = st.file_uploader("Selecione o arquivo PDF", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    regex_data = r'(\d{2}/\d{2}/\d{4})'

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto_bruto = pagina.extract_text()
            if not texto_bruto: continue
            
            # Divide o texto em linhas
            linhas = texto_bruto.split('\n')
            for linha in linhas:
                match_data = re.search(regex_data, linha)
                if match_data:
                    data_f = match_data.group(1)
                    
                    # TENTATIVA 1: Lógica para o formato da Caixa (separado por vírgula e aspas)
                    if '","' in linha or '",' in linha:
                        # Limpamos a linha de aspas e quebras de linha antes de dividir
                        linha_limpa = linha.replace('"', '').replace('\n', '')
                        partes = [p.strip() for p in linha_limpa.split(',')]
                        
                        if len(partes) >= 3:
                            # No seu arquivo, Histórico é a 3ª parte e Valor é a 6ª ou última que contém C/D
                            historico = partes[2].upper()
                            valor_bruto = ""
                            for p in reversed(partes):
                                if ' C' in p.upper() or ' D' in p.upper():
                                    valor_bruto = p
                                    break
                            v_final = processar_valor_universal(valor_bruto)
                        else: v_final = None
                    
                    # TENTATIVA 2: Lógica para Santander (espaços comuns)
                    else:
                        corpo = linha.replace(data_f, "").strip()
                        partes = corpo.split()
                        if len(partes) >= 2:
                            valor_bruto = partes[-1]
                            historico = " ".join(partes[:-1]).strip().upper()
                            if historico.endswith("-"): historico = historico[:-1].strip()
                            v_final = processar_valor_universal(valor_bruto)
                        else: v_final = None

                    # Só adiciona se o valor for real (ignora saldos e zeros)
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

        # GERAÇÃO DO EXCEL PERSONALIZADO
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, startrow=3, startcol=1, sheet_name='Extrato')
            workbook, worksheet = writer.book, writer.sheets['Extrato']
            
            # Formatos de Célula
            fmt_grade = workbook.add_format({'border': 1})
            fmt_data = workbook.add_format({'border': 1, 'align': 'center'})
            fmt_verde = workbook.add_format({'font_color': '#008000', 'num_format': '#,##0.00', 'border': 1})
            fmt_vermelho = workbook.add_format({'font_color': '#FF0000', 'num_format': '#,##0.00', 'border': 1})
            fmt_cabecalho = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1, 'align': 'center'})

            # Configurações de Coluna
            worksheet.set_column('B:B', 12) # Data
            worksheet.set_column('C:C', 45) # Histórico
            worksheet.set_column('D:D', 15) # Valor
            worksheet.set_column('E:H', 20) # Outras colunas

            # Adicionando as Notas (Com o tamanho que você pediu para ler tudo)
            prop_nota = {'width': 300, 'height': 80}
            titulos = ["Data", "Histórico", "Valor", "Débito", "Crédito", "Complemento", "Descrição"]
            for i, tit in enumerate(titulos):
                worksheet.write(3, i+1, tit, fmt_cabecalho)
                if tit == "Descrição":
                    worksheet.write_comment(3, i+1, 'Fórmula: =MAIÚSCULA(CONCAT(G4; " "; C4))', prop_nota)

            # Preenchendo os dados com cores
            for i, row in df.iterrows():
                r = i + 4
                worksheet.write(r, 1, row['Data'], fmt_data)
                worksheet.write(r, 2, row['Histórico'], fmt_grade)
                v = row['Valor']
                worksheet.write_number(r, 3, v, fmt_vermelho if v < 0 else fmt_verde)
                for c in range(4, 8): worksheet.write(r, c, "", fmt_grade)

        st.download_button("📥 Baixar Planilha Pronta", output.getvalue(), "Extrato_Formatado.xlsx")
    else:
        st.error("Não foi possível ler este modelo de PDF. Tente baixar o extrato original em PDF no site do banco.")
