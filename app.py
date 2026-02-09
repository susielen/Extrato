import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(page_title="CONVERSOR DE EXTRATO COMPLETO", layout="wide")

st.title("🤖 ROBÔ DE EXTRATO COM SALDO")
st.write("ORGANIZANDO TUDO: DESCRIÇÃO COMPLETA, DÉBITO, CRÉDITO E SALDO FINAL.")

arquivo_pdf = st.file_uploader("SUBA O SEU PDF AQUI", type="pdf")

if arquivo_pdf:
    dados_extraidos = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                linhas = texto.split('\n')
                data_atual = ""
                historico_acumulado = ""
                valor_pendente = ""
                saldo_pendente = ""

                for linha in linhas:
                    # 1. BUSCA DATA (EX: 17/12)
                    match_data = re.search(r'^(\d{2}/\d{2})', linha)
                    
                    if match_data:
                        # ANTES DE COMEÇAR NOVO DIA, SALVA O ANTERIOR
                        if data_atual and historico_acumulado:
                            dados_extraidos.append([data_atual, historico_acumulado.strip().upper(), valor_pendente, saldo_pendente])
                        
                        data_atual = match_data.group(1)
                        conteudo = linha.replace(data_atual, "").strip()
                        
                        # 2. BUSCA VALORES (EX: 60,00- OU 3.091,00)
                        # PEGAMOS TODOS OS VALORES DA LINHA
                        valores = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}-?)', conteudo)
                        
                        if len(valores) >= 2:
                            # SE TEM DOIS VALORES, O PRIMEIRO É O LANÇAMENTO E O SEGUNDO É O SALDO
                            valor_pendente = valores[0]
                            saldo_pendente = valores[1]
                            historico_acumulado = conteudo
                            for v in valores:
                                historico_acumulado = historico_acumulado.replace(v, "")
                        elif len(valores) == 1:
                            valor_pendente = valores[0]
                            saldo_pendente = ""
                            historico_acumulado = conteudo.replace(valor_pendente, "")
                        else:
                            valor_pendente = ""
                            saldo_pendente = ""
                            historico_acumulado = conteudo
                    else:
                        # CONTINUAÇÃO DO HISTÓRICO (NOMES ABAIXO DO PIX)
                        if data_atual:
                            valores_cont = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}-?)', linha)
                            if valores_cont:
                                if not valor_pendente:
                                    valor_pendente = valores_cont[0]
                                elif not saldo_pendente and len(valores_cont) > 0:
                                    saldo_pendente = valores_cont[-1]
                            
                            texto_limpo = linha
                            for v in valores_cont:
                                texto_limpo = texto_limpo.replace(v, "")
                            historico_acumulado += " " + texto_limpo.strip()

                # SALVA O ÚLTIMO DA PÁGINA
                if data_atual:
                    dados_extraidos.append([data_atual, historico_acumulado.strip().upper(), valor_pendente, saldo_pendente])

    if dados_extraidos:
        tabela_final = []
        for d, h, v, s in dados_extraidos:
            debito = ""
            credito = ""
            
            # SEPARA ENTRADA E SAÍDA
            if "-" in v:
                debito = v.replace("-", "").strip()
            elif v != "":
                credito = v.strip()
            
            # LIMPA O SALDO
            saldo_final = s.strip()
            
            tabela_final.append([d, h, debito, credito, saldo_final])

        df = pd.DataFrame(tabela_final, columns=["DATA", "HISTÓRICO", "DÉBITO (SAÍDA)", "CRÉDITO (ENTRADA)", "SALDO FINAL"])
        
        # TUDO EM MAIÚSCULO
        df = df.astype(str).apply(lambda x: x.str.upper())
        # LIMPEZA DE LINHAS QUE SÃO APENAS SALDO SEM HISTÓRICO ÚTIL
        df = df[df["HISTÓRICO"] != ""]

        st.success("PLANILHA GERADA COM SUCESSO!")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # EXCEL
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='EXTRATO_BANCARIO')
        
        st.download_button(
            label="📥 BAIXAR PLANILHA EXCEL (.XLSX)",
            data=output.getvalue(),
            file_name="EXTRATO_ORGANIZADO.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
