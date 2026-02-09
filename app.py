import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(page_title="Conversor de Extrato MAIÚSCULO", layout="wide")

st.title("🤖 Robô de Extrato (Tudo em Maiúsculo)")
st.write("Vou organizar seu extrato com a descrição completa e tudo em letras grandes.")

arquivo_pdf = st.file_uploader("Suba o seu PDF aqui", type="pdf")

if arquivo_pdf:
    dados_finais = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                linhas = texto.split('\n')
                data_atual = ""
                historico_acumulado = ""
                valor_pendente = ""

                for linha in linhas:
                    # 1. Tenta achar uma data (ex: 17/12)
                    match_data = re.search(r'^(\d{2}/\d{2})', linha)
                    
                    if match_data:
                        # Salva o lançamento anterior antes de começar o novo
                        if data_atual and historico_acumulado:
                            dados_finais.append([data_atual, historico_acumulado.strip().upper(), valor_pendente])
                        
                        data_atual = match_data.group(1)
                        conteudo = linha.replace(data_atual, "").strip()
                        
                        # 2. Procura o valor financeiro
                        match_valor = re.search(r'(\d{1,3}(?:\.\d{3})*,\d{2}-?)', conteudo)
                        if match_valor:
                            valor_pendente = match_valor.group(1)
                            historico_acumulado = conteudo.replace(valor_pendente, "").strip()
                        else:
                            valor_pendente = ""
                            historico_acumulado = conteudo
                    else:
                        # Continuação do histórico (ex: nome da pessoa abaixo do PIX)
                        if data_atual:
                            match_valor_cont = re.search(r'(\d{1,3}(?:\.\d{3})*,\d{2}-?)', linha)
                            if match_valor_cont:
                                valor_pendente = match_valor_cont.group(1)
                                historico_acumulado += " " + linha.replace(valor_pendente, "").strip()
                            else:
                                historico_acumulado += " " + linha.strip()

                if data_atual:
                    dados_finais.append([data_atual, historico_acumulado.strip().upper(), valor_pendente])

    if dados_finais:
        tabela_organizada = []
        for lancamento in dados_finais:
            dt, hist, val = lancamento
            debito = ""
            credito = ""
            
            # Regra de Entrada/Saída
            if "-" in val:
                debito = val.replace("-", "").strip()
            elif val != "":
                credito = val.strip()
            
            # Colocamos TUDO em maiúsculo aqui antes de mandar para a lista
            tabela_organizada.append([dt, hist, debito, credito])

        df = pd.DataFrame(tabela_organizada, columns=["DATA", "HISTÓRICO", "DÉBITO (SAÍDA)", "CRÉDITO (ENTRADA)"])
        
        # Garante que até os títulos e textos da planilha fiquem em maiúsculo
        df = df.astype(str).apply(lambda x: x.str.upper())

        st.success("Tabela gerada com sucesso e tudo em MAIÚSCULO!")
        st.dataframe(df, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='EXTRATO')
        
        st.download_button(
            label="📥 BAIXAR PLANILHA EM EXCEL",
            data=output.getvalue(),
            file_name="EXTRATO_MAIUSCULO.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
