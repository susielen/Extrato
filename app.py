import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(page_title="SUPER CONVERSOR DE EXTRATO", layout="wide")

st.title("🤖 ROBÔ MULTI-EXTRATO")
st.write("ACEITA PADRÃO COM SINAL (-) OU PADRÃO CAIXA (C/D).")

arquivo_pdf = st.file_uploader("SUBA O SEU PDF (QUALQUER BANCO)", type="pdf")

if arquivo_pdf:
    dados_finais = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                linhas = texto.split('\n')
                data_curr, hist_curr, val_curr, saldo_curr = "", "", "", ""

                for linha in linhas:
                    # 1. BUSCA DATA (PADRÃO 17/12 OU 17/12/2025)
                    match_data = re.search(r'(\d{2}/\d{2}(?:/\d{4})?)', linha)
                    
                    if match_data:
                        # SALVA O LANÇAMENTO ANTERIOR ANTES DE COMEÇAR NOVO
                        if data_curr and (val_curr or saldo_curr):
                            dados_finais.append([data_curr, hist_curr.strip().upper(), val_curr, saldo_curr])
                        
                        data_curr = match_data.group(1)
                        # BUSCA VALORES (PEGA NÚMEROS COM VÍRGULA, PODENDO TER '-' OU 'C/D')
                        valores = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}\s?[CD-]?|(?<=\s)-?\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                        
                        if len(valores) >= 2:
                            val_curr, saldo_curr = valores[-2], valores[-1]
                        elif len(valores) == 1:
                            val_curr, saldo_curr = valores[0], ""
                        else:
                            val_curr, saldo_curr = "", ""
                        
                        temp_h = linha.replace(data_curr, "")
                        for v in valores: temp_h = temp_h.replace(v, "")
                        hist_curr = re.sub(r'\d{6,}', '', temp_h).strip() # LIMPA NÚMEROS LONGOS (DOCS)
                    else:
                        if data_curr:
                            # CONTINUAÇÃO DO HISTÓRICO (PEGA NOMES E DETALHES)
                            v_cont = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}\s?[CD-]?|(?<=\s)-?\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                            t_limpo = linha
                            for v in v_cont: t_limpo = t_limpo.replace(v, "")
                            hist_curr += " " + t_limpo.strip()
                            if v_cont:
                                if not val_curr: val_curr = v_cont[0]
                                elif not saldo_curr: saldo_curr = v_cont[-1]

                if data_curr:
                    dados_finais.append([data_curr, hist_curr.strip().upper(), val_curr, saldo_curr])

    if dados_finais:
        tabela_unificada = []
        for d, h, v, s in dados_finais:
            debito, credito = "", ""
            v_limpo = v.upper().replace(" ", "")
            
            # --- REGRA 1: SINAL NEGATIVO (-) ---
            if "-" in v_limpo:
                debito = v_limpo.replace("-", "").strip()
            # --- REGRA 2: LETRA D (SAÍDA CAIXA) ---
            elif "D" in v_limpo:
                debito = v_limpo.replace("D", "").strip()
            # --- REGRA 3: LETRA C OU POSITIVO (ENTRADA) ---
            elif v_limpo != "" and "0,00" not in v_limpo:
                credito = v_limpo.replace("C", "").strip()
            
            tabela_unificada.append([d, h, debito, credito, s.strip().upper()])

        df = pd.DataFrame(tabela_unificada, columns=["DATA", "HISTÓRICO", "DÉBITO (SAÍDA)", "CRÉDITO (ENTRADA)", "SALDO FINAL"])
        df = df.astype(str).apply(lambda x: x.str.upper())

        st.success("EXTRATO PROCESSADO COM SUCESSO!")
        st.dataframe(df, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='EXTRATO')
        st.download_button("📥 BAIXAR PLANILHA UNIFICADA", output.getvalue(), "extrato_final.xlsx")
