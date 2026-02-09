import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(page_title="Conversor de Extrato", layout="wide")

st.title("🤖 Robô de Extrato Bancário")
st.write("Separando as entradas no Crédito e as saídas no Débito.")

arquivo_pdf = st.file_uploader("Suba o PDF do banco", type="pdf")

if arquivo_pdf:
    lista_final = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # Limpamos a linha de espaços vazios
                    col = [str(c).strip() if c else "" for c in linha]
                    
                    # O robô só trabalha se a linha começar com uma DATA (ex: 17/12)
                    if col and re.match(r'\d{2}/\d{2}', col[0]):
                        data = col[0]
                        historico = col[1]
                        
                        # Procuramos o valor (geralmente onde tem vírgula)
                        valor_texto = ""
                        for c in col[2:]:
                            if "," in c:
                                valor_texto = c
                                break
                        
                        debito = ""
                        credito = ""
                        
                        # REGRA DO SEU ROBÔ:
                        # Se tiver o sinal "-" ou "D", é SAÍDA (DÉBITO)
                        if "-" in valor_texto or "D" in valor_texto.upper():
                            debito = valor_texto.replace("-", "").replace("D", "").strip()
                        # Se não tiver sinal ou tiver "C", é ENTRADA (CRÉDITO)
                        elif valor_texto != "":
                            credito = valor_texto.replace("C", "").strip()
                            
                        lista_final.append([data, historico, debito, credito])

    if lista_final:
        df = pd.DataFrame(lista_final, columns=["Data", "Histórico", "Débito (Saída)", "Crédito (Entrada)"])
        
        st.success("Tabela gerada com sucesso!")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Criar o arquivo Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Extrato_Organizado')
        
        st.download_button(
            label="📥 Baixar Planilha Excel",
            data=output.getvalue(),
            file_name="extrato_separado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
