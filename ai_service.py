import os
from google import genai
from dotenv import load_dotenv

# Carrega a API Key do arquivo .env
load_dotenv()

# Inicializa o cliente moderno da Google (ele busca automaticamente a GEMINI_API_KEY no .env)
client = genai.Client()

def gerar_conteudo_educacional(prompt_professor):
    """
    Envia o pedido do professor para o Gemini e retorna o plano de aula gerado.
    """
    try:
        # Usando o modelo padrão recomendado atualizado
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_professor,
        )
        return response.text
    except Exception as e:
        raise Exception(f"Erro na comunicação com o Gemini: {str(e)}")