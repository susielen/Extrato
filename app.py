import streamlit as st
import pandas as pd
import pdfplumber
import io

st.set_page_config(page_title="Planilha de Extrato Real", layout="wide")

st.title("📋 Minha Planilha Organizada")
st.write("Vou arrumar as colunas para que fiquem exatamente nos lugares certos.")

arquivo_pdf = st.file_uploader("Suba o PDF aqui", type="pdf")

if arquivo_pdf:
    dados_finais = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # O robô remove tudo que for vazio ou apenas espaço
                    linha_limpa = [item.strip() if item else "" for item in linha if item is not None]
                    
                    # Se a linha tiver pelo menos 3 ou 4 informações, ela é um lançamento!
                    if len(linha_limpa) >= 3:
                        # Se a linha estiver curta, o robô coloca "espaço" para completar 4 colunas
                        while len(linha_limpa) < 4:
                            linha_limpa.append("")
                        
                        dados_finais.append(linha_limpa[:4])

    if dados_finais:
        # Criamos a planilha com os nomes que você quer
        df = pd.DataFrame(dados_finais, columns=["Data", "Histórico", "Débito (Saída)", "Crédito (Entrada)"])
        
        # O robô remove linhas que são apenas títulos repetidos
        df = df[~df["Data"].str.contains("Data|Saldo", case=False, na=False)]

        st.success("Tabela organizada com sucesso!")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Prepara para salvar no Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Extrato_Limpo')
        
        st.download_button(
            label="📥 Baixar Planilha Arrumada",
            data=output.getvalue(),
            file_name="extrato_perfeito.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
