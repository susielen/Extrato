import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(page_title="Conversor de Extrato Bancário", layout="wide")

st.title("📋 Meu Conversor de Extrato")
st.write("Vou organizar seu extrato em: Data, Histórico, Débito (Saída) e Crédito (Entrada).")

arquivo_pdf = st.file_uploader("Suba o seu PDF aqui", type="pdf")

if arquivo_pdf:
    dados_extraidos = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            # Pegamos o texto bruto da página para não depender de tabelas invisíveis
            texto_pagina = pagina.extract_text()
            if texto_pagina:
                linhas = texto_pagina.split('\n')
                for linha in linhas:
                    # O robô procura linhas que começam com Data (ex: 17/12 ou 17/12/2025)
                    match_data = re.search(r'(\d{2}/\d{2}(?:/\d{2,4})?)', linha)
                    
                    if match_data:
                        data = match_data.group(1)
                        # Removemos a data do texto para sobrar o resto
                        resto = linha.replace(data, "").strip()
                        
                        # Procuramos valores (ex: 1.057,00 ou 60,00-)
                        # Essa regra pega números que terminam ou começam com sinal
                        valores = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}-?|(?<=\s)-?\d{1,3}(?:\.\d{3})*,\d{2})', resto)
                        
                        if valores:
                            valor_principal = valores[-1] # Geralmente o último valor da linha é o da transação
                            historico = resto.replace(valor_principal, "").strip()
                            
                            debito = ""
                            credito = ""
                            
                            # REGRA: Se tem o tracinho "-", é DÉBITO (Saída). Se não, é CRÉDITO (Entrada).
                            if "-" in valor_principal:
                                debito = valor_principal.replace("-", "").strip()
                            else:
                                credito = valor_principal.strip()
                            
                            dados_extraidos.append([data, historico, debito, credito])

    if dados_extraidos:
        df = pd.DataFrame(dados_extraidos, columns=["Data", "Histórico", "Débito (Saída)", "Crédito (Entrada)"])
        
        st.success(f"Consegui ler {len(df)} lançamentos!")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Botão para o Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Extrato')
        
        st.download_button(
            label="📥 Baixar Planilha Pronta",
            data=output.getvalue(),
            file_name="extrato_dia_a_dia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("O robô ainda não conseguiu ler. Pode ser que esse PDF seja uma imagem ou foto.")
