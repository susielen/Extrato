import streamlit as st
import pandas as pd
import pdfplumber
import io

# Configuração da página
st.set_page_config(page_title="Conversor de PDF para Excel")

st.title("🤖 Robô Conversor de Extrato")
st.write("Transformo seu PDF em Excel com as colunas: Data, Histórico, Débito e Crédito.")

# Upload do arquivo
arquivo_pdf = st.file_uploader("Selecione o arquivo PDF do banco", type="pdf")

if arquivo_pdf:
    dados_vagos = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # O robô limpa a linha e verifica se tem dados
                    if linha and any(item for item in linha):
                        # Pega as 4 colunas principais (ajuste conforme seu banco)
                        dados_vagos.append(linha[:4])

    if dados_vagos:
        # Criando a tabela (Data, Histórico, Débito, Crédito)
        df = pd.DataFrame(dados_vagos, columns=["Data", "Historico", "Debito", "Credito"])
        
        st.success("PDF lido com sucesso!")
        st.dataframe(df, use_container_width=True)

        # Preparando o Excel para baixar
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Extrato_Bancario')
        
        st.download_button(
            label="📥 Baixar Arquivo Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="extrato_convertido.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Não encontrei tabelas de dados neste arquivo.")
