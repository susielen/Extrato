import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def processar_valor_com_sinal(texto_valor):
    """
    Analisa se o valor é negativo (-) ou positivo/crédito (C ou sem sinal)
    e retorna o valor limpo e a coluna correta.
    """
    if not texto_valor: return None, None
    
    # Limpeza inicial: remove R$, espaços e pontos de milhar
    t = str(texto_valor).upper().replace("R$", "").replace(" ", "")
    
    # IDENTIFICAÇÃO DO SINAL/TIPO
    # É débito se: tiver o sinal '-' OU tiver a letra 'D'
    e_debito = '-' in t or 'D' in t
    
    # Limpa o texto para deixar apenas o número e a vírgula decimal
    apenas_numeros = re.sub(r'[^\d,]', '', t)
    
    try:
        # Converte para float (ex: "1.250,50" -> 1250.50)
        valor_float = float(apenas_numeros.replace(',', '.'))
        
        if e_debito:
            return valor_float, "DEBITO"
        else:
            return valor_float, "CREDITO"
    except:
        return None, None

# --- Interface Streamlit ---
st.set_page_config(page_title="Robô de Extratos Pro", layout="wide")
st.title("🤖 Robô de Extratos Bancários")

st.sidebar.header("📋 Dados do Relatório")
nome_empresa = st.sidebar.text_input("Nome da Empresa", "Minha Empresa")
nome_banco = st.sidebar.text_input("Nome do Banco", "Meu Banco")

arquivo_pdf = st.file_uploader("Carregue o PDF do Extrato", type=["pdf"])

if arquivo_pdf:
    dados_extraidos = []
    
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto_completo = pagina.extract_text()
            if not texto_completo: continue
            
            linhas = texto_completo.split('\n')
            for linha in linhas:
                # Procura o padrão de data (DD/MM ou DD/MM/AAAA) no início da linha
                match_data = re.search(r'^(\d{2}/\d{2}(?:/\d{4})?)', linha.strip())
                
                if match_data:
                    data_str = match_data.group(1)
                    
                    # Remove a data da linha para isolar histórico e valor
                    resto_da_linha = linha.replace(data_str, "").strip()
                    
                    # Divide a linha em palavras para pegar o valor no final
                    partes = resto_da_linha.split()
                    
                    if len(partes) >= 2:
                        valor_bruto = partes[-1]  # O valor com sinal está no fim
                        historico = " ".join(partes[:-1]) # O meio é o histórico
                        
                        valor_final, tipo = processar_valor_com_sinal(valor_bruto)
                        
                        if valor_final is not None:
                            dados_extraidos.append({
                                'Data_Obj': pd.to_datetime(data_str, dayfirst=True, errors='coerce'),
                                'Data': data_str,
                                'Histórico': historico,
                                'Débito': valor_final if tipo == "DEBITO" else None,
                                'Crédito': valor_final if tipo == "CREDITO" else None
                            })

    if dados_extraidos:
        df = pd.DataFrame(dados_extraidos)
        # Ordena por data (mais antigo para o mais novo)
        df = df.sort_values('Data_Obj').drop(columns=['Data_Obj'])
        
        st.write(f"### ✅ Visualização: {nome_empresa} - {nome_banco}")
        st.dataframe(df, use_container_width=True)

        # Geração do Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Título e Empresa no topo
            pd.DataFrame([[f"EMPRESA: {nome_empresa}"], [f"BANCO: {nome_banco}"], [""]]).to_excel(writer, index=False, header=False, startrow=0)
            
            # Dados a partir da linha 4
            df.to_excel(writer, index=False, startrow=3, sheet_name='Extrato')
            
            # Formatação de Dinheiro
            workbook = writer.book
            worksheet = writer.sheets['Extrato']
            format_dinheiro = workbook.add_format({'num_format': '#,##0.00'})
            worksheet.set_column('C:D', 18, format_dinheiro)
            worksheet.set_column('B:B', 40) # Coluna de Histórico mais larga

        st.download_button(
            label="📥 Baixar Planilha Excel",
            data=output.getvalue(),
            file_name=f"Extrato_{nome_empresa}_{nome_banco}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("Não foram encontrados dados. Verifique se o PDF contém texto e se o valor está no fim da linha.")
