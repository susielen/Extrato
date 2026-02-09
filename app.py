import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(page_title="CONVERSOR MULTI-BANCO", layout="wide")

st.title("🤖 MEU ROBÔ BANCÁRIO (CAIXA & SANTANDER)")
st.write("ORGANIZANDO TUDO: DATAS EM ORDEM, HISTÓRICO COMPLETO E SALDO NO FIM DO DIA.")

arquivo_pdf = st.file_uploader("COLOQUE O SEU PDF AQUI", type="pdf")

if arquivo_pdf:
    dados_lista = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            # ESTRATÉGIA 1: TENTAR LER COMO TABELA (EX: CAIXA)
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    col = [str(c).replace('\n', ' ').strip() if c else "" for c in linha]
                    match_dt = re.search(r'(\d{2}/\d{2}/\d{4}|\d{2}/\d{2})', col[0])
                    if match_dt:
                        data = match_dt.group(1)
                        # Tenta pegar valor e saldo de tabelas
                        v_achados = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}\s?[CD-]?|(?<=\s)-?\d{1,3}(?:\.\d{3})*,\d{2})', " ".join(col))
                        if len(v_achados) >= 1:
                            v = v_achados[0]
                            s = v_achados[-1] if len(v_achados) > 1 else ""
                            h = " ".join(col).replace(data, "").replace(v, "").replace(s, "").strip()
                            dados_lista.append({"DATA": data, "HIST": h, "VAL": v, "SALDO": s})

            # ESTRATÉGIA 2: SE NÃO ACHOU NADA, TENTA LER COMO TEXTO (EX: SANTANDER)
            if not dados_lista:
                texto = pagina.extract_text()
                if texto:
                    linhas = texto.split('\n')
                    for l in linhas:
                        match_dt = re.search(r'^(\d{2}/\d{2}(?:/\d{4})?)', l)
                        if match_dt:
                            data = match_dt.group(1)
                            v_achados = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}-?|(?<=\s)-?\d{1,3}(?:\.\d{3})*,\d{2})', l)
                            if v_achados:
                                v = v_achados[0]
                                s = v_achados[-1] if len(v_achados) > 1 else ""
                                h = l.replace(data, "").replace(v, "").replace(s, "").strip()
                                dados_lista.append({"DATA": data, "HIST": h, "VAL": v, "SALDO": s})

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        
        # Ajusta data para ordenação (considerando 2025/2026 se não tiver ano)
        df['DT_AUX'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce')
        if df['DT_AUX'].isnull().any():
            df['DT_AUX'] = pd.to_datetime(df['DATA'] + '/2025', format='%d/%m/%Y', errors='coerce')
        
        df = df.sort_values(by='DT_AUX').reset_index(drop=True)

        final_rows = []
        for i in range(len(df)):
            d, h = df.iloc[i]['DATA'], df.iloc[i]['HIST'].upper()
            v = str(df.iloc[i]['VAL']).upper().replace(" ", "")
            s = str(df.iloc[i]['SALDO']).upper().replace(" ", "")
            
            # Saldo apenas no fim do dia
            saldo_dia = s if (i == len(df)-1 or d != df.iloc[i+1]['DATA']) else ""
            
            deb, cred = "", ""
            # Regra para Saídas (Sinal - ou Letra D)
            if "-" in v or "D" in v:
                deb = v.replace("-", "").replace("D", "").strip()
            else:
                cred = v.replace("C", "").strip()
            
            if h and (deb or cred):
                final_rows.append([d, h, deb, cred, saldo_dia])

        df_final = pd.DataFrame(final_rows, columns=["DATA", "HISTÓRICO", "DÉBITO", "CRÉDITO", "SALDO FINAL"])
        
        st.success("EXTRATO PROCESSADO!")
        st.dataframe(df_final, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='EXTRATO')
        st.download_button("📥 BAIXAR EXCEL AGORA", output.getvalue(), "extrato_unificado.xlsx")
    else:
        st.error("NÃO CONSEGUI LER ESSE PDF. ELE PODE ESTAR PROTEGIDO OU SER UMA FOTO.")
