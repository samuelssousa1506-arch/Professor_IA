import os
import re
import json
import sqlite3
import random
import requests
import markdown as md
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import io
import weasyprint
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

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
    texto = texto.strip()
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

# ------------------- FUNÇÕES DE EXTRAÇÃO E CHAMADA IA -------------------
def extrair_chave_api():
    chave = GEMINI_API_KEY.strip()
    chave = re.sub(r'[\[\]\'"]', '', chave)
    if 'key=' in chave:
        chave = chave.split('key=')[-1]
    if ')' in chave:
        chave = chave.split(')')[-1]
    chave = chave.strip()
    if re.match(r'(AIzaSy[A-Za-z0-9_-]{35}|AQ\.[A-Za-z0-9_-]+)', chave):
        return chave
    return None

def chamar_gemini(prompt, chave):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={chave}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            texto = data['candidates'][0]['content']['parts'][0]['text']
            texto = texto.replace("```html", "").replace("```", "").strip()
            texto = sanitizar_saida_html(texto)
            if '<!--COMPETENCIAS_GERAIS_AQUI-->' in texto:
                texto = texto.replace('<!--COMPETENCIAS_GERAIS_AQUI-->', montar_html_competencias_gerais())
            return texto
        else:
            return f"<!--ERRO--> Código {resp.status_code}: {resp.text}"
    except Exception as e:
        return f"<!--ERRO--> {str(e)}"

# =====================================================================
# FUNÇÕES DE MONTAGEM DE PROMPTS
# =====================================================================

def montar_prompt_plano_aula(dados):
    tema = dados.get('tema', '')
    disciplina = dados.get('disciplina', 'Geral')
    ano = dados.get('ano', 'Geral')
    bncc = dados.get('bncc', '')
    return f"""
    Você é um especialista em planejamento de aulas, com base na BNCC, LDB e DCTMA.
    Gere um plano de aula detalhado para:
    - Disciplina: {disciplina}
    - Ano/Série: {ano}
    - Tema: {tema}
    - Código BNCC: {bncc if bncc else 'selecione o mais adequado'}

    O plano deve conter:
    1. Título da aula
    2. Objetivos (geral e específicos)
    3. Habilidades BNCC trabalhadas
    4. Conteúdos
    5. Metodologia (descrição passo a passo)
    6. Recursos didáticos
    7. Avaliação
    8. Referências

    Responda em HTML puro, sem Markdown.
    """

def montar_prompt_bimestral(dados):
    # ATENÇÃO: Substitua este placeholder pelo prompt completo do Planejamento Bimestral
    return """
    <h4>Planejamento Bimestral</h4>
    <p><strong>ATENÇÃO:</strong> Substitua este placeholder pelo prompt completo do Planejamento Bimestral.</p>
    """

def montar_prompt_atividade(dados):
    tema = dados.get('tema', '')
    disciplina = dados.get('disciplina', 'Geral')
    ano = dados.get('ano', 'Geral')
    quantidade = dados.get('quantidade', '10')
    nivel = dados.get('nivel', 'Médio')
    tipos = dados.get('tipos_atividade', [])
    bncc = dados.get('bncc', '')
    tipos_str = ', '.join(tipos) if tipos else 'variados'
    prompt = f"""
    Você é um especialista em design de atividades pedagógicas, com profundo conhecimento da BNCC, LDB e DCTMA.
    Crie uma atividade educativa para o seguinte contexto:
    - Disciplina: {disciplina}
    - Ano/Série: {ano}
    - Tema/Conteúdo: {tema}
    - Nível de dificuldade: {nivel}
    - Tipos de questões solicitados: {tipos_str}
    - Quantidade de questões: {quantidade}
    - Código BNCC de referência: {bncc if bncc else 'não informado, selecione os mais adequados'}

    A atividade deve conter:
    1. Um título apropriado.
    2. Instruções claras para o aluno.
    3. As questões numeradas, com os tipos solicitados.
    4. Um gabarito ao final, com as respostas corretas (quando aplicável).
    5. As questões devem ser contextualizadas, criativas e alinhadas à BNCC.

    Responda em HTML puro, sem Markdown. Use <h4> para título, <p> para instruções, <ol> ou <ul> para questões, e uma seção <h5>Gabarito</h5> no final.
    """
    return prompt

# =====================================================================
# PROMPT GERADOR DE PROVAS – com 2 colunas e Arial 12
# =====================================================================
def montar_prompt_prova(dados):
    tema = dados.get('tema', '')
    disciplina = dados.get('disciplina', '')
    ano = dados.get('ano', '')
    tipo_prova = dados.get('tipo_prova', 'Mista')
    qtd_questoes = dados.get('qtd_questoes', '10')
    nivel = dados.get('nivel', 'Médio')
    bncc = dados.get('bncc', '')
    prompt = f"""
    Você é um especialista em elaboração de avaliações, alinhado à BNCC, LDB e DCTMA.
    Crie uma prova com as seguintes características:
    - Disciplina: {disciplina}
    - Ano/Série: {ano}
    - Tema/Conteúdo: {tema}
    - Formato: {tipo_prova} (Mista = objetivas + subjetivas; Apenas Objetivas; Apenas Subjetivas)
    - Quantidade de questões: {qtd_questoes}
    - Nível de dificuldade: {nivel}
    - Código BNCC de referência: {bncc if bncc else 'selecione os mais adequados'}

    A prova deve ser formatada em duas colunas de tamanho igual, com fonte Arial 12.
    A estrutura HTML deve ser:
    - Título: <h4 class="titulo-prova">AVALIAÇÃO BIMESTRAL DE {disciplina.upper()}</h4>
    - As questões devem ser agrupadas em uma <div class="questoes-2col"> que aplica duas colunas via CSS (column-count: 2).
    - Cada questão deve ter a classe .questao e conter:
      * Enunciado em negrito: <strong>01. (código) texto da questão</strong>
      * Alternativas como <p class="alt">a) texto</p>, <p class="alt">b) ...</p>, etc. (sem marcadores)
      * Para subjetivas, inclua <div class="linha-resposta"></div> três vezes após o enunciado.
    - Não inclua cabeçalho, apenas o título e as questões.
    - Ao final, inclua uma seção <div class="gabarito"> com o gabarito (para o professor).

    Exemplo de estrutura:
    <div class="questoes-2col">
      <div class="questao">
        <strong>01. (EF09MA02) Qual é ...</strong>
        <p class="alt">a) alternativa A</p>
        <p class="alt">b) alternativa B</p>
        <p class="alt">c) alternativa C</p>
        <p class="alt">d) alternativa D</p>
      </div>
      <!-- próxima questão -->
    </div>
    <div class="gabarito">...</div>

    Responda em HTML puro, sem Markdown. A fonte deve ser Arial 12 (não use Times).
    """
    return prompt

def montar_prompt_duvidas(dados):
    tema = dados.get('tema', '')
    return f"""
    Você é um Consultor Jurídico-Pedagógico especialista em Legislação Educacional Brasileira.
    Responda com total precisão técnica fundamentando-se OBRIGATORIAMENTE em: BNCC, LDB (Lei nº 9.394/96), DCTMA e, quando pertinente, na Constituição Federal.
    Sempre que citar um desses documentos, indique de forma explícita o artigo, competência ou eixo correspondente.
    Dúvida ou Consulta do Professor: "{tema}"
    Responda em HTML puro, sem Markdown.
    """

def montar_prompt_relatorio(dados):
    tema = dados.get('tema', '')
    disciplina = dados.get('disciplina', '')
    ano = dados.get('ano', '')
    return f"""
    Você é um especialista em relatórios pedagógicos. Gere um relatório descritivo para:
    - Disciplina: {disciplina}
    - Ano/Série: {ano}
    - Tema/Conteúdo: {tema}
    Inclua: diagnóstico, desenvolvimento, resultados, recomendações.
    Responda em HTML puro, sem Markdown.
    """

def montar_prompt_inclusao(dados):
    tema = dados.get('tema', '')
    disciplina = dados.get('disciplina', '')
    ano = dados.get('ano', '')
    return f"""
    Você é um especialista em educação inclusiva e AEE. Elabore um plano de atendimento educacional especializado para:
    - Disciplina: {disciplina}
    - Ano/Série: {ano}
    - Tema: {tema}
    Inclua: objetivos, adaptações curriculares, recursos, estratégias, avaliação.
    Responda em HTML puro, sem Markdown.
    """

def montar_prompt_projeto(dados):
    tema = dados.get('tema', '')
    serie = dados.get('serie', '')
    disciplina = dados.get('disciplina', '')
    duracao = dados.get('duracao', '')
    objetivo = dados.get('objetivo', '')
    tipos = dados.get('tipos_projeto', [])
    tipos_str = ', '.join(tipos) if tipos else 'Projeto Interdisciplinar'
    prompt = f"""
    Você é um especialista em projetos pedagógicos interdisciplinares, com base na BNCC, LDB e DCTMA.
    Elabore um projeto completo para os seguintes dados:
    - Tema: {tema}
    - Série/Ano: {serie}
    - Disciplina(s) envolvida(s): {disciplina}
    - Duração prevista: {duracao}
    - Objetivo geral do projeto: {objetivo}
    - Tipo(s) de projeto: {tipos_str}

    O projeto deve conter as seguintes seções, nesta ordem (em HTML puro, sem Markdown):
    1. <h4>Justificativa</h4>
    2. <h4>Objetivos</h4> (Geral e Específicos)
    3. <h4>Competências da BNCC</h4>
    4. <h4>Habilidades da BNCC</h4>
    5. <h4>Metodologia</h4>
    6. <h4>Cronograma</h4> (tabela)
    7. <h4>Recursos</h4>
    8. <h4>Desenvolvimento</h4>
    9. <h4>Avaliação</h4>
    10. <h4>Produto Final</h4>
    11. <h4>Referências</h4>
    """
    return prompt

def montar_prompt_generico(tipo_modulo, dados):
    tema = dados.get('tema', '')
    disciplina = dados.get('disciplina', '')
    ano = dados.get('ano', '')
    return f"""
    Você é um especialista em educação. Gere conteúdo para o módulo {tipo_modulo}.
    Tema: {tema}
    Disciplina: {disciplina}
    Ano: {ano}
    Responda em HTML puro, estruturado com cabeçalhos e listas.
    """

# ------------------- FUNÇÃO PRINCIPAL DE GERAÇÃO -------------------
def gerar_conteudo_ia(tipo_modulo, dados):
    if not GEMINI_API_KEY:
        return obter_fallback_pedagogico(tipo_modulo, dados.get('tema', ''), "Chave API ausente.")
    chave = extrair_chave_api()
    if not chave:
        return obter_fallback_pedagogico(tipo_modulo, dados.get('tema', ''), "Chave inválida.")
    
    prompt_map = {
        'Plano de Aula': montar_prompt_plano_aula,
        'Planejamento Bimestral': montar_prompt_bimestral,
        'Banco de Atividades': montar_prompt_atividade,
        'Gerador de Provas': montar_prompt_prova,
        'Tira-Dúvidas com IA': montar_prompt_duvidas,
        'Relatórios Pedagógicos': montar_prompt_relatorio,
        'Plano de Inclusão / AEE': montar_prompt_inclusao,
        'Projetos Interdisciplinares': montar_prompt_projeto,
    }
    func = prompt_map.get(tipo_modulo, montar_prompt_generico)
    prompt = func(dados)
    resposta = chamar_gemini(prompt, chave)
    if resposta.startswith('<!--ERRO-->'):
        return obter_fallback_pedagogico(tipo_modulo, dados.get('tema', ''), resposta)
    return resposta

# =====================================================================
# INICIALIZAÇÃO DO BANCO DE DADOS (SQLite) - ATUALIZADO
# =====================================================================
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Tabela de usuários com hash
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            escola TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL
        )
    ''')
    # Tabela de materiais salvos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materiais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            dados_ia TEXT,
            favorito INTEGER DEFAULT 0,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    # Tabela de questões reutilizáveis
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            ano TEXT,
            disciplina TEXT,
            conteudo TEXT,
            bncc TEXT,
            dificuldade TEXT,
            tipo TEXT,
            enunciado TEXT NOT NULL,
            alternativas TEXT,
            gabarito TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    # Inserir usuário padrão (Samuel) com senha hash
    hash_senha = generate_password_hash('123456')
    try:
        cursor.execute(
            "INSERT INTO usuarios (nome, escola, email, senha_hash) VALUES (?, ?, ?, ?)",
            ('Samuel Araújo Sousa', 'U.E. Prof. João Martins Neto', 'samuel.ssousa1506@gmail.com', hash_senha)
        )
    except sqlite3.IntegrityError:
        pass
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
        cursor.execute("SELECT id, nome, escola, senha_hash FROM usuarios WHERE LOWER(email) = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user[3], password):
            session['logged_in'] = True
            session['user_id'] = user[0]
            session['user_email'] = email
            session['user_name'] = user[1]
            session['user_school'] = user[2]
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
                hash_senha = generate_password_hash(senha)
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO usuarios (nome, escola, email, senha_hash) VALUES (?, ?, ?, ?)",
                    (nome, escola, email, hash_senha)
                )
                conn.commit()
                conn.close()
                return redirect(url_for('login', sucesso="Conta criada com sucesso! Faça login."))
            except sqlite3.IntegrityError:
                erro = "Este e-mail já está cadastrado no sistema."
    return render_template('cadastro.html', erro=erro)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    form_type = request.args.get('form_type') or request.form.get('form_type') or 'plano'
    if form_type not in MODULOS:
        form_type = 'plano'
        
    config_modulo = MODULOS[form_type]
    conteudo = ""
    dados_ia = {}
    
    # Captura campos comuns
    tema = request.form.get('tema', '').strip()
    disciplina = request.form.get('disciplina', '').strip()
    ano = request.form.get('ano', '').strip()
    bncc = request.form.get('bncc', '').strip()
    tipo_prova = request.form.get('tipo_prova', '').strip()
    qtd_questoes = request.form.get('qtd_questoes', '').strip()
    nivel = request.form.get('nivel', '').strip()
    
    # Planejamento Bimestral
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
    
    # Atividades
    quantidade = request.form.get('quantidade', '10').strip()
    tipos_atividade = request.form.getlist('tipos_atividade')
    
    # Projetos
    serie = request.form.get('serie', '').strip()
    duracao = request.form.get('duracao', '').strip()
    objetivo = request.form.get('objetivo', '').strip()
    tipos_projeto = request.form.getlist('tipos_projeto')
    
    if request.method == 'POST' and tema:
        dados = {
            'tipo_modulo': config_modulo['nome'],
            'disciplina': disciplina,
            'ano': ano,
            'tema': tema,
            'bncc': bncc,
            'tipo_prova': tipo_prova,
            'qtd_questoes': qtd_questoes,
            'nivel': nivel,
            'nome_professor': session.get('user_name', 'Professor(a)'),
            'nome_escola': session.get('user_school', 'Instituição de Ensino'),
            'numero_plano': numero_plano,
            'bimestre': bimestre,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'turma': turma,
            'turno': turno,
            'modalidade': modalidade,
            'ano_letivo': ano_letivo,
            'inep': inep,
            'endereco_escola': endereco_escola,
            'cidade_escola': cidade_escola,
            'estado_escola': estado_escola,
            'zona_escola': zona_escola,
            'telefone_escola': telefone_escola,
            'email_escola': email_escola,
            'observacoes': observacoes,
            'quantidade': quantidade,
            'tipos_atividade': tipos_atividade,
            'serie': serie,
            'duracao': duracao,
            'objetivo': objetivo,
            'tipos_projeto': tipos_projeto,
        }
        conteudo = gerar_conteudo_ia(config_modulo['nome'], dados)
        
        # Extração para provas: informações pedagógicas e gabarito
        if form_type == 'avaliacoes' and conteudo:
            match_pedagogico = re.search(r'<div class="info-pedagogica"[^>]*>(.*?)</div>', conteudo, re.DOTALL)
            if match_pedagogico:
                dados_ia['pedagogico'] = match_pedagogico.group(1)
                conteudo = re.sub(r'<div class="info-pedagogica"[^>]*>.*?</div>', '', conteudo, flags=re.DOTALL)
            else:
                dados_ia['pedagogico'] = 'Informações pedagógicas não disponíveis.'
            
            match_gabarito = re.search(r'<div class="gabarito"[^>]*>(.*?)</div>', conteudo, re.DOTALL)
            if match_gabarito:
                dados_ia['gabarito'] = match_gabarito.group(1)
                conteudo = re.sub(r'<div class="gabarito"[^>]*>.*?</div>', '', conteudo, flags=re.DOTALL)
            else:
                dados_ia['gabarito'] = ''
    
    return render_template(
        'dashboard.html',
        form_type=form_type,
        config=config_modulo,
        conteudo=conteudo,
        dados_ia=dados_ia,
        tema=tema,
        disciplina=disciplina,
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
        quantidade=quantidade,
        tipos_atividade=tipos_atividade,
        serie=serie,
        duracao=duracao,
        objetivo=objetivo,
        tipos_projeto=tipos_projeto,
        app_name="Professor IA",
        name=session.get('user_name', 'Samuel Araújo Sousa'),
        school=session.get('user_school', 'U.E. Prof. João Martins Neto')
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# =====================================================================
# ROTAS PARA BIBLIOTECA E EDIÇÃO
# =====================================================================
@app.route('/salvar_material', methods=['POST'])
def salvar_material():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    usuario_id = session.get('user_id')
    titulo = request.form.get('titulo', 'Material sem título')
    tipo = request.form.get('tipo', 'geral')
    conteudo = request.form.get('conteudo', '')
    dados_ia = request.form.get('dados_ia', '{}')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO materiais (usuario_id, titulo, tipo, conteudo, dados_ia) VALUES (?, ?, ?, ?, ?)",
        (usuario_id, titulo, tipo, conteudo, dados_ia)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('biblioteca'))

@app.route('/biblioteca')
def biblioteca():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    usuario_id = session.get('user_id')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, tipo, data_criacao, favorito, conteudo FROM materiais WHERE usuario_id = ? ORDER BY data_criacao DESC", (usuario_id,))
    materiais = cursor.fetchall()
    conn.close()
    return render_template('biblioteca.html', materiais=materiais)

@app.route('/editar_material/<int:material_id>', methods=['GET', 'POST'])
def editar_material(material_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    usuario_id = session.get('user_id')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    if request.method == 'POST':
        novo_titulo = request.form.get('titulo')
        novo_conteudo = request.form.get('conteudo')
        cursor.execute(
            "UPDATE materiais SET titulo = ?, conteudo = ? WHERE id = ? AND usuario_id = ?",
            (novo_titulo, novo_conteudo, material_id, usuario_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('biblioteca'))
    else:
        cursor.execute("SELECT id, titulo, conteudo, tipo FROM materiais WHERE id = ? AND usuario_id = ?", (material_id, usuario_id))
        material = cursor.fetchone()
        conn.close()
        if not material:
            return "Material não encontrado", 404
        return render_template('editar_material.html', material=material)

@app.route('/favoritar_material/<int:material_id>', methods=['POST'])
def favoritar_material(material_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    usuario_id = session.get('user_id')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE materiais SET favorito = 1 - favorito WHERE id = ? AND usuario_id = ?", (material_id, usuario_id))
    conn.commit()
    conn.close()
    return redirect(url_for('biblioteca'))

@app.route('/excluir_material/<int:material_id>', methods=['POST'])
def excluir_material(material_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    usuario_id = session.get('user_id')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM materiais WHERE id = ? AND usuario_id = ?", (material_id, usuario_id))
    conn.commit()
    conn.close()
    return redirect(url_for('biblioteca'))

# =====================================================================
# ROTA DE EXPORTAÇÃO (com 2 colunas e Arial 12)
# =====================================================================
@app.route('/exportar', methods=['POST'])
def exportar():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    formato = request.form.get('formato', 'pdf')
    conteudo_html = request.form.get('conteudo', '')
    tipo = request.form.get('tipo', 'geral')
    disciplina = request.form.get('disciplina', '')
    
    # Cabeçalho com nome da escola e professor já preenchidos
    if tipo == 'avaliacoes':
        cabecalho = f"""
        <div style="text-align: center; margin-bottom: 20px; border-bottom: 2px solid #0e2a5e; padding-bottom: 10px;">
            <h3 style="color: #0e2a5e; font-family: Arial, sans-serif; font-size: 14pt;">{session.get('user_school', '')}</h3>
            <p style="font-family: Arial, sans-serif; font-size: 12pt;"><strong>Professor(a):</strong> {session.get('user_name', '')}</p>
            <p style="font-family: Arial, sans-serif; font-size: 12pt;"><strong>Disciplina:</strong> {disciplina}</p>
            <p style="font-family: Arial, sans-serif; font-size: 12pt;"><strong>Nome do(a) Aluno(a):</strong> ________________________________________________</p>
            <p style="font-family: Arial, sans-serif; font-size: 12pt;"><strong>Turma:</strong> _____________    <strong>Data:</strong> ____/____/________    <strong>Nota:</strong> _______</p>
        </div>
        """
    else:
        cabecalho = f"""
        <div style="text-align: center; margin-bottom: 20px; border-bottom: 2px solid #0e2a5e; padding-bottom: 10px;">
            <h3 style="color: #0e2a5e; font-family: Arial, sans-serif; font-size: 14pt;">{session.get('user_school', '')}</h3>
            <p style="font-family: Arial, sans-serif; font-size: 12pt;"><strong>Professor(a):</strong> {session.get('user_name', '')}</p>
        </div>
        """
    
    # Para provas, extrai apenas a div .questoes (já vem com 2 colunas)
    if tipo == 'avaliacoes':
        match = re.search(r'<div class="questoes-2col">(.*?)</div>', conteudo_html, re.DOTALL)
        if match:
            # Pega o conteúdo da div .questoes-2col
            questoes_html = match.group(1)
        else:
            # Fallback: se não encontrar, usa todo o conteúdo
            questoes_html = conteudo_html
        
        # Remove gabarito e info-pedagogica do conteúdo principal
        conteudo_html = re.sub(r'<div class="gabarito"[^>]*>.*?</div>', '', conteudo_html, flags=re.DOTALL)
        conteudo_html = re.sub(r'<div class="info-pedagogica"[^>]*>.*?</div>', '', conteudo_html, flags=re.DOTALL)
        # Usa apenas as questões em 2 colunas
        conteudo_html = f'<div class="questoes-2col">{questoes_html}</div>'
    
    # CSS para duas colunas, Arial 12
    css_profissional = """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; font-size: 12pt; line-height: 1.5; margin: 0.5in; color: #000; }
        .titulo-prova { text-align: center; font-size: 14pt; font-weight: 700; text-transform: uppercase; margin: 0.5rem 0 1.2rem 0; letter-spacing: 1px; color: #0e2a5e; font-family: Arial, sans-serif; }
        .questoes-2col { column-count: 2; column-gap: 40px; column-fill: auto; }
        .questao { margin-bottom: 1.2rem; break-inside: avoid; page-break-inside: avoid; }
        .questao strong { font-weight: 700; display: block; margin-bottom: 0.2rem; }
        .questao .alt { margin-left: 1.2rem; margin-bottom: 0.1rem; }
        .linha-resposta { border-bottom: 1px dotted #999; margin: 10px 0; height: 0; }
        .gabarito { margin-top: 20px; padding-top: 10px; border-top: 2px solid #0e2a5e; column-span: all; }
        hr { border: 0; border-top: 2px solid #0e2a5e; }
        /* Ajustes para impressão */
        @media print {
            body { margin: 0.5in; }
            .questoes-2col { column-gap: 30px; }
            .questao { margin-bottom: 0.8rem; }
        }
    </style>
    """
    
    html_completo = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Documento Exportado</title>
    {css_profissional}
    </head>
    <body>
        {cabecalho}
        {conteudo_html}
        <!-- O gabarito fica apenas na visualização, não é exportado -->
    </body>
    </html>
    """
    
    if formato == 'pdf':
        pdf = weasyprint.HTML(string=html_completo).write_pdf()
        return send_file(io.BytesIO(pdf), as_attachment=True, download_name='documento.pdf', mimetype='application/pdf')
    else:  # docx
        doc = Document()
        if tipo == 'avaliacoes':
            doc.add_heading(session.get('user_school', ''), level=1)
            doc.add_paragraph(f'Professor(a): {session.get("user_name", "")}')
            doc.add_paragraph(f'Disciplina: {disciplina}')
            doc.add_paragraph('Nome do(a) Aluno(a): ________________________________________________')
            doc.add_paragraph('Turma: _____________      Data: ____/____/________      Nota: _______')
        else:
            doc.add_heading(session.get('user_school', ''), level=1)
            doc.add_paragraph(f'Professor(a): {session.get("user_name", "")}')
        doc.add_paragraph('')
        doc.add_paragraph(conteudo_html)
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name='documento.docx', mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

# =====================================================================
# ROTA PARA SALVAR QUESTÃO (BANCO DE QUESTÕES)
# =====================================================================
@app.route('/salvar_questao', methods=['POST'])
def salvar_questao():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    usuario_id = session.get('user_id')
    dados = request.form
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO questoes (usuario_id, ano, disciplina, conteudo, bncc, dificuldade, tipo, enunciado, alternativas, gabarito)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (usuario_id, dados.get('ano'), dados.get('disciplina'), dados.get('conteudo'),
         dados.get('bncc'), dados.get('dificuldade'), dados.get('tipo'),
         dados.get('enunciado'), dados.get('alternativas'), dados.get('gabarito'))
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)