import os
import sqlite3
import sys
from flask import Flask, render_template, request, redirect, url_for, session

try:
    import google.generativeai as genai
    from google.api_core import errors
    GEMINI_DISPONIVEL = True
except ImportError:
    GEMINI_DISPONIVEL = False

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_mestra_professor_ia_2026")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY and GEMINI_DISPONIVEL:
    genai.configure(api_key=GEMINI_API_KEY)

# Mapeamento Global unificado com o HTML
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

def obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano):
    if tipo_modulo == 'Tira-Dúvidas com IA':
        return f"""
        <h4><i class="fa-solid fa-graduation-cap text-primary me-2"></i> Consultoria Pedagógica (Modo de Segurança)</h4>
        <p>Você perguntou sobre: <strong>{tema}</strong></p>
        <hr>
        <h5>Informações de Referência Educacional:</h5>
        <p>Para consultas sobre a <strong>BNCC</strong>, <strong>LDB</strong> ou <strong>DCTMA</strong>, certifique-se de que sua chave de API está ativa no painel do Render.</p>
        """
    elif tipo_modulo == 'Gerador de Provas':
        return f"""
        <p><strong>01. (EF09MA02) O número &pi; (Pi) pertence ao conjunto dos números:</strong></p>
        <p>a) naturais.<br>b) inteiros.<br>c) racionais.<br>d) irracionais.</p>
        <br>
        <p><strong>02. (EF09MA04) Escrevemos 203 milhões de habitantes em Notação Científica como:</strong></p>
        <p>a) 2,03 x 10<sup>7</sup><br>b) 2,03 x 10<sup>8</sup></p>
        """
    else:
        return f"""
        <h4><i class="fa-solid fa-file-invoice text-primary me-2"></i> Estrutura Operacional</h4>
        <p><strong>Módulo ativo:</strong> {tipo_modulo}</p>
        <p><strong>Tema solicitado:</strong> {tema}</p>
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

    if not GEMINI_DISPONIVEL or not GEMINI_API_KEY:
        return obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano)

    try:
        configuracao = genai.types.GenerationConfig(
            max_output_tokens=8192,
            temperature=0.5 if tipo_modulo == 'Tira-Dúvidas com IA' else 0.7
        )
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        if tipo_modulo == 'Tira-Dúvidas com IA':
            prompt = f"""
            Você é um Consultor Jurídico-Pedagógico especialista em Legislação Educacional Brasileira.
            Responda de forma clara e fundamentada sobre: BNCC, LDB, DCTMA e Constituição Federal.
            
            Dúvida do Professor: "{tema}"
            
            Retorne em HTML estruturado (h4, p, strong, ul, li) sem delimitadores markdown.
            """
        else:
            prompt = f"""
            Atue como um Especialista em Design Pedagógico. Gere o conteúdo completo para '{tipo_modulo}'.
            Escopo: Disciplina: {disciplina} | Ano: {ano} | Tema: {tema} | BNCC: {bncc} | Nível: {nivel}
            """
            if tipo_modulo == 'Gerador de Provas':
                prompt += f"""
                Gere exatamente {qtd_questoes} questões no formato {tipo_prova}.
                Use numeração 01., 02., inclua a BNCC entre parênteses e enunciados em <strong>.
                """

        response = model.generate_content(prompt, generation_config=configuracao)
        return response.text.replace("```html", "").replace("```", "").strip()

    except Exception:
        return obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano)

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

    # Coleta o form_type tanto de requisições GET quanto POST de forma segura
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
    
    if request.method == 'POST' and tema:
        conteudo = executar_geracao_ia(
            tipo_modulo=config_modulo['nome'],
            disciplina=disciplina,
            ano=ano,
            tema=tema,
            bncc=bncc,
            tipo_prova=tipo_prova,
            qtd_questoes=qtd_questoes,
            nivel=nivel
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