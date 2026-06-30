import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import init_db, create_user, verify_user
from ai_service import gerar_conteudo_educacional as generate_pedagogical_content

# 🔒 Carrega as variáveis de ambiente seguras (essencial para produção)
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_secreta_do_professor_ia_123")

# Inicialização segura e blindada do banco de dados
try:
    init_db()
except Exception as e:
    print("Aviso na inicialização automática do banco:", e)

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
            flash('Conta criada com sucesso! Faça o seu login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Este e-mail já está cadastrado.', 'danger')
            
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 🔐 CHAVE MESTRA DESENVOLVEDOR: SAMUEL DEV MASTER
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
                session['user_id'] = user['id'] if isinstance(user, dict) else user[0]
                session['user_name'] = user['name'] if isinstance(user, dict) else user[1]
                session['user_email'] = user['email'] if isinstance(user, dict) else user[2]
                session['user_school'] = user['school_name'] if isinstance(user, dict) else user[3]
                
                # 🛡️ TRATAMENTO SEGURO CONTRA BUG DE INDEXERROR DO DICIONÁRIO
                try:
                    if isinstance(user, dict):
                        session['user_role'] = user.get('role', 'user')
                    else:
                        session['user_role'] = user[4] if len(user) > 4 else 'user'
                except Exception:
                    session['user_role'] = 'user'
                    
                return redirect(url_for('dashboard'))
        except Exception as e:
            print("Erro na consulta do banco de dados:", e)
            
        flash('Usuário ou senha incorretos.', 'danger')
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Por favor, faça login primeiro.', 'warning')
        return redirect(url_for('login'))
        
    return redirect(url_for('gerador', form_type='plano'))

# 🤖 MOTOR INTELIGENTE MULTI-MÓDULO COM MATRIZ DE DIRETRIZES
@app.route('/gerador', methods=['GET', 'POST'])
def gerador():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # 🔒 BLINDAGEM DE ROTA: Captura o tipo de módulo via formulário oculto ou argumento de link
    form_type = request.form.get('form_type') or request.args.get('form_type', 'plano')
    bncc_digitada = request.form.get('bncc', '')
    
    modulos_config = {
        'plano': {
            'nome': 'Plano de Aula Completo', 
            'icone': 'fa-book', 
            'cor': '#4e73df', 
            'diretriz': (
                "Desenvolva um Plano de Aula extremamente detalhado e robusto para o professor usar como guia. "
                "Você deve incluir impreterivelmente: "
                "1. OBJETIVOS DE APRENDIZAGEM (Gerais e específicos alinhados à BNCC). "
                "2. CONTEÚDO PROGRAMÁTICO (Subtópicos detalhados da aula). "
                "3. METODOLOGIA PASSO A PASSO DIVIDIDA POR TEMPO (Acolhimento/Introdução: 10 min; Desenvolvimento/Teoria: 20 min; Prática Guiada: 15 min; Conclusão/Fechamento: 5 min). Explique o que o professor fala e faz em cada etapa. "
                "4. RECURSOS DIDÁTICOS (Materiais necessários). "
                "5. ESTRATÉGIA DE AVALIAÇÃO (Como verificar se aprenderam de forma formativa)."
            )
        },
        'bimestral': {
            'nome': 'Planejamento Bimestral SEMED', 
            'icone': 'fa-calendar-check', 
            'cor': '#fd7e14', 
            'diretriz': (
                "Gere um Planejamento de Curso Bimestral corporativo completo, baseado rigorosamente no modelo padrão institucional da Secretaria Municipal de Educação (SEMED) de Presidente Dutra - MA. "
                "⚠️ AVISO CRÍTICO: NÃO GERE UM PLANO DE AULA INDIVIDUAL OU DIÁRIO. O escopo deve abranger o bimestre inteiro e conter obrigatoriamente as seguintes partes organizadas:\n"
                "1. COMPETÊNCIAS GERAIS DA EDUCAÇÃO BÁSICA: Enumere de forma adaptada as macro-competências da BNCC focadas nas necessidades do bimestre.\n"
                "2. COMPETÊNCIAS ESPECÍFICAS DO COMPONENTE: Detalhe as competências exclusivas para a disciplina e ano informados.\n"
                "3. UNIDADES TEMÁTICAS: Mapeie as grandes áreas organizacionais da BNCC aplicadas ao período.\n"
                "4. OBJETOS DE CONHECIMENTO: Apresente os conteúdos e conceitos detalhados explicitando sua respectiva unidade organizacional no formato 'UNIDADE: Nome da Unidade / Ano'.\n"
                "5. HABILIDADES: Indique os códigos alfanuméricos oficiais da BNCC (ex: EF06MA04, EF06MA05) seguidos rigorosamente de suas descrições completas e desdobramentos regionais.\n"
                "6. SUGESTÕES METODOLÓGICAS: Proponha estratégias de ensino de médio prazo, abordagens práticas contextualizadas, uso de tecnologias didáticas ou materiais concretos aplicados ao cronograma do bimestre.\n"
                "7. AVALIAÇÃO: Detalhe os critérios e instrumentos de nota (avaliação bimestral, participação, trabalhos, devolução de cadernos de exercícios).\n"
                "8. RECURSOS: Enumere a infraestrutura material necessária (jogos, materiais impressos, cartazes, mídias digitais).\n"
                "9. REFERÊNCIAS: Inclua obrigatoriamente referências normativas locais, com destaque para o 'Documento Curricular do Território Maranhense (SEDUC-MA)' e livros didáticos contemporâneos da área.\n"
                "10. OBSERVAÇÕES PERTINENTES: Espaço para indicação de sequências didáticas especiais, projetos interdisciplinares (ex: Clubes de Letramento) ou complementos curriculares específicos."
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
                "2. QUESTÕES OBJETIVAS (Gere 4 questões de múltipla escolha. Cada questão DEVE ter 5 alternativas de A até E. Certifique-se de que os distratores sejam plausíveis); "
                "3. QUESTÕES DISCURSIVAS (Gere 2 questões dissertativas com espaço/linhas para resposta); "
                "4. MATRIZ de correção, critérios de pontuação detalhados e expectativas de resposta no final."
            )
        },
        'relatorios': {
            'nome': 'Modelos de Relatórios Pedagógicos', 
            'icone': 'fa-chart-line', 
            'cor': '#f6c23e', 
            'diretriz': (
                "Gere um Guia de Parecer Descritivo e Relatórios Pedagógicos de Alunos. "
                "⚠️ AVISO CRÍTICO: NÃO GERE PLANOS DE AULA OU EXERCÍCIOS PARA OS ALUNOS. "
                "O foco é a avaliação de desempenho escolar. Forneça: 1. Modelos de escrita para desempenho Cognitivo (Alto, Regular e Crítico); "
                "2. Indicadores de avaliação Socioemocional; 3. Um MODELO DE TEXTO FORMAL PREENCHÍVEL (esqueleto com lacunas/parênteses para o professor preencher manualmente com os dados de cada estudante); 4. Sugestões de plano de intervenção pedagógica."
            )
        },
        'inclusao': {
            'nome': 'Plano de Inclusão e AEE', 
            'icone': 'fa-hands-asl-interpreting', 
            'cor': '#e74a3b', 
            'diretriz': (
                "Gere um documento técnico focado em Adaptação Curricular para Atendimento Educacional Especializado (AEE). "
                "⚠️ AVISO CRÍTICO: NÃO GERE UM PLANO DE AULA TRADICIONAL. "
                "Forneça modificações estruturais completas e estratégias de acessibilidade diretas para o tema proposto divididas para: "
                "1. Transtorno do Espectro Autista (TEA) (adaptações visuais e estruturação de comandos); 2. TDAH (estratégias de foco e dinâmicas cinestésicas); 3. Dislexia/Dificuldades acentuadas de leitura; "
                "4. Sugestão de instrumentos avaliativos flexibilizados para inclusão escolar."
            )
        },
        'projetos': {
            'nome': 'Projetos Interdisciplinares (PBL)', 
            'icone': 'fa-diagram-project', 
            'cor': '#6f42c1', 
            'diretriz': (
                "Gere um Projeto Pedagógico de Médio/Longo Prazo baseado na Aprendizagem Baseada em Projetos (PBL). "
                "⚠️ AVISO CRÍTICO: NÃO GERE UM PLANO DE AULA SIMPLES DE 50 MINUTOS. "
                "O escopo deve conter: 1. Pergunta Disparadora / Desafio Central motivador; 2. Mapeamento de Conexão entre Disciplinas (Interdisciplinaridade); "
                "3. Cronograma de Atividades de execução sugerido por semanas; 4. Produto Final / Culminância do projeto para a comunidade escolar; 5. Rúbrica de Avaliação de competências holística."
            )
        }
    }
    
    config = modulos_config.get(form_type, modulos_config['plano'])
    
    if request.method == 'POST':
        tema = request.form.get('tema')
        disciplina = request.form.get('disciplina', '')
        ano = request.form.get('ano', '')
        
        try:
            # Engenharia de super-prompt estrutural sem conflitos de contexto
            prompt_completo = (
                f"Você é o Co-Pilot Acadêmico Premium do Professor {session.get('user_name')}.\n"
                f"DIRETRIZ OBRIGATÓRIA DO MÓDULO EXECUTADO: {config['diretriz']}\n\n"
                f"DADOS DO ESCOPO DE ENTRADA:\n"
                f"- Tema Solicitado: '{tema}'\n"
                f"- Disciplina: '{disciplina}'\n"
                f"- Ano/Turma: '{ano}'\n"
                f"- Alinhamento BNCC: '{bncc_digitada if bncc_digitada else 'Geral'}'\n\n"
                f"REGRAS ESTREITAS DE SAÍDA:\n"
                f"1. NÃO utilize caracteres Markdown como asteriscos (*) ou hashtags (#) em momento algum.\n"
                f"2. Inicie títulos principais estritamente com o prefixo 'SECAO: '\n"
                f"3. Inicie subtítulos ou tópicos menores estritamente com 'SUBSECAO: '\n"
                f"4. Escreva de forma profunda, assertiva, longa e sem textos introdutórios informais fora do corpo do documento."
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
    flash('O Banco de Materiais está sendo preparado e estará disponível em breve!', 'info')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Configuração inteligente: lê a porta dinâmica injetada pelo Render ou roda em 5000 localmente
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)