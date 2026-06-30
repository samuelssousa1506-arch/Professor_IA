import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def gerar_conteudo_educacional(tipo_modulo, disciplina, ano, tema, bncc):
    """
    Comunica com o Gemini-2.5-Flash utilizando o SDK moderno do Google (google-genai)
    e molda o comportamento da IA com base no módulo ativo no painel.
    """
    client = genai.Client()
    
    prompt = f"""
    Atue como um Consultor Pedagógico Sênior e Especialista em Alinhamento Curricular da BNCC.
    Sua tarefa é redigir um documento técnico de alto nível pedagógico do tipo: {tipo_modulo}.
    
    Metadados de Contexto:
    - Componente Curricular: {disciplina}
    - Segmento de Ensino: {ano}
    - Objeto de Estudo / Tema Central: {tema}
    - Códigos e Habilidades de Referência BNCC: {bncc}
    
    Instruções específicas de Escrita para o módulo {tipo_modulo}:
    - Se for 'Plano de Aula': Forneça objetivos conceituais/procedimentais, metodologia detalhada dividida em momentos (introdução, desenvolvimento, fechamento), recursos didáticos e estratégias de avaliação.
    - Se for 'Planejamento Bimestral': Estruture a distribuição do tema ao longo de 8 semanas, definindo cronogramas de conteúdos, competências específicas trabalhadas no período e metodologias de verificação continuada.
    - Se for 'Banco de Atividades': Crie uma lista com exercícios diversificados (questões contextualizadas de múltipla escolha e questões discursivas) acompanhadas de seus respectivos gabaritos justificados.
    - Se for 'Gerador de Provas': Desenvolva uma avaliação formal e estruturada contendo cabeçalho institucional, instruções de aplicação, critérios de pontuação e questões categorizadas por níveis de complexidade taxonômica (fácil, média, difícil).
    - Se for 'Relatórios Pedagógicos': Monte um modelo detalhado de parecer descritivo de desempenho escolar, mapeando evolução cognitiva, pontos de atenção e intervenções necessárias baseadas no aprendizado desse tema.
    - Se for 'Plano de Inclusão / AEE': Desenvolva adaptações curriculares precisas para alunos com necessidades específicas (PCD/Altas Habilidades), propondo flexibilização de tempo, recursos assistivos e metodologias ativas direcionadas.
    - Se for 'Projetos Interdisciplinares': Idealize um escopo de projeto integrando este tema a outras duas áreas do conhecimento, definindo a problemática motivadora, produto final esperado e rubricas de avaliação coletiva.

    Diretrizes de Formatação Estritas do Layout (Cruciais para renderização HTML):
    1. Para qualquer título de seção principal, inicie a linha exatamente com o prefixo: SECAO: Nome do Título
    2. Para qualquer subtítulo ou subseção, inicie a linha exatamente com o prefixo: SUBSECAO: Nome do Subtítulo
    3. Utilize '---' isolado em uma linha para demarcar separações visuais de blocos ou quebras de páginas pedagógicas.
    4. ATENÇÃO: Nunca envie formatações brutas de Markdown como hashtags (#) ou asteriscos (*) para aplicar negritos. Retorne o texto limpo, pois o JavaScript cuidará da estilização.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Falha crítica na API do Gemini: {str(e)}"