import streamlit as st
import pandas as pd
import pdfplumber
import io

st.set_page_config(page_title="MEU ROBÔ DA CAIXA", layout="wide")

st.title("🤖 MEU ROBÔ DA CAIXA")
st.write("ORGANIZO TUDO: DATAS EM ORDEM, HISTÓRICO COMPLETO E SALDO SÓ NO FIM DO DIA.")

arquivo_pdf = st.file_uploader("COLOQUE O EXTRATO DA CAIXA AQUI", type="pdf")

if arquivo_pdf:
    dados_extraidos = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            # AQUI ESTÁ O SEGREDO: MANDAR O ROBÔ EXTRAIR A TABELA DIRETAMENTE
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela:
                    # Limpamos os espaços e removemos None
                    linha_limpa = [str(item).strip() if item else "" for item in linha]
                    
                    # Verificamos se a linha começa com uma data (ex: 28/02/2025)
                    if linha_limpa and '/' in linha_limpa[0]:
                        # Na Caixa, geralmente temos: Data, Nr. Doc, Histórico, Favorecido, CPF, Valor, Saldo
                        # Vamos pegar os campos que você precisa
                        data = linha_limpa[0].split('-')[0] # Pega só a data, tira a hora
                        historico = f"{linha_limpa[2]} {linha_limpa[3]}".strip() # Junta Histórico + Favorecido
                        valor = linha_limpa[5]
                        saldo = linha_limpa[6]
                        
                        dados_extraidos.append([data, historico.upper(), valor.upper(), saldo.upper()])

    if dados_extraidos:
        df = pd.DataFrame(dados_extraidos, columns=["DATA", "HISTORICO", "VALOR", "SALDO_BRUTO"])
        
        # COLOCA AS DATAS NA ORDEM CERTA (DIA 01, 02, 03...)
        df['DT_AUX'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y', errors='coerce')
        df = df.dropna(subset=['DT_AUX']).sort_values(by='DT_AUX').reset_index(drop=True)

        final_rows = []
        for i in range(len(df)):
            d, h = df.iloc[i]['DATA'], df.iloc[i]['HISTORICO']
            v = df.iloc[i]['VALOR'].replace(" ", "")
            s = df.iloc[i]['SALDO_BRUTO'].replace(" ", "")
            
            # SÓ MOSTRA O SALDO SE FOR A ÚLTIMA LINHA DAQUELE DIA
            saldo_dia = s if (i == len(df)-1 or d != df.iloc[i+1]['DATA']) else ""
            
            deb, cred = "", ""
            # REGRA CAIXA: D É DÉBITO, C É CRÉDITO
            if "D" in v:
                deb = v.replace("D", "").strip()
            elif "C" in v:
                cred = v.replace("C", "").strip()
            
            # Removemos linhas que não são lançamentos reais (como saldo anterior)
            if "SALDO" not in h:
                final_rows.append([d, h, deb, cred, saldo_dia])

        df_final = pd.DataFrame(final_rows, columns=["DATA", "HISTÓRICO", "DÉBITO", "CRÉDITO", "SALDO FINAL"])

        st.success(f"CONSEGUI! ENCONTREI {len(df_final)} LANÇAMENTOS.")
        st.dataframe(df_final, use_container_width=True, hide_index=True)

        # AGORA O BOTÃO DE BAIXAR
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='EXTRATO')
        
        st.download_button(
            label="📥 CLIQUE AQUI PARA BAIXAR O EXCEL",
            data=output.getvalue(),
            file_name="extrato_caixa_final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("AINDA NÃO CONSEGUI LER OS DADOS. PODE SER O FORMATO DA TABELA.")
