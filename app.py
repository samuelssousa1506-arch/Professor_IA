import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session

# Importa o serviço de IA configurado com a nova biblioteca do Google
from ai_service import gerar_conteudo_educacional

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_mestra_professor_ia_2026")

# Banco de Dados: Função para inicializar as tabelas necessárias
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
    # Garante que o acesso do desenvolvedor Samuel sempre existirá por padrão
    cursor.execute("SELECT * FROM usuarios WHERE email = 'samuel.ssousa1506@gmail.com'")
    if not cursor.fetchone():
        # CORRIGIDO: Mudado 'school' para 'escola' para bater com a tabela acima
        cursor.execute('''
            INSERT INTO usuarios (nome, escola, email, senha) 
            VALUES ('Samuel Araújo Sousa', 'Fábrica de Software', 'samuel.ssousa1506@gmail.com', '123456')
        ''')
    conn.commit()
    conn.close()

# Executa a inicialização do banco ao rodar o app
init_db()

# Mapas de configuração visual de cada módulo do sistema
MODULOS = {
    'plano': {'nome': 'Plano de Aula', 'cor': '#4e73df', 'icone': 'fa-book'},
    'bimestral': {'nome': 'Planejamento Bimestral', 'cor': '#fd7e14', 'icone': 'fa-calendar-check'},
    'atividades': {'nome': 'Banco de Atividades', 'cor': '#1cc88a', 'icone': 'fa-list-check'},
    'avaliacoes': {'nome': 'Gerador de Provas', 'cor': '#36b9cc', 'icone': 'fa-file-signature'},
    'relatorios': {'nome': 'Relatórios Pedagógicos', 'cor': '#f6c23e', 'icone': 'fa-chart-line'},
    'inclusao': {'nome': 'Plano de Inclusão / AEE', 'cor': '#e74a3b', 'icone': 'fa-hands-asl-interpreting'},
    'projetos': {'nome': 'Projetos Interdisciplinares', 'cor': '#6f42c1', 'icone': 'fa-diagram-project'}
}

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
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT nome, escola, senha FROM usuarios WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and user[2] == password:
            session['logged_in'] = True
            session['user_email'] = email
            session['user_name'] = user[0]   
            session['user_school'] = user[1] 
            return redirect(url_for('index'))
        else:
            erro = "E-mail ou senha incorretos."
            
    return render_template('login.html', erro=erro, sucesso=sucesso)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    erro = None
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        escola = request.form.get('escola', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()
        
        if nome and escola and email and senha:
            try:
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO usuarios (nome, escola, email, senha)
                    VALUES (?, ?, ?, ?)
                ''', (nome, escola, email, senha))
                conn.commit()
                conn.close()
                return redirect(url_for('login', sucesso="Conta criada com sucesso! Entre abaixo."))
            except sqlite3.IntegrityError:
                erro = "Este e-mail já está cadastrado no sistema."
        else:
            erro = "Por favor, preencha todos os campos."
            
    return render_template('cadastro.html', erro=erro)

def executar_logica_painel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    form_type = request.args.get('form_type') or request.form.get('form_type') or 'plano'
    if form_type not in MODULOS:
        form_type = 'plano'
        
    config_modulo = MODULOS[form_type]
    
    conteudo = ""
    tema = ""
    disciplina = ""
    ano = ""
    bncc = ""
    
    if request.method == 'POST':
        tema = request.form.get('tema', '').strip()
        disciplina = request.form.get('disciplina', '').strip()
        ano = request.form.get('ano', '').strip()
        bncc = request.form.get('bncc', '').strip()
        
        if tema:
            conteudo = gerar_conteudo_educacional(
                tipo_modulo=config_modulo['nome'],
                disciplina=disciplina if disciplina else "Geral",
                ano=ano if ano else "Segmento Geral",
                tema=tema,
                bncc=bncc if bncc else "Diretrizes gerais da BNCC"
            )
        else:
            conteudo = "Por favor, defina um Tema Principal antes de solicitar a geração do material."

    return render_template(
        'dashboard.html',
        form_type=form_type,
        config=config_modulo,
        conteudo=conteudo,
        tema=tema,
        disciplina=disciplina,
        ano=ano,
        bncc=bncc,
        app_name="Professor IA",
        name=session.get('user_name'),     
        school=session.get('user_school')  
    )

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    return executar_logica_painel()

@app.route('/gerador', methods=['GET', 'POST'])
def gerador():
    return executar_logica_painel()

@app.route('/banco')
def banco():
    return redirect(url_for('dashboard', form_type='atividades'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)