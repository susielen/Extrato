import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
from datetime import datetime

st.set_page_config(page_title="CONVERSOR CAIXA ORGANIZADO", layout="wide")

st.title("🤖 ROBÔ CAIXA: DIA A DIA")
st.write("ORDENANDO POR DATA E MOSTRANDO O SALDO FINAL DE CADA DIA.")

arquivo_pdf = st.file_uploader("SUBA O EXTRATO DA CAIXA AQUI", type="pdf")

if arquivo_pdf:
    dados_brutos = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                linhas = texto.split('\n')
                data_atual, hist_acumulado, val_curr, saldo_curr = "", "", "", ""

                for linha in linhas:
                    # 1. BUSCA DATA (EX: 20/02/2025)
                    match_data = re.search(r'(\d{2}/\d{2}/\d{4})', linha)
                    
                    if match_data:
                        if data_atual and (val_curr or saldo_curr):
                            dados_brutos.append({"DATA": data_atual, "HIST": hist_acumulado, "VAL": val_curr, "SALDO": saldo_curr})
                        
                        data_atual = match_data.group(1)
                        # PEGA VALORES COM C/D OU SINAL (-)
                        valores = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}\s?[CD-]?|(?<=\s)-?\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                        
                        if len(valores) >= 2:
                            val_curr, saldo_curr = valores[-2], valores[-1]
                        elif len(valores) == 1:
                            val_curr, saldo_curr = valores[0], ""
                        else:
                            val_curr, saldo_curr = "", ""
                        
                        temp_h = linha.replace(data_atual, "")
                        for v in valores: temp_h = temp_h.replace(v, "")
                        hist_acumulado = re.sub(r'\d{6,}', '', temp_h).strip()
                    else:
                        if data_atual:
                            v_cont = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}\s?[CD-]?|(?<=\s)-?\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                            t_limpo = linha
                            for v in v_cont: t_limpo = t_limpo.replace(v, "")
                            hist_acumulado += " " + t_limpo.strip()
                            if v_cont:
                                if not val_curr: val_curr = v_cont[0]
                                if len(v_cont) > 1 or not saldo_curr: saldo_curr = v_cont[-1]

                if data_atual:
                    dados_brutos.append({"DATA": data_atual, "HIST": hist_acumulado, "VAL": val_curr, "SALDO": saldo_curr})

    if dados_brutos:
        # CRIANDO O DATAFRAME
        df = pd.DataFrame(dados_brutos)
        
        # CONVERTE DATA PARA ORDENAR CERTO
        df['DT_OBJ'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y')
        df = df.sort_values(by='DT_OBJ').reset_index(drop=True)

        tabela_limpa = []
        # LOGICA PARA MANTER SALDO SÓ NO ÚLTIMO LANÇAMENTO DO DIA
        for i in range(len(df)):
            d = df.iloc[i]['DATA']
            h = df.iloc[i]['HIST'].upper()
            v = df.iloc[i]['VAL'].upper().replace(" ", "")
            s = df.iloc[i]['SALDO'].upper().replace(" ", "")
            
            # SÓ MOSTRA O SALDO SE FOR A ÚLTIMA LINHA DO DIA OU A ÚLTIMA DA TABELA
            saldo_final = s if (i == len(df)-1 or d != df.iloc[i+1]['DATA']) else ""
            
            debito, credito = "", ""
            if "D" in v or "-" in v:
                debito = v.replace("D", "").replace("-", "").strip()
            elif "C" in v and "0,00" not in v:
                credito = v.replace("C", "").strip()
            elif v and "C" not in v and "D" not in v and "-" not in v:
                credito = v.strip()

            tabela_limpa.append([d, h, debito, credito, saldo_final])

        df_final = pd.DataFrame(tabela_limpa, columns=["DATA", "HISTÓRICO", "DÉBITO", "CRÉDITO", "SALDO DO DIA"])
        
        st.success("PLANILHA ORDENADA E LIMPA!")
        st.dataframe(df_final, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='EXTRATO')
        st.download_button("📥 BAIXAR EXCEL ORGANIZADO", output.getvalue(), "extrato_caixa_ordenado.xlsx")
