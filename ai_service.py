import os
import google.generativeai as genai
from google.api_core import errors

# Configuração da API Key obtida das variáveis de ambiente (Local ou Render)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def gerar_conteudo_educacional(**kwargs):
    """
    Gera conteúdo educacional utilizando a API do Gemini.
    Possui tratamento contra o erro 429 (Resource Exhausted) para evitar que o app trave.
    """
    tipo_modulo = kwargs.get('tipo_modulo', 'Banco de Atividades')
    tema = kwargs.get('tema', '')
    disciplina = kwargs.get('disciplina', 'Geral')
    ano = kwargs.get('ano', 'Geral')
    bncc = kwargs.get('bncc', '')
    tipo_prova = kwargs.get('tipo_prova', 'Mista')
    qtd_questoes = kwargs.get('qtd_questoes', '10')
    nivel = kwargs.get('nivel', 'Médio')

    # Se a API Key não estiver configurada, aciona o fallback imediatamente
    if not GEMINI_API_KEY:
        return obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano)

    try:
        # Inicializa o modelo otimizado e rápido
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Engenharia de Prompt rigorosa para manter o padrão identitário do teu PDF
        prompt = f"""
        Atue como um Especialista em Design Pedagógico e Elaboração de Avaliações Escolares Oficiais.
        Sua tarefa é gerar o conteúdo para o módulo '{tipo_modulo}'.
        
        DADOS DO ESCOPO DO DOCUMENTO:
        - Componente Curricular / Disciplina: {disciplina}
        - Ano Escolar / Série: {ano}
        - Objeto de Estudo / Tema central: {tema}
        - Código de Diretriz BNCC base: {bncc}
        - Nível de Rigor Cognitivo: {nivel}
        """

        if tipo_modulo == 'Gerador de Provas':
            prompt += f"""
            - Quantidade de Questões solicitadas: {qtd_questoes}
            - Formato das Questões: {tipo_prova} (Opções: Mista, Objetiva ou Subjetiva)

            DIRETRIZES OBRIGATÓRIAS DE FORMATAÇÃO (ESTRUTURA IDENTITÁRIA DO MODELO REAL):
            1. Use numeração sequencial com dois dígitos seguidos de ponto para cada questão (Exemplo: 01., 02., 03., etc).
            2. Imediatamente após a numeração, inclua a diretriz BNCC entre parênteses. Use o código fornecido ({bncc}) ou deduza um código real e correto da BNCC caso o campo esteja vazio. Exemplo: '01. (EF09MA02) '.
            3. Todo o texto do enunciado da questão DEVE estar estritamente dentro da tag HTML <strong>...</strong> (Negrito).
            4. Para questões Objetivas ou Mistas, posicione as alternativas de 'a)' até 'd)' alinhadas verticalmente logo abaixo do enunciado, separadas por quebras de linha (<br>).
            5. Para questões Subjetivas/Discursivas, adicione exatamente de 3 a 4 linhas de resposta utilizando a estrutura HTML de classe do sistema: <div class="linha-resposta"></div>.
            6. IMPORTANTE: Não adicione cabeçalhos textuais duplicados, títulos extras ou decorações de markdown (como asteriscos de negrito do próprio markdown). Retorne diretamente o código HTML limpo das questões.

            EXEMPLO DE FORMATO ESPERADO:
            <p><strong>01. ({bncc if bncc else "EF09MA02"}) Escreva o enunciado da questão aqui em formato de texto contínuo e bem elaborado...</strong></p>
            <p>a) Primeira alternativa.<br>b) Segunda alternativa.<br>c) Terceira alternativa.<br>d) Quarta alternativa.</p>
            <br>
            """
        else:
            prompt += """
            Gere uma estrutura pedagógica profissional formatada em HTML limpo. Use títulos H4 estruturados, 
            listas organizadas e parágrafos bem definidos que se adequem perfeitamente a uma folha de papel impressa.
            """

        # Envia a requisição para a API do Gemini
        response = model.generate_content(prompt)
        return response.text

    except errors.ResourceExhausted:
        # TRATAMENTO DO ERRO 429: Se estourar a quota, renderiza um aviso amigável sem quebrar o servidor
        return f"""
        <div class="alert alert-warning no-print my-3 py-3 border-start border-warning border-3 rounded-3" style="background-color: #fffbeb;">
            <h5 class="fw-bold text-warning-dark mb-1"><i class="fa-solid fa-triangle-exclamation me-2"></i> Limite Diário Excedido (Quota da API)</h5>
            <p class="small text-muted mb-0">
                O limite diário de requisições da camada gratuita da API do Gemini foi atingido para este projeto (Erro 429 RESOURCE_EXHAUSTED). 
                Para continuar gerando novos conteúdos sob demanda, você pode migrar para o plano <em>Pay-As-You-Go</em> no Google AI Studio. 
                <strong>O sistema ativou o Modo de Segurança com uma demonstração estruturada abaixo.</strong>
            </p>
        </div>
        {obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano)}
        """
        
    except Exception as e:
        # Captura de qualquer outro erro técnico inesperado
        return f"""
        <div class="alert alert-danger no-print my-3">
            <h6><i class="fa-solid fa-circle-xmark me-2"></i> Erro ao processar requisição com a IA</h6>
            <p class="small mb-0">Detalhes técnicos do erro: {str(e)}</p>
        </div>
        """

def obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano):
    """
    Função de contingência para fornecer um layout de exemplo idêntico 
    ao padrão exigido quando a API não puder responder.
    """
    if tipo_modulo == 'Gerador de Provas':
        return f"""
        <p><strong>01. (EF09MA02) O número &pi; (Pi) é o nome dado ao quociente entre as medidas da circunferência e do diâmetro de um mesmo círculo. Este número possui infinitas casas decimais e não possui um período que se repita. Portanto, podemos afirmar corretamente que o número &pi; pertence ao conjunto dos números:</strong></p>
        <p>a) naturais.<br>b) inteiros.<br>c) racionais.<br>d) irracionais.</p>
        <br>
        <p><strong>02. (EF09MA04) O Brasil possui uma população estimada de aproximadamente 203 milhões de habitantes, de acordo com o último censo demográfico oficial do IBGE. Assinale a alternativa que apresenta a escrita correta desse número habitacional em Notação Científica:</strong></p>
        <p>a) 203 x 10<sup>7</sup><br>b) 2,03 x 10<sup>7</sup><br>c) 2,03 x 10<sup>-8</sup><br>d) 2,03 x 10<sup>8</sup></p>
        <br>
        <p><strong>03. (EF09MA03) Um determinado conjunto habitacional planejado é composto por exatamente 6 prédios residenciais. Sabendo que cada prédio tem 6 andares, e cada andar possui 6 apartamentos mapeados, indique a potência que representa o número total de apartamentos:</strong></p>
        <p>a) 6<sup>3</sup><br>b) 6<sup>4</sup><br>c) 6<sup>5</sup><br>d) 6<sup>6</sup></p>
        <br>
        <p><strong>04. (EF09MA02) Analise as propriedades matemáticas das raízes quadradas listadas abaixo e marque a opção que representa necessariamente a raiz cujo resultado final é classificado como um Número Irracional:</strong></p>
        <p>a) &radic;400<br>b) &radic;144<br>c) &radic;196<br>d) &radic;250</p>
        <br>
        <p><strong>05. (EF09MA01) Escreva com suas palavras qual a diferença prática entre o comportamento de um número racional (como uma dízima periódica) e um número irracional na reta numérica real:</strong></p>
        <div class="linha-resposta"></div>
        <div class="linha-resposta"></div>
        <div class="linha-resposta"></div>
        <div class="linha-resposta"></div>
        """
    else:
        return f"""
        <h4><i class="fa-solid fa-file-invoice text-primary me-2"></i> Estrutura de Documentação Pedagógica</h4>
        <p><strong>Módulo operacional ativo:</strong> {tipo_modulo}</p>
        <p><strong>Escopo Temático:</strong> {tema if tema else 'Objeto de Conhecimento Geral'} associado à disciplina de {disciplina}.</p>
        <hr>
        <h5>Diretrizes e Objetivos de Aprendizagem Base:</h5>
        <ul>
            <li>Desenvolver as competências cognitivas previstas para o {ano}.</li>
            <li>Estimular o raciocínio lógico-matemático e a interpretação textual dos enunciados propostos.</li>
            <li>Garantir o alinhamento pedagógico de acordo com os descritores de habilidades da BNCC.</li>
        </ul>
        """