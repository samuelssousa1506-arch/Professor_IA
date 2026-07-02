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
# SEÇÃO PEDAGÓGICA (MÓDULO DE GERAÇÃO OTIMIZADO)
# =====================================================================
def obter_fallback_pedagogico(tipo_modulo, tema, disciplina, ano):
    """Fallback estruturado exatamente no padrão exigido pelo modelo PDF real."""
    if tipo_modulo == 'Gerador de Provas':
        return f"""
        <p><strong>01. (EF09MA02) O número &pi; (Pi) é o nome dado ao quociente entre as medidas da circunferência e do diâmetro de um mesmo círculo. Este número possui infinitas casas decimais e não possui um período que se repita. Portanto, podemos afirmar corretamente que o número &pi; pertence ao conjunto dos números:</strong></p>
        <p>a) naturais.<br>b) inteiros.<br>c) racionais.<br>d) irracionais.</p>
        <br>
        <p><strong>02. (EF09MA04) O Brasil possui uma população estimada de aproximadamente 203 milhões de habitantes, de acordo com o último censo demográfico oficial do IBGE. Assinale a alternativa que apresenta a escrita correta desse número habitacional em Notação Científica:</strong></p>
        <p>a) 203 x 10<sup>7</sup><br>b) 2,03 x 10<sup>7</sup><br>c) 2,03 x 10<sup>-8</sup><br>d) 2,03 x 10<sup>8</sup></p>
        <br>
        <p><strong>03. (EF09MA03) Um determinado conjunto habitacional planejado é composto por exatamente 6 prédios residenciais. Sabendo que cada prédio tem 6 andares, e cada andar possui 6 apartamentos mapeados, indique a potência que representa o número total de apartamentos:</strong></p>
        <p>a) 6<sup>3</sup><br>b) 6<sup>4</sup><br>c) 6<sup>5</sup><br>d) 6<sup>6</sup></p>
        <br>
        <p><strong>04. (EF09MA02) Analise as propriedades matemáticas das raíces quadradas listadas abaixo e marque a opção que representa necessariamente a raiz cujo resultado final é classificado como um Número Irracional:</strong></p>
        <p>a) &radic;400<br>b) &radic;144<br>c) &radic;196<br>d) &radic;250</p>
        <br>
        <p><strong>05. (EF09MA01) Escreva com suas palavras qual a diferença prática entre o comportamento de um número racional (como uma dízima periódica) e um número irracional na reta numérica real:</strong></p>
        <div class="linha-resposta"></div>
        <div class="linha-resposta"></div>
        <div class="linha-resposta"></div>
        <div class="linha-resposta"></div>
        """
    else:
        return f"""
        <h4><i class="fa-solid fa-file-invoice text-primary me-2"></i> Estrutura de Documentação Pedagógica</h4>
        <p><strong>Módulo operacional ativo:</strong> {tipo_modulo}</p>
        <p><strong>Escopo Temático:</strong> {tema if tema else 'Objeto de Conhecimento Geral'} associado à disciplina de {disciplina}.</p>
        <hr>
        <h5>Diretrizes e Objetivos de Aprendizagem Base:</h5>
        <ul>
            <li>Desenvolver as competências cognitivas previstas para o {ano}.</li>
            <li>Estimular o raciocínio lógico-matemático e a interpretação de texto.</li>
            <li>Garantir o alinhamento de acordo com as diretrizes da BNCC.</li>
        </ul>
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
        # Configuração do modelo expandindo o limite máximo de tokens de saída
        configuracao = genai.types.GenerationConfig(
            max_output_tokens=8192,  # Permite textos extremamente longos sem cortes
            temperature=0.7
        )
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Atue como um Especialista em Design Pedagógico e Elaboração de Avaliações Escolares Oficiais.
        Sua tarefa é gerar o conteúdo COMPLETO do início ao fim em HTML limpo para o módulo '{tipo_modulo}'.
        Não pare a geração na metade e não resuma o conteúdo. Escreva todas as partes solicitadas.
        
        DADOS DO ESCOPO DO DOCUMENTO:
        - Componente Curricular / Disciplina: {disciplina}
        - Ano Escolar / Série: {ano}
        - Objeto de Estudo / Tema central: {tema}
        - Código de Diretriz BNCC base: {bncc}
        - Nível de Rigor Cognitivo: {nivel}
        """

        if tipo_modulo == 'Gerador de Provas':
            prompt += f"""
            - Quantidade Exata de Questões solicitadas: DEVE GERAR EXATAMENTE {qtd_questoes} QUESTÕES.
            - Formato das Questões: {tipo_prova}

            DIRETRIZES OBRIGATÓRIAS DE FORMATAÇÃO (ESTRUTURA IDENTITÁRIA DO MODELO REAL):
            1. Use numeração sequencial com dois dígitos seguidos de ponto para cada questão (Exemplo: 01., 02., até chegar na questão {qtd_questoes}).
            2. Imediatamente após a numeração, inclua a diretriz BNCC entre parênteses. Use o código fornecido ({bncc}) ou deduza um correto e real caso esteja vazio. Exemplo: '01. (EF09MA02) '.
            3. Todo o texto do enunciado da questão DEVE estar estritamente dentro da tag HTML <strong>...</strong>.
            4. Para questões Objetivas ou Mistas, posicione as alternativas de 'a)' até 'd)' alinhadas verticalmente logo abaixo do enunciado, separadas por quebras de linha (<br>).
            5. Para questões Subjetivas, adicione de 3 a 4 linhas de resposta utilizando: <div class="linha-resposta"></div>.
            6. IMPORTANTE: Retorne diretamente o código HTML limpo de todas as {qtd_questoes} questões exigidas, sem markdown ou delimitadores ```html.
            """
        else:
            prompt += f"""
            Gere um documento robusto, detalhado e completo de {tipo_modulo} sobre o tema {tema}.
            Estruture utilizando títulos H4, listas organizadas (UL/LI) e parágrafos bem definidos. 
            Não abrevie as seções. Retorne em HTML limpo sem delimitadores de markdown.
            """

        response = model.generate_content(prompt, generation_config=configuracao)
        conteudo_limpo = response.text.replace("```html", "").replace("```", "").strip()
        return conteudo_limpo

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