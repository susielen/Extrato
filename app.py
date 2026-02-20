import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def formatar_valor_final(texto):
    if not texto: return None
    t = str(texto).upper().replace('"', '').replace(' ', '').strip()
    # Regra: para o fornecedor credito (+) e debito (-)
    e_saida = 'D' in t or '-' in t
    # Pega só números e separadores
    num = re.sub(r'[^\d,.]', '', t)
    try:
        if ',' in num and '.' in num: num = num.replace('.', '').replace(',', '.')
        elif ',' in num: num = num.replace(',', '.')
        res = float(num)
        return -res if e_saida else res
    except:
        return None

# --- ESTILO ---
st.set_page_config(page_title="Robô de Extratos Multi-Banco", layout="centered")
st.markdown("<style>.stApp {background-color: #E3F2FD;}</style>", unsafe_allow_html=True)

st.title("🤖 Super Robô de Extratos v13")
st.write("Configurado para ler todas as linhas da Caixa e Santander.")

arquivo_pdf = st.file_uploader("Selecione o PDF", type=["pdf"])

if arquivo_pdf:
    dados_lista = []
    # Expressão que "caça" a linha completa: Data até o Valor (C ou D)
    # Explicação: Procura data, ignora o que tiver no meio, e para quando acha um valor com C ou D
    padrao_caixa = re.compile(r'(\d{2}/\d{2}/\d{4}).*?([\d.,]+\s*[CD])')

    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            # Extrai o texto e remove as quebras de linha para o texto ficar "corrido"
            texto_puro = pagina.extract_text()
            if not texto_puro: continue
            
            # Limpeza radical: transforma a página num único texto sem aspas e sem quebras de linha
            texto_limpo = texto_puro.replace('"', '').replace('\n', ' ').replace('\r', ' ')
            
            # Procura todas as ocorrências na página
            encontrados = padrao_caixa.findall(texto_limpo)
            
            for item in encontrados:
                data_f = item[0]
                valor_bruto = item[1]
                
                # Para achar o histórico, pegamos o que está entre a data e o valor no texto limpo
                # Usamos um truque simples de recorte de texto
                pos_data = texto_limpo.find(data_f)
                pos_valor = texto_limpo.find(valor_bruto, pos_data)
                historico = texto_limpo[pos_data + len(data_f):pos_valor].strip()
                
                # Limpezas finais no histórico
                historico = re.sub(r'\d{2}:\d{2}:\d{2}', '', historico) # Tira a hora
                historico = historico.replace(',', ' ').strip().upper()
                
                v_final = formatar_valor_final(valor_bruto)
                
                # Só adiciona se o valor não for zero e não for o título "SALDO"
                if v_final is not None and v_final != 0 and "SALDO" not in historico:
                    dados_lista.append({
                        'Data': data_f,
                        'Histórico': historico,
                        'Valor': v_final
                    })
                    # Removemos o trecho já processado para não repetir
                    texto_limpo = texto_limpo[pos_valor + len(valor_bruto):]

    if dados_lista:
        df = pd.DataFrame(dados_lista)
        st.success(f"Sucesso! Conseguimos extrair {len(df)} lançamentos.")
        st.dataframe(df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, startrow=3, startcol=1,
