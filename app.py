import streamlit as st
import pandas as pd
import pdfplumber
import io

# Configuração da página para o modo largo (ocupa a tela toda)
st.set_page_config(page_title="Minha Planilha de Extrato", layout="wide")

st.title("📋 Gerador de Planilha de Extrato")
st.write("Vou listar todos os lançamentos do seu PDF dia a dia.")

# Upload do arquivo
arquivo_pdf = st.file_uploader("Arraste o extrato em PDF aqui", type="pdf")

if arquivo_pdf:
    todos_os_lancamentos = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            # O robô olha para cada página e procura a tabelinha
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # O robô limpa e remove espaços em branco de cada linha
                    linha_limpa = [str(item).strip() if item else "" for item in linha]
                    
                    # Verificamos se a linha tem cara de lançamento (se tem data ou valor)
                    if any(linha_limpa):
                        # Pegamos as 4 colunas principais: Data, Histórico, Débito e Crédito
                        todos_os_lancamentos.append(linha_limpa[:4])

    if todos_os_lancamentos:
        # Transformando em uma tabela do computador (DataFrame)
        df = pd.DataFrame(todos_os_lancamentos, columns=["Data", "Histórico", "Débito (Saída)", "Crédito (Entrada)"])
        
        # Removemos linhas que por acaso sejam apenas os títulos repetidos
        df = df[df["Data"].str.lower() != "data"] 

        st.success(f"Encontrei {len(df)} lançamentos no seu extrato!")
        
        # Mostra a planilha bonitona na tela
        st.subheader("Visualização dos Lançamentos Dia a Dia")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Botão para baixar o arquivo para o seu computador
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Lançamentos_Diários')
        
        st.download_button(
            label="📥 Baixar Planilha Completa (.xlsx)",
            data=output.getvalue(),
            file_name="extrato_dia_a_dia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Não consegui encontrar os lançamentos. O PDF está protegido ou sem tabelas?")
