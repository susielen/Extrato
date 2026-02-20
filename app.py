import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def extrair_valor_limpo(texto):
    if not texto: return None
    t = str(texto).upper().replace('"', '').replace(' ', '').strip()
    # Regra Contábil: D é Saída (-), C é Entrada (+)
    saida = 'D' in t or '-' in t
    num = re.sub(r'[^\d,.]', '', t)
    try:
        if ',' in num and '.' in num: num = num.replace('.', '').replace(',', '.')
        elif ',' in num: num = num.replace(',', '.')
        res = float(num)
        return -res if saida else res
    except:
        return None

# --- INTERFACE ---
st.set_page_config(page_title="Conversor de Extrato Profissional", layout="centered")
st.markdown("<style>.stApp {background-color: #E3F2FD;}</style>", unsafe_allow_html=True)

st.title("🤖 Robô de Extratos v14")
st.write("Otimizado para capturar múltiplos lançamentos por linha (Caixa/Santander).")

arquivo_pdf = st.file_uploader("Selecione o PDF", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    # Regex para capturar datas e valores com C/D
    regex_data = r'(\d{2}/\d{2}/\d{4})'
    regex_valor_cd = r'([\d.]+,\d{2}\s*[CD])'

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            # Extração em formato de tabela para lidar com as aspas do seu PDF
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                for linha in tabela:
                    # Une a linha para processar blocos de texto internos
                    texto_linha = " ".join([str(c) for c in linha if c])
                    
                    # Encontra todas as datas e todos os valores na mesma "linha" do PDF
                    datas_encontradas = re.findall(regex_data, texto_linha)
                    valores_encontrados = re.findall(regex_valor_cd, texto_linha)
                    
                    # Se houver múltiplos valores para uma ou mais datas
                    for i in range(len(valores_encontrados)):
                        valor_bruto = valores_encontrados[i]
                        # Associa à data correspondente ou à última data encontrada
                        data_mov = datas_encontradas[i] if i < len(datas_encontradas) else datas_encontradas[-1]
                        
                        # Tenta isolar o histórico (texto que não é data nem valor)
                        historico = texto_linha.replace(data_mov, "").replace(valor_bruto, "")
                        historico = re.sub(r'["\n\r]', ' ', historico) # Limpa aspas e quebras
                        historico = re.sub(r'\d{2}:\d{2}:\d{2}', '', historico).strip().upper()
                        
                        v_final = extrair_valor_limpo(valor_bruto)
                        
                        if v_final is not None and v_final != 0 and "SALDO" not in historico:
                            dados_lista.append({
                                'Data': data_mov,
                                'Histórico': historico[:50], # Limita tamanho para o Excel
                                'Valor': v_final
                            })

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        st.success(f"Capturados {len(df)} lançamentos com sucesso!")
        st.dataframe(df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, startrow=3, startcol=1, sheet_name='Extrato')
            workbook, worksheet = writer.book, writer.sheets['Extrato']
            
            fmt_verde = workbook.add_format({'font_color': '#008000', 'num_format': '#,##0.00', 'border': 1})
            fmt_vermelho = workbook.add_format({'font_color': '#FF0000', 'num_format': '#,##0.00', 'border': 1})
            fmt_cabecalho = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1})

            worksheet.set_column('B:D', 20)
            worksheet.set_column('C:C', 40)
            
            for i, row in df.iterrows():
                r = i + 4
                v = row['Valor']
                worksheet.write_number(r, 3, v, fmt_vermelho if v < 0 else fmt_verde)

        st.download_button("📥 Baixar Planilha Integrada", output.getvalue(), "Extrato_Completo.xlsx")
    else:
        st.error("Não foram detectados lançamentos. Verifique o formato do arquivo.")
