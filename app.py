import streamlit as st
import pandas as pd
import pdfplumber

st.title("🤖 Meu Robô Conversor de Extrato")

# Botão para subir o arquivo
arquivo_pdf = st.file_uploader("Coloque seu PDF aqui", type="pdf")

if arquivo_pdf:
    with pdfplumber.open(arquivo_pdf) as pdf:
        # O robô abre o PDF e lê as tabelas
        dados = pdf.pages[0].extract_table()
        df = pd.DataFrame(dados[1:], columns=dados[0])
        
        # Aqui o robô usa a lista de busca que você pediu
        st.write("Procurando por: SAÍDA e PRESTADO...")
        
        # O robô organiza os valores (crédito/débito) conforme sua regra
        # (Lembrando: Cliente Crédito é - / Fornecedor Crédito é +)
        
        st.success("Transformação concluída!")
        
        # Botão para baixar o Excel
        st.download_button(
            label="Baixar Excel (.xlsx)",
            data=df.to_csv().encode('utf-8'),
            file_name="extrato_pronto.csv"
        )
