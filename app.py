import os
from flask import Flask, render_template, request, redirect, url_for
from ai_service import gerar_conteudo_educacional

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_mestra_professor_ia_2026")

# Dicionário de configuração dos módulos Premium que alimenta o painel visual
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
    # Redireciona para a função dashboard com o módulo plano ativo
    return redirect(url_for('dashboard', form_type='plano'))

# Aceita tanto o acesso por /gerador quanto por /dashboard para não quebrar links antigos
@app.route('/gerador', methods=['GET', 'POST'])
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard(): # Mudamos o nome da função de 'gerador' para 'dashboard' para corrigir o HTML
    # Captura qual aba o usuário clicou
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
        # Captura os dados enviados pelo formulário
        tema = request.form.get('tema', '').strip()
        disciplina = request.form.get('disciplina', '').strip()
        ano = request.form.get('ano', '').strip()
        bncc = request.form.get('bncc', '').strip()
        
        if tema:
            # Envia para a inteligência artificial
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
        name="Samuel Araújo Sousa",
        school="Fábrica de Software"
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)