import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

def formatar_valor_universal(texto):
    """Limpa o texto e identifica se é débito pelo sinal ou pela letra D."""
    if not texto: return 0.0, "C"
    # Remove espaços e converte para maiúsculas
    t = str(texto).upper().replace(" ", "")
    
    # Identifica se é saída (presença de '-' ou 'D')
    tipo = "D" if ("-" in t or "D" in t) else "C"
    
    # Pega apenas os números, pontos e vírgulas
    numeros = re.sub(r'[^\d,.-]', '', t)
    
    try:
        # Se o banco usa ponto para milhar (1.000,00), removemos o ponto e trocamos a vírgula
        if "," in numeros:
            valor = float(numeros.replace(".", "").replace(",", "."))
        else:
            valor = float(numeros)
        return abs(valor), tipo
    except:
        return 0.0, "C"

st.title("🤖 Robô de Extratos (Versão Texto)")

empresa = st.sidebar.text_input("Empresa", "Minha Empresa")
banco = st.sidebar.text_input("Banco", "Meu Banco")

arquivo = st.file_uploader("Suba o PDF aqui", type="pdf")

if arquivo:
    dados_brutos = []
    
    with pdfplumber.open(arquivo) as pdf:
        for pagina in pdf.pages:
            # EXTRAÇÃO POR TEXTO (mais garantido que tabela)
            texto_pag = pagina.extract_text()
            if not texto_pag: continue
            
            linhas = texto_pag.split('\n')
            for linha in linhas:
                # Procura por um padrão de data (ex: 01/01/2026 ou 01/01)
                match_data = re.search(r'(\d{2}/\d{2}/\d{4}|\d{2}/\d{2})', linha)
                
                if match_data:
                    data = match_data.group(1)
                    # O resto da linha vira o histórico e valor
                    resto = linha.replace(data, "").strip()
                    
                    # Tenta pegar o último "bloco" da linha como sendo o valor
                    partes = resto.split()
                    if len(partes) >= 2:
                        valor_texto = partes[-1] # Geralmente o valor está no fim
                        historico = " ".join(partes[:-1])
                        
                        v_num, v_tipo = formatar_valor_universal(valor_texto)
                        
                        if v_num > 0: # Só adiciona se houver valor
                            dados_brutos.append({
                                'Data_Sort': pd.to_datetime(data, dayfirst=True, errors='coerce'),
                                'Data': data,
                                'Histórico': historico,
                                'Débito': v_num if v_tipo == "D" else None,
                                'Crédito': v_num if v_tipo == "C" else None
                            })

    if dados_brutos:
        df = pd.DataFrame(dados_brutos)
        # Ordenar e Limpar
        df = df.sort_values('Data_Sort').drop(columns=['Data_Sort'])
        
        st.write("### ✅ Extrato Processado")
        st.dataframe(df, use_container_width=True)

        # Gerar Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Cabeçalho
            pd.DataFrame([[f"EMPRESA: {empresa}"], [f"BANCO: {banco}"]]).to_excel(writer, index=False, header=False)
            # Dados (começando na linha 3)
            df.to_excel(writer, index=False, startrow=3, sheet_name='Extrato')
            
        st.download_button("📥 Baixar Excel", output.getvalue(), f"Extrato_{banco}.xlsx")
    else:
        st.error("❌ Não encontrei dados no formato esperado. O PDF pode ser uma imagem (digitalizado).")
