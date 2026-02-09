import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

# Título do Robô
st.set_page_config(page_title="CONVERSOR CAIXA FINAL", layout="wide")
st.title("🤖 MEU ROBÔ DA CAIXA")
st.write("ORGANIZO TUDO: DATAS EM ORDEM, HISTÓRICO COMPLETO E SALDO SÓ NO FIM DO DIA.")

arquivo_pdf = st.file_uploader("COLOQUE O EXTRATO DA CAIXA AQUI", type="pdf")

if arquivo_pdf:
    dados_lista = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                linhas = texto.split('\n')
                dt_atual, hist_acum, v_pend, s_pend = "", "", "", ""

                for linha in linhas:
                    # BUSCA DATA NO FORMATO DA CAIXA (DIA/MÊS/ANO) 
                    match_dt = re.search(r'(\d{2}/\d{2}/\d{4})', linha)
                    
                    if match_dt:
                        # SALVA O QUE JÁ TINHA ANTES DE COMEÇAR UM NOVO DIA
                        if dt_atual:
                            dados_lista.append([dt_atual, hist_acum.strip().upper(), v_pend, s_pend])
                        
                        dt_atual = match_dt.group(1)
                        # PROCURA VALORES COM C, D OU SINAL DE MENOS 
                        v_achados = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}\s?[CD-]?|(?<=\s)-?\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                        
                        if len(v_achados) >= 2:
                            v_pend, s_pend = v_achados[-2], v_achados[-1]
                        elif len(v_achados) == 1:
                            v_pend, s_pend = v_achados[0], ""
                        else:
                            v_pend, s_pend = "", ""
                        
                        # LIMPA O NÚMERO DO DOCUMENTO E VALORES DO HISTÓRICO
                        limpo = linha.replace(dt_atual, "")
                        for va in v_achados: limpo = limpo.replace(va, "")
                        hist_acum = re.sub(r'\d{6}', '', limpo).strip()
                    else:
                        # SE NÃO TEM DATA, É O NOME DA PESSOA (FAVORECIDO) 
                        if dt_atual:
                            v_cont = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2}\s?[CD-]?|(?<=\s)-?\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                            t_cont = linha
                            for vc in v_cont: t_cont = t_cont.replace(vc, "")
                            hist_acum += " " + t_cont.strip()
                            if v_cont:
                                if not v_pend: v_pend = v_cont[0]
                                s_pend = v_cont[-1]

                # NÃO ESQUECE O ÚLTIMO LANÇAMENTO
                if dt_atual:
                    dados_lista.append([dt_atual, hist_acum.strip().upper(), v_pend, s_pend])

    if dados_lista:
        df = pd.DataFrame(dados_lista, columns=["DATA", "HISTORICO", "VALOR", "SALDO_BRUTO"])
        
        # COLOCA AS DATAS NA ORDEM CERTA (DIA 01, 02, 03...)
        df['DT_AUX'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y')
        df = df.sort_values(by='DT_AUX').reset_index(drop=True)

        final_rows = []
        for i in range(len(df)):
            d, h = df.iloc[i]['DATA'], df.iloc[i]['HISTORICO']
            v = str(df.iloc[i]['VALOR']).upper().replace(" ", "")
            s = str(df.iloc[i]['SALDO_BRUTO']).upper().replace(" ", "")
            
            # SÓ MOSTRA O SALDO SE FOR A ÚLTIMA LINHA DAQUELE DIA 
            saldo_dia = s if (i == len(df)-1 or d != df.iloc[i+1]['DATA']) else ""
            
            deb, cred = "", ""
            if "D" in v or "-" in v:
                deb = v.replace("D", "").replace("-", "").strip()
            else:
                cred = v.replace("C", "").strip()
            
            if h != "" or v != "":
                final_rows.append([d, h, deb, cred, saldo_dia])

        df_final = pd.DataFrame(final_rows, columns=["DATA", "HISTÓRICO", "DÉBITO", "CRÉDITO", "SALDO FINAL"])
        
        st.success("CONSEGUI! AQUI ESTÁ SUA PLANILHA:")
        st.dataframe(df_final, use_container_width=True, hide_index=True)

        # AGORA O BOTÃO DE BAIXAR SEMPRE APARECE
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='EXTRATO')
        
        st.download_button(
            label="📥 CLIQUE AQUI PARA BAIXAR O EXCEL",
            data=output.getvalue(),
            file_name="extrato_caixa_perfeito.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("NÃO ENCONTREI NADA NO PDF. VERIFIQUE SE ELE NÃO É UMA FOTO.")
