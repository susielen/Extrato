import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def limpar_valor(texto):
    """Extrai o número e decide se é Débito ou Crédito"""
    if not texto: return 0.0, "C"
    t = str(texto).upper()
    # Identifica saída se tiver sinal de menos ou a letra D
    tipo = "D" if ('-' in t or 'D' in t) else "C"
    # Remove tudo que não é dígito ou vírgula
    numeros = re.sub(r'[^\d,]', '', t)
    try:
        valor = float(numeros.replace(',', '.'))
    except:
        valor = 0.0
    return valor, tipo

def extrair_dados_pdf(arquivo_pdf, col_data, col_hist, col_valor):
    dados = []
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if not tabela: continue
            
            for linha in tabela:
                # Remove linhas que são claramente cabeçalhos ou vazias
                if not linha or len(linha) <= max(col_data, col_hist, col_valor): continue
                
                txt_data = str(linha[col_data])
                # Tenta validar se a célula da data parece uma data (ex: 01/01 ou 01/01/2026)
                if not re.search(r'\d{2}/\d{2}', txt_data): continue
                
                v_num, v_tipo = limpar_valor(linha[col_valor])
                
                dados.append({
                    'Data_Bruta': pd.to_datetime(txt_data, dayfirst=True, errors='coerce'),
                    'Data': txt_data,
                    'Histórico': linha[col_hist],
                    'Débito': v_num if v_tipo == "D" else None,
                    'Crédito': v_num if v_tipo == "C" else None
                })
    return dados

# --- INTERFACE STREAMLIT ---
st.title("🤖 Super Transformador de Extratos")
st.sidebar.header("🏢 Dados do Relatório")
empresa = st.sidebar.text_input("Empresa")
banco = st.sidebar.text_input("Banco")

upload = st.file_uploader("Arraste seu PDF aqui", type="pdf")

if upload:
    with pdfplumber.open(upload) as pdf:
        # Pega uma amostra para o usuário configurar
        amostra = pdf.pages[0].extract_table()
    
    if amostra:
        st.info("Abaixo está uma amostra do seu PDF. Diga ao robô qual coluna é qual:")
        st.table(amostra[:3]) # Mostra as 3 primeiras linhas
        
        c1, c2, c3 = st.columns(3)
        cols = [f"Coluna {i}" for i in range(len(amostra[0]))]
        idx_d = c1.selectbox("Data", range(len(cols)), index=0)
        idx_h = c2.selectbox("Histórico", range(len(cols)), index=1)
        idx_v = c3.selectbox("Valor", range(len(cols)), index=len(cols)-1)

        if st.button("✨ Transformar Agora"):
            lista_final = extrair_dados_pdf(upload, idx_d, idx_h, idx_v)
            df = pd.DataFrame(lista_final)
            
            if not df.empty:
                # Ordenar por data real e depois formatar
                df = df.sort_values('Data_Bruta').drop(columns=['Data_Bruta'])
                
                st.success("Transformado com sucesso!")
                st.dataframe(df)

                # Gerar Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Título
                    pd.DataFrame([[f"EMPRESA: {empresa}"], [f"BANCO: {banco}"]]).to_excel(writer, index=False, header=False, startrow=0)
                    # Dados
                    df.to_excel(writer, index=False, startrow=3, sheet_name='Resultado')
                
                st.download_button("📥 Baixar Planilha Pronta", output.getvalue(), f"Extrato_{empresa}.xlsx")
            else:
                st.error("Não consegui extrair dados. Verifique se as colunas estão corretas.")
