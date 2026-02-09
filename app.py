import streamlit as st
import pandas as pd
import pdfplumber
import io

# Título do seu Robô
st.set_page_config(page_title="Conversor de Extrato Bancário")
st.title("🤖 Meu Robô de Extratos")
st.write("Configurado: Entrada é Crédito (+) e Saída é Débito (-)")

# Campo para o PDF
arquivo_pdf = st.file_uploader("Suba o extrato em PDF", type="pdf")

if arquivo_pdf:
    dados_bancarios = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # O robô limpa a linha e garante que tem conteúdo
                    if linha and any(item for item in linha):
                        # Pega as colunas na ordem do banco
                        dados_bancarios.append(linha[:4])

    if dados_bancarios:
        # Organiza as 4 colunas que você pediu
        df = pd.DataFrame(dados_bancarios, columns=["Data", "Historico", "Debito", "Credito"])
        
        # O robô procura as palavras SAÍDA e PRESTADO [cite: 2026-02-05]
        palavras_importantes = ["SAÍDA", "PRESTADO"]
        df['Aviso'] = df['Historico'].apply(
            lambda x: "🚩" if any(p in str(x).upper() for p in palavras_importantes) else ""
        )

        st.success("Tabela gerada com sucesso!")
        st.dataframe(df, use_container_width=True)

        # Prepara o download para Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Extrato')
        
        st.download_button(
            label="📥 Baixar Planilha (.xlsx)",
            data=output.getvalue(),
            file_name="extrato_bancario.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Não encontrei informações no PDF.")
