import streamlit as st
import pandas as pd
import pdfplumber
import io

# Configuração da página
st.set_page_config(page_title="Conversor de Extrato", layout="wide")

st.title("🤖 Meu Robô de Extratos")
st.write("Converta seu PDF para Excel com as colunas: Data, Histórico, Débito e Crédito.")

# Escolha da regra de sinal
tipo_conta = st.radio("Configuração de sinal para:", ["Fornecedor", "Cliente"])

arquivo_pdf = st.file_uploader("Suba seu extrato em PDF", type="pdf")

if arquivo_pdf:
    dados_extraidos = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # Remove linhas totalmente vazias
                    if any(item is not None and str(item).strip() != "" for item in linha):
                        dados_extraidos.append(linha)

    if dados_extraidos:
        # Criamos o DataFrame com as colunas que você pediu
        df = pd.DataFrame(dados_extraidos)
        
        # Ajustamos para ter exatamente 4 colunas principais
        if len(df.columns) >= 4:
            df = df.iloc[:, :4]
            df.columns = ["Data", "Historico", "Debito", "Credito"]
            
            # Busca palavras-chave no histórico
            palavras_alerta = ["SAÍDA", "PRESTADO"]
            df['Atenção'] = df['Historico'].apply(
                lambda x: "⚠️" if any(p in str(x).upper() for p in palavras_alerta) else ""
            )
            
            st.success("PDF lido com sucesso!")
            st.dataframe(df, use_container_width=True)

            # Criar o arquivo Excel para download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Extrato')
            
            st.download_button(
                label="📥 Baixar Planilha Excel",
                data=output.getvalue(),
                file_name="extrato_convertido.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("O robô não encontrou 4 colunas nesse PDF. O formato pode ser diferente.")
    else:
        st.warning("Não consegui ler nenhuma tabela nesse PDF.")
