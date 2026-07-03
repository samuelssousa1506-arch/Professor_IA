import os
import re
import sqlite3
import random
import requests
import markdown as md
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_mestra_professor_ia_2026")

# 1. MAPEAMENTO DA CHAVE GEMINI
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# Dicionário de módulos unificado
MODULOS = {
    'plano': {'nome': 'Plano de Aula', 'icone': 'fa-book'},
    'bimestral': {'nome': 'Planejamento Bimestral', 'icone': 'fa-calendar-check'},
    'atividades': {'nome': 'Banco de Atividades', 'icone': 'fa-list-check'},
    'avaliacoes': {'nome': 'Gerador de Provas', 'icone': 'fa-file-signature'},
    'duvidas': {'nome': 'Tira-Dúvidas com IA', 'icone': 'fa-circle-question'},
    'relatorios': {'nome': 'Relatórios Pedagógicos', 'icone': 'fa-chart-line'},
    'inclusao': {'nome': 'Plano de Inclusão / AEE', 'icone': 'fa-hands-asl-interpreting'},
    'projetos': {'nome': 'Projetos Interdisciplinares', 'icone': 'fa-diagram-project'}
}

# =====================================================================
# TEXTO OFICIAL FIXO — COMPETÊNCIAS GERAIS DA EDUCAÇÃO BÁSICA (BNCC, 2018)
# Fixado no backend (não gerado pela IA) para garantir fidelidade 100% ao
# texto oficial do MEC em todo Planejamento Bimestral, independente do tema.
# =====================================================================
COMPETENCIAS_GERAIS_BNCC = [
    "Valorizar e utilizar os conhecimentos historicamente construídos sobre o mundo físico, social, cultural e digital para entender e explicar a realidade, continuar aprendendo e colaborar para a construção de uma sociedade justa, democrática e inclusiva.",
    "Exercitar a curiosidade intelectual e recorrer à abordagem própria das ciências, incluindo a investigação, a reflexão, a análise crítica, a imaginação e a criatividade, para investigar causas, elaborar e testar hipóteses, formular e resolver problemas e criar soluções (inclusive tecnológicas) com base nos conhecimentos das diferentes áreas.",
    "Valorizar e fruir as diversas manifestações artísticas e culturais, das locais às mundiais, e também participar de práticas diversificadas da produção artístico-cultural.",
    "Utilizar diferentes linguagens – verbal (oral ou visual-motora, como Libras, e escrita), corporal, visual, sonora e digital –, bem como conhecimentos das linguagens artística, matemática e científica, para se expressar e partilhar informações, experiências, ideias e sentimentos em diferentes contextos e produzir sentidos que levem ao entendimento mútuo.",
    "Compreender, utilizar e criar tecnologias digitais de informação e comunicação de forma crítica, significativa, reflexiva e ética nas diversas práticas sociais (incluindo as escolares) para se comunicar, acessar e disseminar informações, produzir conhecimentos, resolver problemas e exercer protagonismo e autoria na vida pessoal e coletiva.",
    "Valorizar a diversidade de saberes e vivências culturais e apropriar-se de conhecimentos e experiências que lhe possibilitem entender as relações próprias do mundo do trabalho e fazer escolhas alinhadas ao exercício da cidadania e ao seu projeto de vida, com liberdade, autonomia, consciência crítica e responsabilidade.",
    "Argumentar com base em fatos, dados e informações confiáveis, para formular, negociar e defender ideias, pontos de vista e decisões comuns que respeitem e promovam os direitos humanos, a consciência socioambiental e o consumo responsável em âmbito local, regional e global, com posicionamento ético em relação ao cuidado de si mesmo, dos outros e do planeta.",
    "Conhecer-se, apreciar-se e cuidar de sua saúde física e emocional, compreendendo-se na diversidade humana e reconhecendo suas emoções e as dos outros, com autocrítica e capacidade para lidar com elas.",
    "Exercitar a empatia, o diálogo, a resolução de conflitos e a cooperação, fazendo-se respeitar e promovendo o respeito ao outro e aos direitos humanos, com acolhimento e valorização da diversidade de indivíduos e de grupos sociais, seus saberes, identidades, culturas e potencialidades, sem preconceitos de qualquer natureza.",
    "Agir pessoal e coletivamente com autonomia, responsabilidade, flexibilidade, resiliência e determinação, tomando decisões com base em princípios éticos, democráticos, inclusivos, sustentáveis e solidários.",
]

def montar_html_competencias_gerais():
    ordinais = ["1ª", "2ª", "3ª", "4ª", "5ª", "6ª", "7ª", "8ª", "9ª", "10ª"]
    itens = "".join(
        f"<p><strong>{ordinais[i]}</strong> - {texto}</p>"
        for i, texto in enumerate(COMPETENCIAS_GERAIS_BNCC)
    )
    return f'<h5 class="doc-secao-titulo">Competências Gerais da Educação Básica</h5><div class="doc-secao-corpo">{itens}</div>'

def sanitizar_saida_html(texto):
    """
    Rede de segurança: mesmo instruindo o Gemini a responder em HTML puro,
    modelos de linguagem eventualmente retornam sintaxe Markdown (###, **, *).
    Esta função detecta esse padrão e converte para HTML real antes de renderizar.
    """
    texto = texto.strip()

    # Heurística: se encontrarmos marcadores clássicos de Markdown, convertemos.
    parece_markdown = bool(re.search(r'(^|\n)#{2,6}\s|\*\*[^*]+\*\*|(^|\n)\*\s|(^|\n)-\s', texto))

    if parece_markdown:
        texto = md.markdown(texto, extensions=['tables', 'nl2br', 'sane_lists'])

    return texto.strip()

def obter_fallback_pedagogico(tipo_modulo, tema, erro_adicional=""):
    return f"""
    <h4><i class="fa-solid fa-graduation-cap text-primary me-2"></i> {tipo_modulo} (Modo de Segurança)</h4>
    <p>O sistema não conseguiu conectar ao Gemini em tempo real. Certifique-se de que configurou a variável <strong>GEMINI_API_KEY</strong> corretamente no painel do Render.</p>
    <p><strong>Tema enviado:</strong> {tema}</p>
    {f'<p class="text-danger small"><strong>Detalhes do Erro:</strong> {erro_adicional}</p>' if erro_adicional else ''}
    """

def executar_geracao_ia(**kwargs):
    tipo_modulo = kwargs.get('tipo_modulo', 'Banco de Atividades')
    tema = kwargs.get('tema', '')
    disciplina = kwargs.get('disciplina', 'Geral')
    ano = kwargs.get('ano', 'Geral')
    bncc = kwargs.get('bncc', '')
    tipo_prova = kwargs.get('tipo_prova', 'Mista')
    qtd_questoes = kwargs.get('qtd_questoes', '10')
    nivel = kwargs.get('nivel', 'Médio')
    nome_professor = kwargs.get('nome_professor', 'Professor(a)')
    nome_escola = kwargs.get('nome_escola', 'Instituição de Ensino')

    # Campos específicos do Planejamento Bimestral (formato oficial SEMED)
    numero_plano = kwargs.get('numero_plano', '')
    bimestre = kwargs.get('bimestre', '1º BIM')
    data_inicio = kwargs.get('data_inicio', '')
    data_fim = kwargs.get('data_fim', '')
    turma = kwargs.get('turma', '')
    turno = kwargs.get('turno', '')
    modalidade = kwargs.get('modalidade', 'Presencial')
    ano_letivo = kwargs.get('ano_letivo', '')
    inep = kwargs.get('inep', '')
    endereco_escola = kwargs.get('endereco_escola', '')
    cidade_escola = kwargs.get('cidade_escola', '')
    estado_escola = kwargs.get('estado_escola', 'MA')
    zona_escola = kwargs.get('zona_escola', '')
    telefone_escola = kwargs.get('telefone_escola', '')
    email_escola = kwargs.get('email_escola', '')
    observacoes = kwargs.get('observacoes', '')

    if not GEMINI_API_KEY:
        return obter_fallback_pedagogico(tipo_modulo, tema, "A variável GEMINI_API_KEY está ausente no painel do Render.")

    # -----------------------------------------------------------------
    # EXTRAÇÃO CIRÚRGICA DA CHAVE COM REGEX (Ignora qualquer formatação de link)
    # -----------------------------------------------------------------
    # O padrão procura pela sequência que começa com AIza ou AQ e pega apenas caracteres válidos de chave
    match = re.search(r'(AIzaSy[A-Za-z0-9_-]+|AQ\.[A-Za-z0-9_-]+)', GEMINI_API_KEY)
    
    if match:
        chave_limpa = match.group(1).strip()
    else:
        # Fallback caso a regex não isole (remove manualmente caracteres de link comuns)
        chave_limpa = GEMINI_API_KEY.replace("[", "").replace("]", "").replace("'", "").replace('"', '')
        if "key=" in chave_limpa:
            chave_limpa = chave_limpa.split("key=")[-1]
        if ")" in chave_limpa:
            chave_limpa = chave_limpa.split(")")[-1]
        chave_limpa = chave_limpa.strip()
    # -----------------------------------------------------------------

    # 2. CONSTRUÇÃO DO PROMPT PEDAGÓGICO
    regras_formato = """
        REGRAS OBRIGATÓRIAS DE FORMATAÇÃO DA SAÍDA:
        - Responda ESTRITAMENTE em HTML puro e semântico (tags: h4, h5, p, strong, em, ul, ol, li, table, thead, tbody, tr, th, td, div).
        - NUNCA utilize sintaxe Markdown (proibido: #, ##, ###, **texto**, *item*, -, ```). Se precisar de negrito use <strong>, se precisar de título use <h4>/<h5>, se precisar de lista use <ul><li>.
        - NUNCA inclua delimitadores de bloco de código como ```html ou ```.
        - Use <table class="tabela-bncc"> quando fizer sentido organizar habilidades BNCC, cronogramas ou critérios de avaliação em formato tabular.
    """
    if tipo_modulo == 'Tira-Dúvidas com IA':
        prompt = f"""
        Você é um Consultor Jurídico-Pedagógico especialista e expert em Legislação Educacional Brasileira.
        Responda com total precisão técnica fundamentando-se OBRIGATORIAMENTE em: BNCC (Base Nacional Comum Curricular), LDB (Lei nº 9.394/96), DCTMA (Documento Curricular do Território Maranhense) e, quando pertinente, na Seção da Educação da Constituição Federal.
        Sempre que citar um desses documentos, indique de forma explícita o artigo, competência ou eixo correspondente.
        Dúvida ou Consulta do Professor: "{tema}"
        {regras_formato}
        """
    elif tipo_modulo == 'Planejamento Bimestral':
        numero_final = numero_plano.strip() or str(random.randint(10000, 99999))
        ano_letivo_final = ano_letivo.strip() or str(datetime.now().year)
        criado_em = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        turma_completa = f"{ano} | ({turma}) | {turno}".upper() if turma or turno else ano.upper()
        periodo_execucao = f"{data_inicio} a {data_fim}" if data_inicio and data_fim else "[preencher período de execução]"

        prompt = f"""
        Atue como um Especialista em Planejamento Pedagógico Escolar, com domínio profundo da BNCC (Base Nacional Comum Curricular), da LDB (Lei nº 9.394/96) e do DCTMA (Documento Curricular do Território Maranhense).
        Gere um PLANEJAMENTO BIMESTRAL completo e oficial, seguindo EXATAMENTE a estrutura, ordem de seções e nível de detalhamento abaixo — este é o modelo oficial usado pela Secretaria Municipal de Educação, e deve ser reproduzido fielmente.

        {regras_formato}
        REGRA ADICIONAL CRÍTICA: Não gere você mesmo a seção "Competências Gerais da Educação Básica". No lugar exato indicado abaixo, insira apenas o marcador literal <!--COMPETENCIAS_GERAIS_AQUI--> (sem nenhum texto ao redor, sem tags H5, apenas o comentário HTML). Esse marcador será substituído automaticamente pelo sistema pelo texto oficial completo.

        ESTRUTURA OBRIGATÓRIA DO DOCUMENTO, NESTA ORDEM EXATA:

        1. <div class="doc-cabecalho-oficial">
           Inclua, em formato de linhas rotuladas (<p><strong>RÓTULO:</strong> valor</p>):
           INEP: {inep or '[preencher]'}
           ESCOLA: {nome_escola}
           ENDEREÇO: {endereco_escola or '[preencher endereço]'}
           CIDADE: {cidade_escola or '[preencher cidade]'} ESTADO: {estado_escola}
           ZONA: {zona_escola or '[preencher]'} TELEFONE: {telefone_escola or '[preencher]'} EMAIL: {email_escola or '[preencher]'}
           </div>

        2. <h2 class="doc-titulo-oficial">PLANO BIMESTRAL #{numero_final}</h2>

        3. <div class="doc-metadata-oficial">
           Em linhas rotuladas, exatamente nesta ordem:
           BIMESTRAL // {modalidade}
           {bimestre} {periodo_execucao}
           TURMA: {turma_completa}
           COMP. CURR.: {disciplina}
           EXECUÇÃO: {periodo_execucao}
           CRIADO EM: {criado_em}
           PROFESSOR(A): {nome_professor}
           ANO LETIVO: {ano_letivo_final}
           </div>

        4. <!--COMPETENCIAS_GERAIS_AQUI-->

        5. <h5 class="doc-secao-titulo">Competências Específicas de {disciplina}</h5>
           Liste, numeradas (1ª, 2ª, 3ª...), as competências específicas oficiais da BNCC para a área de conhecimento à qual "{disciplina}" pertence (ex: Ciências da Natureza, Matemática, Linguagens, Ciências Humanas), voltadas ao Ensino Fundamental — Anos Finais. Seja fiel ao texto oficial, sem inventar.

        6. <h5 class="doc-secao-titulo">Unidades Temáticas</h5>
           Identifique a(s) unidade(s) temática(s) da BNCC relacionada(s) ao tema "{tema}" para a série/ano "{ano}", no formato "Nome da Unidade / {ano}".

        7. <h5 class="doc-secao-titulo">Objetos de Conhecimento</h5>
           Liste os objetos de conhecimento relacionados ao tema, cada um seguido de "UNIDADE: [nome da unidade] / {ano}".

        8. <h5 class="doc-secao-titulo">Habilidades</h5>
           Liste as habilidades da BNCC pertinentes (formato: código - descrição completa da habilidade). Priorize o código informado pelo professor ({bncc if bncc else 'nenhum código específico informado — selecione os mais adequados ao tema'}) e complemente com habilidades relacionadas do mesmo objeto de conhecimento.

        9. <h5 class="doc-secao-titulo">Sugestões Metodológicas</h5>
           Lista <ul><li> com 8 a 10 sugestões práticas e variadas de condução das aulas ao longo do bimestre (leitura, TIC, debates, mapas conceituais, saída de campo, mostra científica, etc.), adaptadas ao tema e à realidade do Maranhão quando pertinente.

        10. <h5 class="doc-secao-titulo">Avaliação</h5>
            Lista <ul><li> com os instrumentos avaliativos do bimestre (ex: Avaliação Bimestral, Seminários, Trabalhos individuais e em grupo, etc.), adequados ao tema.

        11. <h5 class="doc-secao-titulo">Recursos</h5>
            Lista <ul><li> com os recursos didáticos necessários (materiais, equipamentos, tecnologia).

        12. <h5 class="doc-secao-titulo">Referências</h5>
            Liste em linhas simples (sem bullets), formato ABNT simplificado:
            BRASIL. Ministério da Educação. Documento Curricular do Território Maranhense (DCTMA): para o ensino fundamental. Rio de Janeiro: FGV, [ano mais recente conhecido].
            BRASIL. Ministério da Educação. Base Nacional Comum Curricular (BNCC). Brasília, 2018.
            E, se pertinente ao tema/disciplina, uma referência bibliográfica de livro didático real e amplamente reconhecido (não invente autores/obras).

        13. <h5 class="doc-secao-titulo">Observações Pertinentes</h5>
            {f'Inclua o seguinte texto informado pelo professor: "{observacoes}"' if observacoes else 'Deixe um parágrafo curto padrão indicando que não há observações adicionais registradas, ou omita se preferir deixar em branco.'}

        DADOS DE CONFIGURAÇÃO DO ESCOPO:
        - Componente/Disciplina: {disciplina}
        - Ano/Série Escolar: {ano}
        - Tema Central / Objeto de Estudo: {tema}
        - Código de Habilidade BNCC Alvo: {bncc}
        """
    else:
        prompt = f"""
        Atue como um Especialista em Design Pedagógico e Elaboração de Conteúdo Escolar Avançado, com domínio profundo da BNCC, da LDB (Lei nº 9.394/96) e do DCTMA (Documento Curricular do Território Maranhense).
        Gere o conteúdo completo e detalhado para o documento estruturado do módulo '{tipo_modulo}'.

        CABEÇALHO OBRIGATÓRIO DO DOCUMENTO (gere como primeiro bloco, em uma <div class="cabecalho-documento">):
        - Instituição de Ensino: {nome_escola}
        - Professor(a) Responsável: {nome_professor}
        - Componente Curricular: {disciplina}
        - Ano/Série: {ano}
        - Data de Geração: [inserir placeholder ___/___/______ para preenchimento manual]

        FUNDAMENTAÇÃO LEGAL OBRIGATÓRIA:
        Todo o conteúdo pedagógico deve estar alinhado e referenciar explicitamente, quando aplicável:
        1. BNCC — cite a(s) competência(s) geral(is) e a(s) habilidade(s) específica(s) trabalhada(s).
        2. LDB (Lei nº 9.394/96) — cite o artigo pertinente aos princípios/fins da educação relacionados ao tema.
        3. DCTMA — cite o eixo ou orientação curricular do território maranhense relacionado.
        Inclua uma seção final <h5>Fundamentação Legal</h5> resumindo essas referências.

        DADOS DE CONFIGURAÇÃO DO ESCOPO:
        - Componente/Disciplina: {disciplina}
        - Ano/Série Escolar: {ano}
        - Tema Central / Objeto de Estudo: {tema}
        - Código de Habilidade BNCC Alvo: {bncc}
        - Nível de Rigor Cognitivo: {nivel}
        {regras_formato}
        """
        if tipo_modulo == 'Gerador de Provas':
            prompt += f"""
            DIRETRIZES DO GERADOR DE PROVAS EXCLUSIVAS:
            1. Você deve gerar exatamente {qtd_questoes} questões no formato de aplicação: {tipo_prova}.
            2. Utilize estritamente numeração sequencial de dois dígitos seguida de ponto (Exemplo: 01., 02., 03.).
            3. Sempre inclua a diretriz BNCC entre parênteses logo após o número. Exemplo: '01. (EF09MA02) '.
            4. Todo o texto do enunciado da pergunta DEVE estar encapsulado dentro da tag HTML <strong>...</strong>.
            5. Para questões objetivas, organize alternativas perfeitamente alinhadas verticalmente de a) até d) separadas por quebras de linha <br>.
            6. Para questões discursivas ou subjetivas, adicione o espaço para escrita do aluno aplicando a tag: <div class="linha-resposta"></div> repetida 3 vezes consecutivas.
            """
        elif tipo_modulo == 'Plano de Aula':
            prompt += """
            SEÇÃO OBRIGATÓRIA — METODOLOGIAS E SUGESTÕES DE AULAS DIFERENCIADAS:
            Inclua, antes da conclusão do plano, uma seção <h5>Sugestões de Aulas Diferenciadas</h5> com pelo menos 3 a 4 propostas concretas e variadas para trabalhar o tema de formas alternativas à aula expositiva tradicional, por exemplo (adapte ao tema e ano/série informados):
            - Aula prática/experimental (uso de materiais concretos, experimentos, manipuláveis).
            - Metodologia ativa (sala de aula invertida, aprendizagem baseada em problemas/projetos, gamificação).
            - Atividade em grupo/colaborativa (debate, júri simulado, oficina, estudo de caso).
            - Uso de tecnologia/recursos digitais (aplicativos, vídeos, simuladores, jogos educativos).
            - Conexão com o cotidiano/comunidade local (saída de campo, entrevista, estudo do meio, quando aplicável ao contexto maranhense).
            Apresente cada sugestão em formato de lista <ul><li>, com um parágrafo curto (2-3 linhas) explicando como aplicá-la e qual habilidade/competência da BNCC ela reforça.

            SEÇÃO FINAL OBRIGATÓRIA — REFERÊNCIAS:
            Ao final do documento, após todo o conteúdo pedagógico, inclua uma seção <h5>Referências</h5> contendo:
            1. As referências normativas/legais utilizadas, no formato ABNC simplificado, por exemplo:
               BRASIL. Ministério da Educação. Base Nacional Comum Curricular (BNCC). Brasília: MEC, 2018.
               BRASIL. Lei nº 9.394, de 20 de dezembro de 1996. Lei de Diretrizes e Bases da Educação Nacional (LDB). Brasília, 1996.
               MARANHÃO. Secretaria de Estado da Educação. Documento Curricular do Território Maranhense (DCTMA). São Luís, [ano de publicação mais recente conhecido].
            2. Quaisquer referências bibliográficas pedagógicas adicionais (autores, teóricos ou materiais didáticos) efetivamente utilizados como base conceitual para o conteúdo gerado, também em formato ABNT simplificado, listadas em <ul><li>.
            3. Não invente nomes de autores ou obras específicas que não sejam amplamente reconhecidas na área; se não houver referência bibliográfica adicional além das normativas, inclua apenas as normativas.
            """
        else:
            prompt += f"\nEstruture o documento de forma oficial e profissional com cabeçalhos h4, h5, parágrafos bem espaçados e listas dinâmicas."

    # 3. ENDPOINT DA API DO GEMINI COM A URL 100% HIGIENIZADA
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={chave_limpa}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            resultado = response.json()
            texto_gerado = resultado['candidates'][0]['content']['parts'][0]['text']
            texto_gerado = texto_gerado.replace("```html", "").replace("```", "").strip()
            texto_gerado = sanitizar_saida_html(texto_gerado)
            # Substitui o marcador pelo texto oficial fixo das Competências Gerais da Educação Básica
            if '<!--COMPETENCIAS_GERAIS_AQUI-->' in texto_gerado:
                texto_gerado = texto_gerado.replace('<!--COMPETENCIAS_GERAIS_AQUI-->', montar_html_competencias_gerais())
            return texto_gerado
        else:
            return obter_fallback_pedagogico(tipo_modulo, tema, f"Código {response.status_code} - Resposta: {response.text}")
            
    except Exception as e:
        return obter_fallback_pedagogico(tipo_modulo, tema, f"Falha de conexão física: {str(e)}")

# =====================================================================
# INICIALIZAÇÃO DO BANCO DE DADOS (SQLite)
# =====================================================================
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            escola TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        )
    ''')
    cursor.execute("SELECT * FROM usuarios WHERE LOWER(email) = 'samuel.ssousa1506@gmail.com'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO usuarios (nome, escola, email, senha) 
            VALUES ('Samuel Araújo Sousa', 'U.E. Prof. João Martins Neto', 'samuel.ssousa1506@gmail.com', '123456')
        ''')
    conn.commit()
    conn.close()

init_db()

# =====================================================================
# ROTAS FLASK
# =====================================================================
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return redirect(url_for('dashboard', form_type='plano'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    sucesso = request.args.get('sucesso')
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('senha', '').strip()
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT nome, escola, senha FROM usuarios WHERE LOWER(email) = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and str(user[2]).strip() == password:
            session['logged_in'] = True
            session['user_email'] = email
            session['user_name'] = user[0]   
            session['user_school'] = user[1] 
            return redirect(url_for('dashboard', form_type='plano'))
        else:
            erro = "E-mail ou senha incorretos."
    return render_template('login.html', erro=erro, sucesso=sucesso)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    erro = None
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        escola = request.form.get('escola', '').strip()
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '').strip()
        
        if not nome or not escola or not email or not senha:
            erro = "Todos os campos são obrigatórios."
        else:
            try:
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO usuarios (nome, escola, email, senha) VALUES (?, ?, ?, ?)",
                    (nome, escola, email, senha)
                )
                conn.commit()
                conn.close()
                return redirect(url_for('login', sucesso="Conta criada com sucesso! Faça login."))
            except sqlite3.IntegrityError:
                erro = "Este e-mail já está cadastrado no sistema."
    return render_template('cadastro.html', erro=erro)

@app.route('/dashboard', methods=['GET', 'POST'])
@app.route('/gerador', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    form_type = request.args.get('form_type') or request.form.get('form_type') or 'plano'
    if form_type not in MODULOS:
        form_type = 'plano'
        
    config_modulo = MODULOS[form_type]
    conteudo = ""
    
    tema = request.form.get('tema', '').strip()
    disciplina = request.form.get('disciplina', '').strip()
    ano = request.form.get('ano', '').strip()
    bncc = request.form.get('bncc', '').strip()
    tipo_prova = request.form.get('tipo_prova', '').strip()
    qtd_questoes = request.form.get('qtd_questoes', '').strip()
    nivel = request.form.get('nivel', '').strip()

    # Campos específicos do Planejamento Bimestral
    numero_plano = request.form.get('numero_plano', '').strip()
    bimestre = request.form.get('bimestre', '1º BIM').strip()
    data_inicio = request.form.get('data_inicio', '').strip()
    data_fim = request.form.get('data_fim', '').strip()
    turma = request.form.get('turma', '').strip()
    turno = request.form.get('turno', '').strip()
    modalidade = request.form.get('modalidade', 'Presencial').strip()
    ano_letivo = request.form.get('ano_letivo', '').strip()
    inep = request.form.get('inep', '').strip()
    endereco_escola = request.form.get('endereco_escola', '').strip()
    cidade_escola = request.form.get('cidade_escola', '').strip()
    estado_escola = request.form.get('estado_escola', 'MA').strip()
    zona_escola = request.form.get('zona_escola', '').strip()
    telefone_escola = request.form.get('telefone_escola', '').strip()
    email_escola = request.form.get('email_escola', '').strip()
    observacoes = request.form.get('observacoes', '').strip()

    if request.method == 'POST' and tema:
        conteudo = executar_geracao_ia(
            tipo_modulo=config_modulo['nome'],
            disciplina=disciplina,
            ano=ano,
            tema=tema,
            bncc=bncc,
            tipo_prova=tipo_prova,
            qtd_questoes=qtd_questoes,
            nivel=nivel,
            nome_professor=session.get('user_name', 'Professor(a)'),
            nome_escola=session.get('user_school', 'Instituição de Ensino'),
            numero_plano=numero_plano,
            bimestre=bimestre,
            data_inicio=data_inicio,
            data_fim=data_fim,
            turma=turma,
            turno=turno,
            modalidade=modalidade,
            ano_letivo=ano_letivo,
            inep=inep,
            endereco_escola=endereco_escola,
            cidade_escola=cidade_escola,
            estado_escola=estado_escola,
            zona_escola=zona_escola,
            telefone_escola=telefone_escola,
            email_escola=email_escola,
            observacoes=observacoes
        )

    return render_template(
        'dashboard.html',
        form_type=form_type,
        config=config_modulo,
        conteudo=conteudo,
        tema=tema,
        disciplina=disciplina if disciplina else "Componente Curricular",
        ano=ano,
        bncc=bncc,
        tipo_prova=tipo_prova,
        qtd_questoes=qtd_questoes,
        nivel=nivel,
        numero_plano=numero_plano,
        bimestre=bimestre,
        data_inicio=data_inicio,
        data_fim=data_fim,
        turma=turma,
        turno=turno,
        modalidade=modalidade,
        ano_letivo=ano_letivo,
        inep=inep,
        endereco_escola=endereco_escola,
        cidade_escola=cidade_escola,
        estado_escola=estado_escola,
        zona_escola=zona_escola,
        telefone_escola=telefone_escola,
        email_escola=email_escola,
        observacoes=observacoes,
        app_name="Professor IA",
        name=session.get('user_name', 'Samuel Araújo Sousa'),     
        school=session.get('user_school', 'U.E. Prof. João Martins Neto')  
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)