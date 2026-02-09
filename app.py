import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(page_title="CONVERSOR DE EXTRATO COMPLETO", layout="wide")

st.title("🤖 ROBÔ DE EXTRATO BANCÁRIO")
st.write("ORGANIZANDO: DATA, HISTÓRICO COMPLETO, DÉBITO, CRÉDITO E SALDO FINAL.")

arquivo_pdf = st.file_uploader("SUBA O SEU PDF AQUI", type="pdf")

if arquivo_pdf:
    dados_finais = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                linhas = texto.split('\n')
                data_atual = ""
                historico_acumulado = ""
                valor_lancamento = ""
                saldo_linha = ""

                for linha in linhas:
                    # 1. BUSCA DATA NO INÍCIO DA LINHA (EX: 17/12)
                    match_data = re.search(r'^(\d{2}/\d{2})', linha)
                    
                    if match_data:
                        # SALVA O LANÇAMENTO ANTERIOR SE EXISTIR
                        if data_atual and (valor_lancamento or saldo_linha):
                            dados_finais.append([data_atual, historico_acumulado.strip().upper(), valor_lancamento, saldo_linha])
                        
                        data_atual = match_data.group(1)
                        conteudo = linha.replace(data_atual, "").strip()
                        
                        # 2. BUSCA TODOS OS VALORES NA LINHA (DINHEIRO)
                        valores = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}-?)', conteudo)
                        
                        if len(valores) >= 2:
                            valor_lancamento = valores[-2] # PENÚLTIMO É O LANÇAMENTO
                            saldo_linha = valores[-1]      # ÚLTIMO É O SALDO
                            # LIMPA O HISTÓRICO DOS VALORES
                            temp_hist = conteudo
                            for v in valores: temp_hist = temp_hist.replace(v, "")
                            historico_acumulado = temp_hist.strip()
                        elif len(valores) == 1:
                            valor_lancamento = valores[0]
                            saldo_linha = ""
                            historico_acumulado = conteudo.replace(valor_lancamento, "").strip()
                        else:
                            valor_lancamento = ""
                            saldo_linha = ""
                            historico_acumulado = conteudo
                    else:
                        # CONTINUAÇÃO DE HISTÓRICO OU VALORES EM LINHAS SEPARADAS
                        if data_atual:
                            valores_cont = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}-?)', linha)
                            if valores_cont:
                                if len(valores_cont) >= 2:
                                    valor_lancamento = valores_cont[-2]
                                    saldo_linha = valores_cont[-1]
                                else:
                                    # SE SÓ TEM UM VALOR E JÁ TEMOS O LANÇAMENTO, ELE É O SALDO
                                    if valor_lancamento:
                                        saldo_linha = valores_cont[0]
                                    else:
                                        valor_lancamento = valores_cont[0]
                            
                            # JUNTA O TEXTO AO HISTÓRICO
                            texto_limpo = linha
                            for v in valores_cont: texto_limpo = texto_limpo.replace(v, "")
                            if texto_limpo.strip():
                                historico_acumulado += " " + texto_limpo.strip()

                # SALVA O ÚLTIMO DA PÁGINA
                if data_atual:
                    dados_finais.append([data_atual, historico_acumulado.strip().upper(), valor_lancamento, saldo_linha])

    if dados_finais:
        tabela_pronta = []
        for d, h, v, s in dados_finais:
            debito, credito = "", ""
            # REGRA: SE TEM "-" É DÉBITO, SENÃO É CRÉDITO
            if "-" in v:
                debito = v.replace("-", "").strip()
            elif v:
                credito = v.strip()
            
            tabela_pronta.append([d, h, debito, credito, s.strip()])

        df = pd.DataFrame(tabela_pronta, columns=["DATA", "HISTÓRICO", "DÉBITO (SAÍDA)", "CRÉDITO (ENTRADA)", "SALDO FINAL"])
        df = df.astype(str).apply(lambda x: x.str.upper())

        st.success("PLANILHA ORGANIZADA!")
        st.dataframe(df, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='EXTRATO')
        
        st.download_button(label="📥 BAIXAR EXCEL (.XLSX)", data=output.getvalue(), 
                           file_name="EXTRATO_DIA_A_DIA.xlsx", 
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
