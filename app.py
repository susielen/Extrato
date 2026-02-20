import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def extrair_valor(texto):
    if not texto: return 0.0, "C"
    texto_limpo = str(texto).upper().replace('R$', '').strip()
    e_saida = '-' in texto_limpo or 'D' in texto_limpo
    apenas_numeros = re.sub(r'[^\d,]', '', texto_limpo)
    try:
        valor_float = float(apenas_numeros.replace(',', '.'))
    except:
        valor_float = 0.0
    return valor_float, "D" if e_saida else "C"

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Robô de Extratos Pro", layout="wide")
st.title("🤖 Robô de Extratos Bancários")

# Sidebar para informações da Empresa e Banco
st.sidebar.header("📋 Identificação")
nome_empresa = st.sidebar.text_input("Nome da Empresa", "Minha Empresa Ltda")
nome_banco = st.sidebar.text_input("Nome do Banco", "Banco Exemplo")

arquivo_pdf = st.file_uploader("Suba o PDF do extrato", type=["pdf"])

if arquivo_pdf:
    # 1. Leitura Inicial para mapeamento de colunas
    with pdfplumber.open(arquivo_pdf) as pdf:
        primeira_pagina = pdf.pages[0].extract_table()
        
    if primeira_pagina:
        st.subheader("⚙️ Configuração de Colunas")
        colunas_exemplo = primeira_pagina[0] # Pega o cabeçalho detectado
        
        c1, c2, c3 = st.columns(3)
        with c1: idx_data = st.selectbox("Coluna da DATA", range(len(colunas_exemplo)), format_func=lambda x: f"Coluna {x}: {colunas_exemplo[x]}")
        with c2: idx_hist = st.selectbox("Coluna do HISTÓRICO", range(len(colunas_exemplo)), format_func=lambda x: f"Coluna {x}: {colunas_exemplo[x]}", index=1)
        with c3: idx_valor = st.selectbox("Coluna do VALOR", range(len(colunas_exemplo)), format_func=lambda x: f"Coluna {x}: {colunas_exemplo[x]}", index=2)

        if st.button("🚀 Processar Extrato"):
            dados_finais = []
            
            with pdfplumber.open(arquivo_pdf) as pdf:
                for pagina in pdf.pages:
                    tabela = pagina.extract_table()
                    if tabela:
                        for linha in tabela:
                            try:
                                # Pular linhas que não têm data válida (ajuste conforme o banco)
                                if not linha[idx_data] or len(str(linha[idx_data])) < 5: continue
                                
                                valor_num, tipo = extrair_valor(linha[idx_valor])
                                
                                dados_finais.append({
                                    'Data': pd.to_datetime(linha[idx_data], dayfirst=True, errors='coerce'),
                                    'Histórico': linha[idx_hist],
                                    'Débito': valor_num if tipo == "D" else None,
                                    'Crédito': valor_num if tipo == "C" else None
                                })
                            except: continue

            # Criar DataFrame e Ordenar por Data
            df = pd.DataFrame(dados_finais)
            df = df.dropna(subset=['Data']).sort_values(by='Data')
            df['Data'] = df['Data'].dt.strftime('%d/%m/%Y') # Formata para o Excel

            # 2. Exibição e Download
            st.divider()
            st.subheader(f"📊 Resultado: {nome_empresa} - {nome_banco}")
            st.dataframe(df, use_container_width=True)

            # Gerar Excel com Título
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Criar cabeçalho customizado
                df_titulo = pd.DataFrame([[f"EMPRESA: {nome_empresa}"], [f"BANCO: {nome_banco}"], [""]])
                df_titulo.to_excel(writer, index=False, header=False, startrow=0)
                
                # Dados começam na linha 4
                df.to_excel(writer, index=False, startrow=4, sheet_name='Extrato')
                
                # Ajuste de largura das colunas
                worksheet = writer.sheets['Extrato']
                for i, col in enumerate(df.columns):
                    worksheet.set_column(i, i, 20)

            st.download_button(
                label="📥 Baixar Planilha Excel Ordenada",
                data=output.getvalue(),
                file_name=f"Extrato_{nome_empresa}_{nome_banco}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
