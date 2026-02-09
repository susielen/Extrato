import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(page_title="ROBÔ BANCÁRIO UNIVERSAL", layout="wide")

st.title("🤖 ROBÔ MULTI-BANCOS")
st.write("ORGANIZADO: DATAS EM ORDEM, HISTÓRICO COMPLETO E REGRAS DE C/D OU SINAL (+/-).")

arquivo_pdf = st.file_uploader("SUBA O SEU PDF (CAIXA, SANTANDER, ITAÚ, ETC.)", type="pdf")

if arquivo_pdf:
    dados_brutos = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                linhas = texto.split('\n')
                data_curr, hist_curr, val_curr, saldo_curr = "", "", "", ""

                for linha in linhas:
                    # 1. BUSCA DATA (EX: 28/02/2025 OU 28/02)
                    match_dt = re.search(r'(\d{2}/\d{2}(?:/\d{4})?)', linha)
                    
                    if match_dt:
                        # SALVA O LANÇAMENTO ANTERIOR ANTES DE COMEÇAR NOVO
                        if data_curr and (val_curr or saldo_curr):
                            dados_brutos.append({"DATA": data_curr, "HIST": hist_curr.strip().upper(), "VAL": val_curr, "SALDO": saldo_curr})
                        
                        data_curr = match_dt.group(1)
                        # BUSCA VALORES (RECONHECE NÚMEROS COM , E SINAIS/LETRAS AO LADO)
                        v_achados = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}\s?[CD-]?|(?<=\s)-?\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                        
                        if len(v_achados) >= 2:
                            val_curr, saldo_curr = v_achados[-2], v_achados[-1]
                        elif len(v_achados) == 1:
                            val_curr, saldo_curr = v_achados[0], ""
                        else:
                            val_curr, saldo_curr = "", ""
                        
                        temp_h = linha.replace(data_curr, "")
                        for v in v_achados: temp_h = temp_h.replace(v, "")
                        hist_curr = re.sub(r'\d{6,}', '', temp_h).strip()
                    else:
                        if data_curr:
                            # CONTINUAÇÃO DO HISTÓRICO (NOME DA PESSOA ABAIXO)
                            v_cont = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}\s?[CD-]?|(?<=\s)-?\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                            t_limpo = linha
                            for v in v_cont: t_limpo = t_limpo.replace(v, "")
                            hist_curr += " " + t_limpo.strip()
                            if v_cont:
                                if not val_curr: val_curr = v_cont[0]
                                saldo_curr = v_cont[-1]

                if data_curr:
                    dados_brutos.append({"DATA": data_curr, "HIST": hist_curr.strip().upper(), "VAL": val_curr, "SALDO": saldo_curr})

    if dados_brutos:
        df = pd.DataFrame(dados_brutos)
        
        # --- GARANTE AS DATAS EM ORDEM (01, 02, 03...) ---
        df['DT_AUX'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce')
        if df['DT_AUX'].isnull().any():
            df['DT_AUX'] = pd.to_datetime(df['DATA'] + '/2025', format='%d/%m/%Y', errors='coerce')
        
        df = df.sort_values(by='DT_AUX').reset_index(drop=True)

        tabela_final = []
        for i in range(len(df)):
            d, h = df.iloc[i]['DATA'], df.iloc[i]['HIST']
            v = str(df.iloc[i]['VAL']).upper().replace(" ", "")
            s = str(df.iloc[i]['SALDO']).upper().replace(" ", "")
            
            # MOSTRA O SALDO APENAS NO ÚLTIMO LANÇAMENTO DO DIA
            saldo_dia = s if (i == len(df)-1 or d != df.iloc[i+1]['DATA']) else ""
            
            deb, cred = "", ""
            # APLICAÇÃO DAS REGRAS UNIVERSAIS (CAIXA, BB, ITAÚ, SANTANDER)
            if "D" in v or "-" in v:
                deb = v.replace("D", "").replace("-", "").strip()
            elif "C" in v:
                cred = v.replace("C", "").strip()
            elif v != "" and "0,00" not in v:
                # Caso sem sinal/letra (assume crédito se não tiver indicador de débito)
                cred = v.strip()
            
            if h and (deb or cred):
                tabela_final.append([d, h, deb, cred, saldo_dia])

        df_final = pd.DataFrame(tabela_final, columns=["DATA", "HISTÓRICO", "DÉBITO (SAÍDA)", "CRÉDITO (ENTRADA)", "SALDO FINAL"])
        
        st.success("PLANILHA PRONTA E ORGANIZADA!")
        st.dataframe(df_final, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='EXTRATO')
        st.download_button("📥 BAIXAR EXCEL AGORA", output.getvalue(), "extrato_universal.xlsx")
