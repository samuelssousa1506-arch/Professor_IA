import os
import sqlite3
import sys
from flask import Flask, render_template, request, redirect, url_for, session

# Importação da biblioteca oficial do Gemini
try:
    import google.generativeai as genai
    from google.api_core import errors
    GEMINI_DISPONIVEL = True
except ImportError:
    GEMINI_DISPONIVEL = False

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_mestra_professor_ia_2026")

# Configuração da API Key obtida das variáveis de ambiente
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY and GEMINI_DISPONIVEL:
    genai.configure(api_key=GEMINI_API_KEY)

# =====================================================================
# SEÇÃO PEDAGÓGICA (MÓDULO DE GERAÇÃO COM EXPERT EM LEGISLAÇÃO)
# =====================================================================
def obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano):
    """Fallback estruturado no padrão exigido pelo modelo real."""
    if tipo_modulo == 'Tira-Dúvidas com IA':
        return f"""
        <h4><i class="fa-solid fa-graduation-cap text-primary me-2"></i> Consultoria Pedagógica (Modo de Segurança)</h4>
        <p>Você perguntou sobre: <strong>{tema}</strong></p>
        <hr>
        <h5>Informações de Referência Educacional:</h5>
        <p>Para consultas aprofundadas sobre a <strong>BNCC (Base Nacional Comum Curricular)</strong>, <strong>LDB (Lei de Diretrizes e Bases - Lei nº 9.394/96)</strong>, <strong>DCTMA (Documento Curricular do Território Maranhense)</strong> ou o Artigo 205 ao 214 da <strong>Constituição Federal</strong>, certifique-se de que sua chave de API está ativa para receber respostas dinâmicas e contextualizadas da IA.</p>
        """
    elif tipo_modulo == 'Gerador de Provas':
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
        <p><strong>Escopo Temático:</strong> {tema if tema else 'Objeto de Conhecimento Geral'}.</p>
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
        
        # Engenharia de Prompt focada no novo perfil de Expert Jurídico/Pedagógico Educacional
        if tipo_modulo == 'Tira-Dúvidas com IA':
            prompt = f"""
            Você é um Consultor Jurídico-Pedagógico de Elite e Cientista Educacional, expert absoluto em Legislação Educacional Brasileira e Diretrizes Curriculares.
            Sua especialidade cobre com precisão técnica milimétrica:
            - BNCC (Base Nacional Comum Curricular)
            - LDB (Lei de Diretrizes e Bases da Educação Nacional - Lei nº 9.394/196)
            - DCTMA (Documento Curricular do Território Maranhense)
            - Seção da Educação na Constituição Federal de 1988 (Artigos 205 a 214)
            - Planos Nacionais e Municipais de Educação, Teorias de Aprendizagem e Didática Aplicada.

            O Professor solicitou a seguinte consulta ou dúvida sobre o universo educacional:
            "{tema}"

            INSTRUÇÕES DE RESPOSTA:
            1. Responda de forma clara, didática, fundamentada na lei e extremamente profissional. Citando artigos, incisos, competências ou habilidades específicas sempre que aplicável.
            2. Formate sua resposta utilizando HTML limpo e estruturado. Use títulos com <h4> ou <h5> para organizar as seções, listas estruturadas com <ul> e <li>, parágrafos bem espaçados e termos cruciais ou citações de leis destacadas em <strong>...</strong>.
            3. Não inclua blocos de código markdown ou delimitadores de texto (como ```html). Retorne diretamente as tags HTML prontas para renderização visual bonita em uma folha.
            """
        else:
            prompt = f"""
            Atue como um Especialista em Design Pedagógico e Elaboração de Avaliações Escolares Oficiais.
            Sua tarefa é gerar o conteúdo COMPLETO do início ao fim em HTML limpo para o módulo '{tipo_modulo}'.
            
            DADOS DO ESCOPO:
            - Disciplina: {disciplina} | Ano/Série: {ano} | Tema: {tema} | BNCC: {bncc} | Rigor: {nivel}
            """
            if tipo_modulo == 'Gerador de Provas':
                prompt += f"""
                - Quantidade Exata de Questões: DEVE GERAR EXATAMENTE {qtd_questoes} QUESTÕES.
                - Formato: {tipo_prova}

                DIRETRIZES OBRIGATÓRIAS (PADRÃO DO DOCUMENTO REAL):
                1. Numeração sequencial de dois dígitos (Exemplo: 01., 02., até {qtd_questoes}).
                2. Inclua a diretriz BNCC entre parênteses logo após a numeração. Use o código ({bncc}) ou deduza um correto caso vazio. Exemplo: '01. (EF09MA02) '.
                3. Todo o texto do enunciado da questão DEVE estar dentro de <strong>...</strong> (Negrito).
                4. Para Objetivas/Mistas, alternativas de 'a)' até 'd)' alinhadas verticalmente e separadas por <br>.
                5. Para Subjetivas, adicione de 3 a 4 linhas de resposta usando: <div class="linha-resposta"></div>.
                6. IMPORTANTE: Retorne diretamente o código HTML limpo, sem markdown.
                """
            else:
                prompt += f"""
                Gere um documento robusto e completo de {tipo_modulo} sobre o tema {tema}.
                Estruture utilizando títulos H4, listas organizadas (UL/LI) e parágrafos bem definidos. 
                Retorne em HTML limpo sem delimitadores de markdown.
                """

        response = model.generate_content(prompt, generation_config=configuracao)
        conteudo_limpo = response.text.replace("```html", "").replace("```", "").strip()
        return conteudo_limpo

    except errors.ResourceExhausted:
        return f"""
        <div class="alert alert-warning no-print my-3 py-3 border-start border-warning border-3 rounded-3" style="background-color: #fffbeb;">
            <h5 class="fw-bold text-warning-dark mb-1"><i class="fa-solid fa-triangle-exclamation me-2"></i> Limite Diário Excedido (Quota da API)</h5>
            <p class="small text-muted mb-0">Quota atingida. Modo de segurança ativo abaixo.</p>
        </div>
        {obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano)}
        """
    except Exception as e:
        return obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano)

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

# Adicionado o novo módulo na estrutura global do sistema
MODULOS = {
    'plano': {'nome': 'Plano de Aula', 'icone': 'fa-book'},
    'bimestral': {'nome': 'Planejamento Bimestral', 'icone': 'fa-calendar-check'},
    'atividades': {'nome': 'Banco de Atividades', 'icone': 'fa-list-check'},
    'avaliacoes': {'nome': 'Gerador de Provas', 'icone': 'fa-file-signature'},
    'duvidas': {'nome': 'Tira-Dúvidas com IA', 'icone': 'fa-graduation-cap'},
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
                return redirect(url_for('login',色素sucesso="Conta criada com sucesso! Faça login."))
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
            disciplina=disciplina if disciplina else "Geral",
            ano=ano if ano else "Geral",
            tema=tema,
            bncc=bncc if bncc else "",
            tipo_prova=tipo_prova if tipo_prova else "Mista",
            qtd_questoes=qtd_questoes if qtd_questoes else "10",
            nivel=nivel if nivel else "Médio"
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