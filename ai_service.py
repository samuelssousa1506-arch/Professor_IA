import os
import google.generativeai as genai
from google.api_core import errors

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def gerar_conteudo_educacional(**kwargs):
    tipo_modulo = kwargs.get('tipo_modulo', 'Banco de Atividades')
    tema = kwargs.get('tema', '')
    disciplina = kwargs.get('disciplina', 'Geral')
    ano = kwargs.get('ano', 'Geral')
    bncc = kwargs.get('bncc', '')
    tipo_prova = kwargs.get('tipo_prova', 'Mista')
    qtd_questoes = kwargs.get('qtd_questoes', '10')
    nivel = kwargs.get('nivel', 'Médio')

    if not GEMINI_API_KEY:
        return obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano)

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
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
            - Formato das Questões: {tipo_prova}

            DIRETRIZES OBRIGATÓRIAS DE FORMATAÇÃO (ESTRUTURA IDENTITÁRIA DO MODELO REAL):
            1. Use numeração sequencial com dois dígitos seguidos de ponto para cada questão (Exemplo: 01., 02., etc).
            2. Imediatamente após a numeração, inclua a diretriz BNCC entre parênteses. Use o código fornecido ({bncc}) ou deduza um correto caso vazio. Exemplo: '01. (EF09MA02) '.
            3. Todo o texto do enunciado da questão DEVE estar estritamente dentro da tag HTML <strong>...</strong>.
            4. Para questões Objetivas ou Mistas, posicione as alternativas de 'a)' até 'd)' alinhadas verticalmente logo abaixo do enunciado, separadas por quebras de linha (<br>).
            5. Para questões Subjetivas, adicione de 3 a 4 linhas de resposta utilizando: <div class="linha-resposta"></div>.
            6. IMPORTANTE: Retorne diretamente o código HTML limpo das questões, sem markdown.
            """
        else:
            prompt += """
            Gere uma estrutura pedagógica profissional formatada em HTML limpo. Use títulos H4 estruturados, 
            listas organizadas e parágrafos bem definidos.
            """

        response = model.generate_content(prompt)
        return response.text

    except errors.ResourceExhausted:
        return f"""
        <div class="alert alert-warning no-print my-3 py-3 border-start border-warning border-3 rounded-3" style="background-color: #fffbeb;">
            <h5 class="fw-bold text-warning-dark mb-1"><i class="fa-solid fa-triangle-exclamation me-2"></i> Limite Diário Excedido (Quota da API)</h5>
            <p class="small text-muted mb-0">
                O limite diário de requisições da camada gratuita da API do Gemini foi atingido para este projeto. O sistema ativou o Modo de Segurança com uma demonstração estruturada abaixo.
            </p>
        </div>
        {obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano)}
        """
    except Exception as e:
        return f"<div class='alert alert-danger'>Erro ao processar com a IA: {str(e)}</div>"

def obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano):
    if tipo_modulo == 'Gerador de Provas':
        return f"""
        <p><strong>01. (EF09MA02) O número &pi; (Pi) é o nome dado ao quociente entre as medidas da circunferência e do diâmetro de um mesmo círculo. Este número possui infinitas casas decimais e não possui um período que se repita. Portanto, podemos afirmar corretamente que o número &pi; pertence ao conjunto dos números:</strong></p>
        <p>a) naturais.<br>b) inteiros.<br>c) racionais.<br>d) irracionais.</p>
        <br>
        <p><strong>02. (EF09MA04) O Brasil possui uma população estimada de aproximadamente 203 milhões de habitantes, de acordo com o último censo demográfico oficial do IBGE. Assinale a alternativa que apresenta a escrita correta desse número habitacional em Notação Científica:</strong></p>
        <p>a) 203 x 10<sup>7</sup><br>b) 2,03 x 10<sup>7</sup><br>c) 2,03 x 10<sup>-8</sup><br>d) 2,03 x 10<sup>8</sup></p>
        """
    else:
        return f"""
        <h4><i class="fa-solid fa-file-invoice text-primary me-2"></i> Estrutura de Documentação Pedagógica</h4>
        <p><strong>Módulo operacional ativo:</strong> {tipo_modulo}</p>
        <p><strong>Escopo Temático:</strong> {tema if tema else 'Objeto de Conhecimento Geral'} associado à disciplina de {disciplina}.</p>
        """