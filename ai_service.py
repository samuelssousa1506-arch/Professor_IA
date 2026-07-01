import os

# Tenta importar a biblioteca nova ou a antiga do Google de forma segura
try:
    from google import genai
    USE_NEW_SDK = True
except ImportError:
    import google.generativeai as genai
    USE_NEW_SDK = False

def gerar_conteudo_educacional(tipo_modulo, disciplina, ano, tema, bncc):
    # Procura a chave nas variáveis de ambiente do servidor
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    # Se não encontrar a chave, avisa diretamente na tela em vez de quebrar
    if not api_key:
        return """
        <div class="alert alert-warning mt-3">
            <i class="fa-solid fa-triangle-exclamation me-2"></i>
            <strong>Chave API Não Configurada:</strong> A variável <code>GEMINI_API_KEY</code> não foi encontrada no Render. 
            Por favor, adicione-a no menu 'Environment' do seu painel do Render.
        </div>
        """
    
    try:
        # Monta um prompt detalhado e estruturado para o Gemini
        prompt = f"""
        Você é um especialista em educação de alto nível.
        Gere um conteúdo de excelência para o módulo '{tipo_modulo}', focado na disciplina de '{disciplina}' para o '{ano}'.
        Tema Principal / Objeto de Estudo: {tema}
        Diretrizes e Alinhamento com a BNCC: {bncc}
        
        Regras de Formatação Obrigatórias:
        1. Responda estruturando o texto APENAS em HTML elegante (use <p>, <ul>, <li>, <strong>, <h5>, e tabelas <table> se necessário).
        2. NÃO inclua as marcações de bloco de código como ```html no início ou ``` no final. Retorne o HTML limpo.
        3. Seja extremamente detalhado, profundo e prático para o uso do professor em sala de aula.
        """
        
        if USE_NEW_SDK:
            # Executa usando a nova biblioteca do Google
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text if response.text else "O modelo retornou uma resposta vazia."
        else:
            # Executa usando a biblioteca clássica (fallback)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text if response.text else "O modelo retornou uma resposta vazia."
            
    except Exception as e:
        # Se der qualquer erro na API, exibe a mensagem detalhada na tela para diagnóstico
        return f"""
        <div class="alert alert-danger mt-3">
            <i class="fa-solid fa-circle-exclamation me-2"></i>
            <strong>Erro na comunicação com o Gemini AI:</strong> {str(e)}
        </div>
        """