import os

try:
    from google import genai
    USE_NEW_SDK = True
except ImportError:
    import google.generativeai as genai
    USE_NEW_SDK = False

def gerar_conteudo_educacional(tipo_modulo, disciplina, ano, tema, bncc):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        return """
        <div class="alert alert-warning mt-3">
            <i class="fa-solid fa-triangle-exclamation me-2"></i>
            <strong>Chave API Não Configurada:</strong> A variável <code>GEMINI_API_KEY</code> não foi encontrada no Render. 
            Por favor, adicione-a no menu 'Environment' do seu painel do Render.
        </div>
        """
    
    # 📋 PROMPT ESPECIALIZADO PARA O LAYOUT DA SEMED PRESIDENTE DUTRA
    if tipo_modulo == "Planejamento Bimestral":
        prompt = f"""
        Você é um consultor pedagógico sênior especialista na estrutura curricular da SEMED de Presidente Dutra - MA e na BNCC.
        
        O professor forneceu as seguintes Unidades Temáticas de partida: "{tema}"
        Componente Curricular: {disciplina}
        Ano/Segmento: {ano}
        Diretrizes adicionais fornecidas pelo usuário: {bncc if bncc else "Nenhuma diretriz manual inserida."}
        
        Sua tarefa é expandir essas Unidades Temáticas e gerar COMPLETAMENTE o restante do Plano Bimestral oficial, estruturando a resposta EXCLUSIVAMENTE em tags HTML limpas (sem blocos de código markdown ```html), seguindo rigorosamente a estrutura abaixo:

        1. <h4 class="mt-4 border-bottom pb-2 text-dark font-weight-bold">COMPETÊNCIAS GERAIS DA EDUCAÇÃO BÁSICA</h4>
           (Selecione de 3 a 5 Competências Gerais da BNCC que tenham ligação direta com as unidades temáticas inseridas e liste-as de forma textual e numerada, ex: "1ª - Valorizar e utilizar os conhecimentos...", "2ª - Exercitar a curiosidade...", etc.)

        2. <h4 class="mt-4 border-bottom pb-2 text-dark font-weight-bold">COMPETÊNCIAS ESPECÍFICAS DE {disciplina.upper()}</h4>
           (Gere ou selecione as competências específicas da BNCC correspondentes a esta disciplina para este ano letivo, listadas como 1ª, 2ª, 3ª...)

        3. <h4 class="mt-4 border-bottom pb-2 text-dark font-weight-bold">OBJETOS DE CONHECIMENTO</h4>
           (Mapeie e detalhe os Objetos de Conhecimento/Conteúdos para cada Unidade Temática informada pelo professor, associando explicitamente cada um à sua respectiva UNIDADE, ex: "<strong>UNIDADE:</strong> Números / 4º ANO - Problemas envolvendo diferentes significados...")

        4. <h4 class="mt-4 border-bottom pb-2 text-dark font-weight-bold">HABILIDADES (BNCC)</h4>
           (Liste os códigos alfanuméricos oficiais da BNCC correspondentes e a descrição da habilidade completa, ex: "<strong>EF04MA06</strong> - Resolver e elaborar problemas...")

        5. <h4 class="mt-4 border-bottom pb-2 text-dark font-weight-bold">SUGESTÕES METODOLÓGICAS</h4>
           (Escreva uma lista detalhada e robusta de ações práticas, dinâmicas, sequências didáticas e atividades lúdicas aplicadas ao mundo real para o professor conduzir em sala de aula com base nesses conteúdos)

        6. <h4 class="mt-4 border-bottom pb-2 text-dark font-weight-bold">AVALIAÇÃO</h4>
           (Liste os critérios e instrumentos avaliativos adequados, como: Participação, Trabalhos em grupos, Devolutivas de atividades, Avaliação bimestral)

        7. <h4 class="mt-4 border-bottom pb-2 text-dark font-weight-bold">RECURSOS</h4>
           (Liste os materiais necessários: Livro didático, Data Show, Materiais manipuláveis, Cartazes, Softwares educativos, etc.)

        8. <h4 class="mt-4 border-bottom pb-2 text-dark font-weight-bold">REFERÊNCIAS</h4>
           (Inclua os documentos norteadores obrigatórios: BNCC, DCTMA - Documento Curricular Territorial do Maranhão, e referências de livros didáticos compatíveis)

        9. <h4 class="mt-4 border-bottom pb-2 text-dark font-weight-bold">OBSERVAÇÕES PERTINENTES</h4>
           (Insira recomendações pedagógicas importantes, como habilidades de anos anteriores que precisam de revisão/pré-requisito para este bimestre, cronograma de simulados ou projetos interdisciplinares do município)

        Regras de Formatação:
        - Use tags como <p>, <ul>, <li>, <strong> para manter o visual profissional.
        - Não use decorações markdown adicionais. Retorne apenas o código estruturado que vai direto para o papel.
        """
    else:
        # Prompt padrão para os outros módulos (Plano de aula comum, relatórios, etc)
        prompt = f"""
        Você é um especialista em educação de alto nível.
        Gere um conteúdo de excelência para o módulo '{tipo_modulo}', focado na disciplina de '{disciplina}' para o '{ano}'.
        Tema Principal / Objeto de Estudo: {tema}
        Diretrizes e Alinhamento com a BNCC: {bncc if bncc else "Diretrizes padrão"}
        
        Responda estruturando o texto APENAS em HTML elegante (use <p>, <ul>, <li>, <strong>, <h5>).
        NÃO inclua as marcações de bloco de código como ```html no início ou ``` no final.
        """
    
    try:
        if USE_NEW_SDK:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text if response.text else "O modelo retornou uma resposta vazia."
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text if response.text else "O modelo retornou uma resposta vazia."
            
    except Exception as e:
        return f"""
        <div class="alert alert-danger mt-3">
            <i class="fa-solid fa-circle-exclamation me-2"></i>
            <strong>Erro na comunicação com o Gemini AI:</strong> {str(e)}
        </div>
        """