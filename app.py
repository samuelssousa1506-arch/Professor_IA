import os
from flask import Flask, render_template, request, redirect, url_for, session

# Importa o serviço de IA configurado com a nova biblioteca do Google
from ai_service import gerar_conteudo_educacional

app = Flask(__name__)
# Chave secreta obrigatória para gerir sessões de login de forma segura
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_mestra_professor_ia_2026")

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
    # Se NÃO estiver logado, vai para a tela de login
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    # Se estiver logado, vai direto para o painel
    return redirect(url_for('dashboard', form_type='plano'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validação simples com as suas credenciais
        if email == "samuel.ssousa1506@gmail.com" and password == "123456":
            session['logged_in'] = True
            session['user_email'] = email
            return redirect(url_for('index'))
        else:
            erro = "E-mail ou senha incorretos."
            
    return render_template('login.html', erro=erro)

def executar_logica_painel():
    """
    Função centralizada que processa os formulários e faz a chamada ao Gemini.
    """
    # Bloqueio de segurança: impede acesso direto via URL sem login
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
        name="Samuel Araújo Sousa",
        school="Fábrica de Software"
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
    # Limpa a sessão e desloga o utilizador completamente
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)