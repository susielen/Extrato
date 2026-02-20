import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def processar_valor_unico(texto_valor):
    """Identifica se é débito ou crédito e retorna o valor com o sinal correto."""
    if not texto_valor: return None
    t = str(texto_valor).upper().replace(" ", "").replace("R$", "")
    
    # Identifica se é saída (presença de '-' ou 'D')
    e_saida = '-' in t or 'D' in t
    
    # Limpa apenas para números e vírgula
    apenas_numeros = re.sub(r'[^\d,]', '', t)
    
    try:
        valor_float = float(apenas_numeros.replace(',', '.'))
        return -valor_float if e_saida else valor_float
    except:
        return None

# --- Interface Streamlit ---
st.set_page_config(page_title="Robô de Extratos", layout="centered")
st.title("🤖 Conversor de Extrato Bancário")

col_emp, col_ban = st.columns(2)
nome_empresa = col_emp.text_input("Empresa", "Minha Empresa")
nome_banco = col_ban.text_input("Banco", "Banco")

arquivo_pdf = st.file_uploader("Selecione o arquivo PDF", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if not texto: continue
            for linha in texto.split('\n'):
                # Busca data no início da linha
                match_data = re.search(r'^(\d{2}/\d{2}(?:/\d{4})?)', linha.strip())
                if match_data:
                    data_str = match_data.group(1)
                    resto = linha.replace(data_str, "").strip()
                    partes = resto.split()
                    if len(partes) >= 2:
                        valor_bruto = partes[-1]
                        historico = " ".join(partes[:-1])
                        valor_final = processar_valor_unico(valor_bruto)
                        
                        if valor_final is not None:
                            dados_lista.append({
                                'Data_Obj': pd.to_datetime(data_str, dayfirst=True, errors='coerce'),
                                'Data': data_str,
                                'Histórico': historico,
                                'Valor': valor_final
                            })

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        df = df.sort_values('Data_Obj').drop(columns=['Data_Obj'])
        
        # Colunas extras
        df['Débito'] = ""
        df['Crédito'] = ""
        df['Descrição'] = ""

        st.divider()
        st.write("### Prévia do Extrato")
        st.dataframe(df.style.format({'Valor': "{:.2f}"}), use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Cabeçalho
            pd.DataFrame([[f"EMPRESA: {nome_empresa}"], [f"BANCO: {nome_banco}"]]).to_excel(writer, index=False, header=False, startrow=0)
            
            # Escreve os dados. A partir daqui, as colunas são:
            # A=Data, B=Histórico, C=Valor, D=Débito, E=Crédito, F=Descrição
            df.to_excel(writer, index=False, startrow=3, sheet_name='Extrato')
            
            workbook = writer.book
            worksheet = writer.sheets['Extrato']
            
            # Formatos
            fmt_moeda = workbook.add_format({'num_format': '#,##0.00'})
            
            # Ajuste de Colunas
            worksheet.set_column('C:C', 15, fmt_moeda)
            worksheet.set_column('B:B', 40)
            worksheet.set_column('D:F', 15)

            # Formatação Condicional (Cores Verde e Vermelho)
            ultima_linha = len(df) + 4
            worksheet.conditional_format(f'C5:C{ultima_linha}', {
                'type':     'cell',
                'criteria': '>',
                'value':    0,
                'format':   workbook.add_format({'font_color': '#006100', 'bg_color': '#C6EFCE'})
            })
            worksheet.conditional_format(f'C5:C{ultima_linha}', {
                'type':     'cell',
                'criteria': '<',
                'value':    0,
                'format':   workbook.add_format({'font_color': '#9C0006', 'bg_color': '#FFC7CE'})
            })

            # Inserindo a fórmula CONCAT apenas na coluna Histórico (B)
            # Usando write_formula para garantir que não insira @
            for i in range(len(df)):
                row_num = i + 5
                # Fórmula lendo apenas a coluna B (Histórico)
                formula = f'=CONCAT(B{row_num})'
                worksheet.write_formula(f'F{row_num}', formula)

        st.download_button(
            label="📥 Baixar Planilha Final",
            data=output.getvalue(),
            file_name=f"Extrato_{nome_empresa}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
