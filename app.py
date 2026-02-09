import streamlit as st
import pandas as pd
import pdfplumber
import io

# Configuração simples da página
st.set_page_config(page_title="Conversor de Extrato")

st.title("🤖 Robô de Extrato")
st.write("Transformando seu PDF nas colunas: Data, Histórico, Débito e Crédito.")

# Campo para subir o arquivo
arquivo_pdf = st.file_uploader("Arraste seu PDF aqui", type="pdf")

if arquivo_pdf:
    dados_lista = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # O robô limpa a linha e verifica se não está vazia
                    if linha and any(item for item in linha):
                        # Pegamos as 4 primeiras colunas (Data, Histórico, Débito, Crédito)
                        dados_lista.append(linha[:4])

    if dados_lista:
        # Criando a tabela organizada
        df = pd.DataFrame(dados_lista, columns=["Data", "Historico", "Debito", "Credito"])
        
        # O robô marca as palavras importantes que você pediu [cite: 2026-02-05]
        palavras_alerta = ["SAÍDA", "PRESTADO"]
        df['Busca'] = df['Historico'].apply(
            lambda x: "🚩" if any(p in str(x).upper() for p in palavras_alerta) else ""
        )

        st.success("Prontinho! Aqui está sua prévia:")
        st.dataframe(df, use_container_width=True)

        # Gerando o arquivo para baixar
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Extrato_Bancario')
        
        st.download_button(
            label="📥 Baixar arquivo Excel (.xlsx)",
            data=output.getvalue(),
            file_name="meu_extrato.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Não encontrei dados para converter.")
