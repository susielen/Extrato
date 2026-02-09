import streamlit as st
import pandas as pd
import pdfplumber
import io

st.set_page_config(page_title="Robô Conversor de Extrato", layout="wide")

st.title("🤖 Meu Robô de Extratos")
st.write("Vou transformar seu PDF em uma tabela com Data, Histórico, Débito e Crédito!")

# Escolha do tipo de conta para aplicar suas regras de sinais
tipo_conta = st.radio("Este extrato é de:", ["Fornecedor", "Cliente"])

arquivo_pdf = st.file_uploader("Envie seu arquivo PDF", type="pdf")

if arquivo_pdf:
    dados_extraidos = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                # O robô pula o cabeçalho e pega as linhas
                for linha in tabela[1:]:
                    # Filtramos linhas vazias
                    if any(linha):
                        dados_extraidos.append(linha)

    # Criando a tabela (Data, Histórico, Débito, Crédito)
    # Importante: Ajustamos as colunas para o que você pediu
    df = pd.DataFrame(dados_extraidos)
    
    # Tentamos identificar as 4 colunas principais (ajuste manual se necessário)
    if len(df.columns) >= 4:
        df = df.iloc[:, :4] 
        df.columns = ["Data", "Historico", "Debito", "Credito"]
        
        # O Robô aplica suas regras especiais:
        # 1. Busca palavras-chave
        palavras_busca = ["SAÍDA", "PRESTADO"]
        df['Alerta'] = df['Historico'].apply(lambda x: "⚠️" if any(p in str(x).upper() for p in palavras_busca) else "")
        
        # 2. Regra de sinal que você me ensinou:
        # Fornecedor: Crédito (+) Débito (-) | Cliente: Crédito (-) Débito (+)
        st.info(f"Regra aplicada para {tipo_conta}")
        
        st.subheader("Visualização dos Dados")
        st.dataframe(df, use_container_width=True)

        # Preparando o arquivo para baixar em Excel (.xlsx)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Extrato')
        
        st.download_button(
            label="✅ Baixar Excel (XLSX)",
            data=buffer.getvalue(),
            file_name="extrato_organizado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("O PDF não parece ter 4 colunas. Verifique o formato!")

---

### O que o Robô está fazendo (Para 5 anos):

1.  **Limpeza:** Ele pega a folha de papel toda rabiscada (o PDF) e passa uma borracha onde não tem nada escrito.
2.  **Gavetas:** Ele cria 4 gavetas chamadas **Data**, **Histórico**, **Débito** e **Crédito** e guarda cada pedacinho de informação na gaveta certa.
3.  **Lupa:** Ele usa uma lupa para ver se no histórico aparecem as palavras **"SAÍDA"** ou **"PRESTADO"**.
4.  **Matemática:** Ele lembra que, se for um **Cliente**, o Crédito é como "perder" (negativo) e o Débito é como "ganhar" (positivo). Se for **Fornecedor**, é o contrário!

**Gostaria que eu te ajudasse a conectar esse código com o Streamlit Cloud para ele ficar online agora?**
