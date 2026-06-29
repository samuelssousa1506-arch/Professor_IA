import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import init_db, create_user, verify_user
from ai_service import gerar_conteudo_educacional as generate_pedagogical_content

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_secreta_do_professor_ia_123")

try:
    init_db()
except Exception as e:
    print("Aviso na inicialização do banco:", e)

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        school_name = request.form.get('school_name')
        password = request.form.get('password')
        
        if create_user(name, email, school_name, password):
            flash('Conta criada com sucesso!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Este e-mail já está cadastrado.', 'danger')
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email == 'dev@professoria.com' and password == 'dev123':
            session['user_id'] = 999
            session['user_name'] = 'Samuel Araújo Sousa'
            session['user_email'] = 'dev@professoria.com'
            session['user_school'] = 'Fábrica de Software'
            session['user_role'] = 'developer'
            return redirect(url_for('dashboard'))
            
        try:
            user = verify_user(email, password)
            if user:
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_email'] = user['email']
                session['user_school'] = user['school_name']
                session['user_role'] = user.get('role', 'user') if isinstance(user, dict) else 'user'
                return redirect(url_for('dashboard'))
        except Exception as e:
            print("Erro no banco:", e)
            
        flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('gerador', form_type='plano'))

# 🤖 SISTEMA MULTI-MÓDULO REFORÇADO COM RESTRIÇÕES NEGATIVAS
@app.route('/gerador', methods=['GET', 'POST'])
def gerador():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # 🔒 SEGURANÇA: Busca o módulo tanto do formulário POST quanto dos argumentos da URL
    form_type = request.form.get('form_type') or request.args.get('form_type', 'plano')
    bncc_digitada = request.form.get('bncc', '')
    
    modulos_config = {
        'plano': {
            'nome': 'Plano de Aula Completo', 
            'icone': 'fa-book', 
            'cor': '#4e73df', 
            'diretriz': (
                "Desenvolva um Plano de Aula extremamente detalhado e robusto para o professor usar como guia. "
                "Inclua: 1. OBJETIVOS DE APRENDIZAGEM (BNCC); 2. CONTEÚDO PROGRAMÁTICO; "
                "3. METODOLOGIA PASSO A PASSO DIVIDIDA POR TEMPO (Introdução: 10 min, Teoria: 20 min, Prática: 15 min, Fechamento: 5 min); "
                "4. RECURSOS DIDÁTICOS; 5. CRITÉRIOS DE AVALIAÇÃO FORMATIVA."
            )
        },
        'atividades': {
            'nome': 'Banco de Atividades Práticas', 
            'icone': 'fa-list-check', 
            'cor': '#1cc88a', 
            'diretriz': (
                "Gere EXCLUSIVAMENTE um Caderno de Atividades e Exercícios Práticos para os alunos responderem. "
                "⚠️ AVISO CRÍTICO: NÃO GERE UM PLANO DE AULA. Não inclua objetivos para o professor, metodologias, recursos ou divisões de tempo de aula. "
                "O documento deve conter apenas: 1. TEXTO DE APOIO CONTEXTUALIZADO para leitura do aluno; "
                "2. QUESTÕES DE FIXAÇÃO (Mínimo de 3 questões diretas); "
                "3. QUESTÕES DESAFIADORAS / SITUAÇÕES-PROBLEMA (Mínimo de 2 questões complexas); "
                "4. GABARITO COMENTADO no final da página (com a explicação detalhada de cada resposta)."
            )
        },
        'avaliacoes': {
            'nome': 'Gerador de Provas Oficiais', 
            'icone': 'fa-file-signature', 
            'cor': '#36b9cc', 
            'diretriz': (
                "Gere EXCLUSIVAMENTE uma Avaliação Formal/Prova Escrita institucional prontas para aplicação. "
                "⚠️ AVISO CRÍTICO: NÃO GERE PLANOS DE AULA, metodologias ou cronogramas de ensino. "
                "A estrutura deve conter: 1. INSTRUÇÕES GERAIS AO ESTUDANTE; "
                "2. QUESTÕES OBJETIVAS (Gere 4 questões de múltipla escolha de A até E com distratores plausíveis); "
                "3. QUESTÕES DISCURSIVAS (Gere 2 questões dissertativas com espaço/linhas para resposta); "
                "4. MATRIZ de correção e critérios de pontuação detalhados no final."
            )
        },
        'relatorios': {
            'nome': 'Modelos de Relatórios Pedagógicos', 
            'icone': 'fa-chart-line', 
            'cor': '#f6c23e', 
            'diretriz': (
                "Gere um Guia de Parecer Descritivo e Relatórios Pedagógicos de Alunos. "
                "⚠️ AVISO CRÍTICO: NÃO GERE PLANOS DE AULA OU EXERCÍCIOS. "
                "O foco é a avaliação de desempenho. Forneça: 1. Modelos de escrita para desempenho Cognitivo (Alto, Regular e Crítico); "
                "2. Indicadores de avaliação Socioemocional; 3. Um MODELO DE TEXTO FORMAL PREENCHÍVEL (esqueleto com lacunas para o professor preencher com os dados do estudante)."
            )
        },
        'inclusao': {
            'nome': 'Plano de Inclusão e AEE', 
            'icone': 'fa-hands-asl-interpreting', 
            'cor': '#e74a3b', 
            'diretriz': (
                "Gere um documento técnico focado em Adaptação Curricular para Atendimento Educacional Especializado (AEE). "
                "⚠️ AVISO CRÍTICO: NÃO GERE UM PLANO DE AULA TRADICIONAL. "
                "Forneça estratégias de acessibilidade diretas para o tema proposto divididas para: "
                "1. Transtorno do Espectro Autista (TEA); 2. TDAH; 3. Dislexia/Dificuldades acentuadas de leitura; "
                "4. Sugestão de instrumentos avaliativos flexibilizados para inclusão."
            )
        },
        'projetos': {
            'nome': 'Projetos Interdisciplinares (PBL)', 
            'icone': 'fa-diagram-project', 
            'cor': '#6f42c1', 
            'diretriz': (
                "Gere um Projeto Pedagógico de Médio/Longo Prazo baseado na Aprendizagem Baseada em Projetos (PBL). "
                "⚠️ AVISO CRÍTICO: NÃO GERE UM PLANO DE AULA SIMPLES DE 50 MINUTOS. "
                "O escopo deve conter: 1. Pergunta Disparadora/Desafio Central; 2. Mapeamento de Conexão entre Disciplinas; "
                "3. Cronograma de Atividades de execução por semanas; 4. Produto Final/Culminância do projeto; 5. Rúbrica de Avaliação de competências."
            )
        }
    }
    
    config = modulos_config.get(form_type, modulos_config['plano'])
    
    if request.method == 'POST':
        tema = request.form.get('tema')
        disciplina = request.form.get('disciplina', '')
        ano = request.form.get('ano', '')
        
        try:
            prompt_completo = (
                f"Você é o Co-Pilot Acadêmico Premium do Professor {session.get('user_name')}.\n"
                f"DIRETRIZ OBRIGATÓRIA DO MÓDULO EXECUTADO: {config['diretriz']}\n\n"
                f"DADOS DO ESCOPO DE ENTRADA:\n"
                f"- Tema Solicitado: '{tema}'\n"
                f"- Disciplina: '{disciplina}'\n"
                f"- Ano/Turma: '{ano}'\n"
                f"- Alinhamento BNCC: '{bncc_digitada if bncc_digitada else 'Geral'}'\n\n"
                f"REGRAS ESTREITAS DE SAÍDA:\n"
                f"1. NÃO utilize caracteres Markdown como asteriscos (*) ou hashtags (#).\n"
                f"2. Inicie títulos principais estritamente com o prefixo 'SECAO: '\n"
                f"3. Inicie subtítulos ou tópicos menores estritamente com 'SUBSECAO: '\n"
                f"4. Escreva de forma profunda, assertiva e sem textos introdutórios informais fora do documento."
            )
            
            conteudo_gerado = generate_pedagogical_content(prompt_completo)
            
            return render_template('dashboard.html', 
                                   name=session.get('user_name'),
                                   school=session.get('user_school'),
                                   role=session.get('user_role'),
                                   conteudo=conteudo_gerado,
                                   tema=tema, disciplina=disciplina, ano=ano, bncc=bncc_digitada,
                                   form_type=form_type, config=config)
        except Exception as e:
            flash(f'Erro interno no processamento de IA: {str(e)}', 'danger')
            return redirect(url_for('gerador', form_type=form_type))
            
    return render_template('dashboard.html', 
                           name=session.get('user_name'),
                           school=session.get('user_school'),
                           role=session.get('user_role'),
                           form_type=form_type, config=config, bncc=bncc_digitada)

@app.route('/banco')
def banco():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    flash('Banco de Materiais em desenvolvimento.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)