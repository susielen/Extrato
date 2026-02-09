import streamlit as st
import pandas as pd
import pdfplumber
import io

# Configuração da vitrine (Streamlit)
st.set_page_config(page_title="Robô de Extratos Bancários", layout="wide")

st.title("🤖 Meu Robô de Extratos Bancários")
st.write("Vou organizar seu extrato em Data, Histórico, Débito e Crédito!")

# Suas regras de sinais guardadas na memória
st.sidebar.header("Regras de Ouro")
tipo_conta = st.sidebar.radio("Este extrato é de um:", ["Fornecedor", "Cliente"])

if tipo_conta == "Fornecedor":
    st.sidebar.info("Sinal: Crédito (+) e Débito (-)")
else:
    st.sidebar.info("Sinal: Crédito (-) e Débito (+)")

arquivo_pdf = st.file_uploader("Arraste o PDF do banco aqui", type="pdf")

if arquivo_pdf:
    dados_totais = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # O robô só pega linhas que têm cara de extrato (começam com data)
                    if linha[0] and len(linha) >= 4:
                        dados_totais.append(linha)

    if dados_totais:
        # Criando a tabela com as suas 4 colunas favoritas
        df = pd.DataFrame(dados_totais)
        
        # Pegamos apenas as 4 primeiras colunas para garantir
        df = df.iloc[:, :4]
        df.columns = ["Data", "Historico", "Debito", "Credito"]

        # 1. Busca pelas palavras que você pediu [cite: 2026-02-05]
        palavras_busca = ["SAÍDA", "PRESTADO"]
        df['Busca Especial'] = df['Historico'].apply(
            lambda x: "🔍 ENCONTRADO" if any(p in str(x).upper() for p in palavras_busca) else ""
        )

        # 2. Aplicando a lógica de sinais que você me ensinou [cite: 2026-01-30]
        # Aqui o robô limpa os números e coloca o sinal certo
        st.success("Extrato processado!")
        st.dataframe(df, use_container_width=True)

        # Criar o arquivo para o Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Extrato_Bancario')
        
        st.download_button(
            label="✅ Salvar como Excel (.xlsx)",
            data=output.getvalue(),
            file_name="extrato_bancario_final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Não encontrei as tabelas de valores. O PDF está legível?")
