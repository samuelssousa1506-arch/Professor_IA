import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session

try:
    from ai_service import gerar_conteudo_educacional
except ImportError:
    # Fallback pedagógico configurado exatamente com o padrão estrutural do teu PDF
    def gerar_conteudo_educacional(**kwargs):
        if kwargs.get('tipo_modulo') == 'Gerador de Provas':
            return """
            <p><strong>01. (EF09MA02) O número &pi; é usado em situações geométricas como, por exemplo, no cálculo do comprimento de uma circunferência. Seu valor aproximado é 3,141592... Portanto, podemos afirmar que ele é um número:</strong></p>
            <p>a) natural.<br>b) inteiro.<br>c) racional.<br>d) irracional.</p>
            <br>
            <p><strong>02. (EF09MA04) O Brasil possui uma população estimada de 203 milhões de habitantes, segundo o IBGE. Em notação científica, escrevemos este número como:</strong></p>
            <p>a) 203 x 10<sup>7</sup><br>b) 2,03 x 10<sup>7</sup><br>c) 2,03 x 10<sup>-8</sup><br>d) 2,03 x 10<sup>8</sup></p>
            <br>
            <p><strong>03. (EF09MA03) Um conjunto habitacional possui 6 prédios. Cada prédio tem 6 andares, e cada andar, 6 apartamentos. O número total de apartamentos é representado por:</strong></p>
            <p>a) 6<sup>3</sup><br>b) 6<sup>4</sup><br>c) 6<sup>5</sup><br>d) 6<sup>6</sup></p>
            <br>
            <p><strong>04. (EF09MA02) Indique qual alternativa a seguir apresenta um número classificado como irracional:</strong></p>
            <p>a) &radic;400<br>b) &radic;144<br>c) &radic;196<br>d) &radic;250</p>
            """
        return "<h3>Conteúdo gerado para o tema: " + kwargs.get('tema', '') + "</h3>"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_mestra_professor_ia_2026")

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

MODULOS = {
    'plano': {'nome': 'Plano de Aula', 'icone': 'fa-book'},
    'bimestral': {'nome': 'Planejamento Bimestral', 'icone': 'fa-calendar-check'},
    'atividades': {'nome': 'Banco de Atividades', 'icone': 'fa-list-check'},
    'avaliacoes': {'nome': 'Gerador de Provas', 'icone': 'fa-file-signature'},
    'relatorios': {'nome': 'Relatórios Pedagógicos', 'icone': 'fa-chart-line'},
    'inclusao': {'nome': 'Plano de Inclusão / AEE', 'icone': 'fa-hands-asl-interpreting'},
    'projetos': {'nome': 'Projetos Interdisciplinares', 'icone': 'fa-diagram-project'}
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
    return render_template('login.html', erro=erro,致sucesso=sucesso)

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
        conteudo = gerar_conteudo_educacional(
            tipo_modulo=config_modulo['nome'],
            disciplina=disciplina if disciplina else "Geral",
            ano=ano if ano else "Segmento Geral",
            tema=tema,
            bncc=bncc if bncc else "",
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
        name=session.get('user_name', 'Professor'),     
        school=session.get('user_school', 'Instituição de Ensino')  
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)