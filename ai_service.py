import os

try:
    from google import genai
    USE_NEW_SDK = True
except ImportError:
    import google.generativeai as genai
    USE_NEW_SDK = False

def gerar_conteudo_educacional(tipo_modulo, disciplina, ano, tema, bncc, tipo_prova=None, qtd_questoes=None, nivel=None):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        return """
        <div class="alert alert-warning mt-3">
            <i class="fa-solid fa-triangle-exclamation me-2"></i>
            <strong>Chave API Não Configurada:</strong> Adicione a variável <code>GEMINI_API_KEY</code> no painel de ambiente.
        </div>
        """
    
    # PROMPT: PLANEJAMENTO BIMESTRAL
    if tipo_modulo == "Planejamento Bimestral":
        prompt = f"""
        Você é um consultor pedagógico sênior especialista na estrutura curricular da SEMED e na BNCC.
        O professor forneceu as seguintes Unidades Temáticas de partida: "{tema}"
        Componente Curricular: {disciplina} | Ano/Segmento: {ano} | Diretrizes: {bncc}
        
        Gere completamente o Plano Bimestral oficial estruturado exclusivamente em tags HTML limpas (sem markdown ```html):
        1. COMPETÊNCIAS GERAIS DA EDUCAÇÃO BÁSICA (3 a 5 numeradas)
        2. COMPETÊNCIAS ESPECÍFICAS DE {disciplina.upper()}
        3. OBJETOS DE CONHECIMENTO
        4. HABILIDADES (BNCC com códigos e descrições completas)
        5. SUGESTÕES METODOLÓGICAS (Ações práticas detalhadas)
        6. AVALIAÇÃO | 7. RECURSOS | 8. REFERÊNCIAS | 9. OBSERVAÇÕES.
        """
        
    # PROMPT: GERADOR DE PROVAS
    elif tipo_modulo == "Gerador de Provas":
        prompt = f"""
        Você é um especialista em avaliações escolares e elaboração de itens de testes educacionais alinhados à BNCC.
        
        Crie uma avaliação escolar completa em formato HTML limpo (sem blocos ```html) com as seguintes especificações:
        - Disciplina/Componente: {disciplina}
        - Ano/Turma: {ano}
        - Objeto de Estudo / Conteúdo da Prova: {tema}
        - Alinhamento de Diretrizes BNCC: {bncc}
        - Tipo de Questões: {tipo_prova if tipo_prova else 'Mista'}
        - Quantidade total de itens: {qtd_questoes if qtd_questoes else '10'} questões
        - Nível de Rigor Cognitivo: {nivel if nivel else 'Médio'}
        
        Regras de Formatação Obrigatórias do Documento:
        1. ATENÇÃO MÁXIMA: NÃO construa nenhum tipo de cabeçalho escolar ou campo para nome de aluno no topo da sua resposta, pois a nossa plataforma já renderiza um cabeçalho oficial fixo em HTML estruturado. Comece a sua resposta diretamente a partir do bloco de "INSTRUÇÕES DA PROVA".
        2. INSTRUÇÕES: Adicione de 3 a 4 regras curtas e diretas para orientar a realização da prova.
        3. ITENS DE AVALIAÇÃO: Elabore as {qtd_questoes} questões mantendo rigorosamente o nível {nivel}. 
           - Se 'Objetiva' ou 'Mista': Use alternativas de (A) a (E) bem elaboradas e claras.
           - Se 'Subjetiva' ou 'Mista': Deixe de 3 a 4 linhas pontilhadas (<p>....................................................................</p>) para resposta escrita do aluno.
        4. GABARITO AUTOMÁTICO: No final absoluto do texto, gere o Gabarito Resolvido inserido em uma div com a classe CSS 'no-print' (<div class="no-print mt-5 border-top pt-3">) para que o professor o consulte na tela, mas ele não apareça no papel impresso.
        """
        
    # PROMPT PADRÃO / OUTROS MÓDULOS
    else:
        prompt = f"""
        Você é um especialista em educação de alto nível.
        Gere um conteúdo de excelência para o módulo '{tipo_modulo}', focado na disciplina de '{disciplina}' para o '{ano}'.
        Tema Principal: {tema} | Alinhamento: {bncc}
        Responda estruturando o texto APENAS em HTML elegante. Não inclua blocos markdown ```html.
        """
    
    try:
        if USE_NEW_SDK:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            return response.text if response.text else "O modelo retornou uma resposta vazia."
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text if response.text else "O modelo retornou uma resposta vazia."
    except Exception as e:
        return f"<div class='alert alert-danger mt-3'><strong>Erro na comunicação:</strong> {str(e)}</div>"