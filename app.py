import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(page_title="MEU ROBÔ VOLTOU", layout="wide")

st.title("🤖 ROBÔ DE EXTRATO (VERSÃO ESTÁVEL)")
st.write("VOLTAMOS AO JEITO QUE LÊ TUDO: DATA, HISTÓRICO COMPLETO E SALDO NO FIM DO DIA.")

arquivo_pdf = st.file_uploader("COLOQUE O SEU PDF AQUI", type="pdf")

if arquivo_pdf:
    dados_lista = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                linhas = texto.split('\n')
                data_curr, hist_curr, val_curr, saldo_curr = "", "", "", ""

                for linha in linhas:
                    # 1. BUSCA DATA (PADRÃO 17/12 OU 17/12/2025)
                    match_dt = re.search(r'(\d{2}/\d{2}(?:/\d{4})?)', linha)
                    
                    if match_dt:
                        # ANTES DE COMEÇAR NOVO, SALVA O ANTERIOR
                        if data_curr and (val_curr or saldo_curr):
                            dados_lista.append([data_curr, hist_curr.strip().upper(), val_curr, saldo_curr])
                        
                        data_curr = match_dt.group(1)
                        # BUSCA VALORES (PEGA NÚMEROS COM VÍRGULA, COM '-' OU 'C/D')
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
                            # CONTINUAÇÃO DO HISTÓRICO (NOME DA PESSOA)
                            v_cont = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}\s?[CD-]?|(?<=\s)-?\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                            t_limpo = linha
                            for v in v_cont: t_limpo = t_limpo.replace(v, "")
                            hist_curr += " " + t_limpo.strip()
                            if v_cont:
                                if not val_curr: val_curr = v_cont[0]
                                saldo_curr = v_cont[-1]

                if data_curr:
                    dados_lista.append([data_curr, hist_curr.strip().upper(), val_curr, saldo_curr])

    if dados_lista:
        df = pd.DataFrame(dados_lista, columns=["DATA", "HISTORICO", "VALOR", "SALDO_B"])
        
        # COLOCA AS DATAS NA ORDEM CERTA
        df['DT_AUX'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce')
        if df['DT_AUX'].isnull().any():
            df['DT_AUX'] = pd.to_datetime(df['DATA'] + '/2025', format='%d/%m', errors='coerce')
        
        df = df.sort_values(by='DT_AUX').reset_index(drop=True)

        final_rows = []
        for i in range(len(df)):
            d, h = df.iloc[i]['DATA'], df.iloc[i]['HISTORICO']
            v = str(df.iloc[i]['VALOR']).upper().replace(" ", "")
            s = str(df.iloc[i]['SALDO_B']).upper().replace(" ", "")
            
            # SALDO SÓ NO FIM DO DIA
            saldo_dia = s if (i == len(df)-1 or d != df.iloc[i+1]['DATA']) else ""
            
            deb, cred = "", ""
            if "-" in v or "D" in v:
                deb = v.replace("-", "").replace("D", "").strip()
            else:
                cred = v.replace("C", "").strip()
            
            if h and (deb or cred):
                final_rows.append([d, h, deb, cred, saldo_dia])

        df_final = pd.DataFrame(final_rows, columns=["DATA", "HISTÓRICO", "DÉBITO", "CRÉDITO", "SALDO FINAL"])
        
        st.success("CONSEGUI! TUDO VOLTOU AO NORMAL.")
        st.dataframe(df_final, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='EXTRATO')
        st.download_button("📥 BAIXAR EXCEL AGORA", output.getvalue(), "extrato_restaurado.xlsx")
