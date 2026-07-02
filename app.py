import os
import sqlite3
import requests
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_mestra_professor_ia_2026")

# Recupera a chave configurada no Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

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

def obter_fallback_pedagogico(tipo_modulo, tema):
    return f"""
    <h4><i class="fa-solid fa-graduation-cap text-primary me-2"></i> {tipo_modulo} (Modo de Segurança)</h4>
    <p>Não foi possível conectar à IA em tempo real. Verifique se a variável <strong>GEMINI_API_KEY</strong> está salva no Render.</p>
    <p>Tema solicitado: {tema}</p>
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

    if not GEMINI_API_KEY:
        return obter_fallback_pedagogico(tipo_modulo, tema)

    # Engenharia de prompt unificada
    if tipo_modulo == 'Tira-Dúvidas com IA':
        prompt = f"""
        Você é um Consultor Jurídico-Pedagógico especialista em Legislação Educacional Brasileira.
        Responda com precisão sobre: BNCC, LDB (Lei 9.394/96), DCTMA (Documento Curricular do Território Maranhense) e Constituição Federal.
        
        Dúvida do Professor: "{tema}"
        
        Retorne a resposta COMPLETA em HTML limpo (usando h4, p, strong, ul, li). Não use blocos de código markdown (sem ```html).
        """
    else:
        prompt = f"""
        Atue como um Especialista em Design Pedagógico. Gere o conteúdo completo para o documento '{tipo_modulo}'.
        Escopo: Disciplina: {disciplina} | Ano: {ano} | Tema: {tema} | BNCC: {bncc} | Nível: {nivel}
        """
        if tipo_modulo == 'Gerador de Provas':
            prompt += f"""
            Gere exatamente {qtd_questoes} questões no formato {tipo_prova}.
            Use numeração sequencial (01., 02.), inclua a BNCC correspondente entre parênteses e coloque o enunciado dentro de <strong>.
            Para questões de marcar, coloque alternativas de a) até d) com quebras <br>.
            Para discursivas, use <div class="linha-resposta"></div> para as linhas.
            """
        else:
            prompt += f"\nEstruture o documento com títulos h4, parágrafos e listas estruturadas."

    # Chamada direta via API REST (Evita incompatibilidade de versão da biblioteca)
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=){GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 8192,
            "temperature": 0.5 if tipo_modulo == 'Tira-Dúvidas com IA' else 0.7
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            resultado = response.json()
            texto_gerado = resultado['candidates'][0]['content']['parts'][0]['text']
            # Limpa qualquer resíduo de markdown que a IA teime em colocar
            return texto_gerado.replace("```html", "").replace("```", "").strip()
        else:
            return obter_fallback_pedagogico(tipo_modulo, tema) + f"<p class='text-danger'>Erro da API: Código {response.status_code}</p>"
    except Exception as e:
        return obter_fallback_pedagogico(tipo_modulo, tema)

# =====================================================================
# BANCO DE DADOS E ROTAS FLASK
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