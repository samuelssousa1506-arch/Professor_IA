import os
import re
import sqlite3
import random
import requests
import markdown as md
from io import BytesIO
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from htmldocx import HtmlToDocx
from xhtml2pdf import pisa
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_mestra_professor_ia_2026")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 1. MAPEAMENTO DA CHAVE GEMINI
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# Dicionário de módulos unificado
MODULOS = {
    'plano': {'nome': 'Plano de Aula', 'icone': 'fa-book'},
    'bimestral': {'nome': 'Planejamento Bimestral', 'icone': 'fa-calendar-check'},
    'atividades': {'nome': 'Banco de Atividades', 'icone': 'fa-list-check'},
    'avaliacoes': {'nome': 'Gerador de Provas', 'icone': 'fa-file-signature'},
    'simulados': {'nome': 'Simulados', 'icone': 'fa-clipboard-question'},
    'duvidas': {'nome': 'Tira-Dúvidas com IA', 'icone': 'fa-circle-question'},
    'relatorios': {'nome': 'Relatórios Pedagógicos', 'icone': 'fa-chart-line'},
    'inclusao': {'nome': 'Plano de Inclusão / AEE', 'icone': 'fa-hands-asl-interpreting'},
    'projetos': {'nome': 'Projetos Interdisciplinares', 'icone': 'fa-diagram-project'},
    'alfabetizacao': {'nome': 'Alfabetização e Reforço de Leitura', 'icone': 'fa-spell-check'}
}

TIPOS_SIMULADO = [
    "Simulado Bimestral / Revisão de Conteúdo",
    "Simulado tipo ENEM",
    "Simulado tipo Vestibular",
    "Simulado SAEB / Prova Brasil",
    "Simulado de Concurso Público",
    "Simulado Geral / Diagnóstico"
]

NIVEIS_LEITURA = [
    "Pré-silábico (não reconhece letras/sons)",
    "Silábico sem valor sonoro (junta símbolos sem som correspondente)",
    "Silábico com valor sonoro (associa algumas letras ao som)",
    "Silábico-alfabético (mistura sílabas e letras corretamente)",
    "Alfabético com dificuldades (lê, mas troca/omite letras, lê devagar)",
    "Alfabético fluente com dificuldade de interpretação (lê bem, mas não compreende)"
]

FOCOS_ALFABETIZACAO = [
    "Consciência Fonológica (rimas, sons, sílabas)",
    "Reconhecimento de Letras (alfabeto, maiúsculas/minúsculas)",
    "Formação de Sílabas",
    "Leitura de Palavras",
    "Leitura de Frases e Textos Curtos",
    "Fluência Leitora (velocidade e ritmo)",
    "Compreensão Leitora (interpretação)",
    "Escrita Espontânea",
    "Ortografia Básica",
    "Gosto pela Leitura / Motivação"
]

TIPOS_ATIVIDADE = [
    "Interpretação de texto", "Questões objetivas", "Questões subjetivas", "Produção textual",
    "Atividade de leitura (alfabetização)", "Complete as lacunas", "Ligue as colunas",
    "Verdadeiro ou falso", "Caça-palavras", "Cruzadinha", "Sequência lógica",
    "Ordenação de frases", "Escrita de palavras", "Formação de frases", "Problemas matemáticos",
    "Atividade ilustrada", "Recorte e cole", "Pintura educativa", "Pesquisa", "Debate em sala",
    "Trabalho em grupo", "Atividade prática", "Revisão de conteúdo", "Exercícios para reforço"
]

TIPOS_PROJETO = [
    "Feira de Ciências", "Feira Cultural", "Feira Literária", "Mostra Pedagógica", "Visita Técnica",
    "Aula de Campo", "Projeto Interdisciplinar", "Projeto de Leitura", "Projeto de Escrita",
    "Projeto Ambiental", "Projeto de Sustentabilidade", "Projeto de História Local",
    "Projeto de Cultura Popular", "Projeto de Consciência Negra", "Projeto de Educação Financeira",
    "Projeto de Saúde", "Projeto Esportivo", "Gincana Educativa", "Culminância",
    "Exposição de Trabalhos", "Oficina", "Seminário", "Palestra", "Teatro", "Musical",
    "Produção de Podcast", "Produção de Vídeo", "Robótica Educacional", "Clube de Ciências",
    "Clube de Leitura", "Horta Escolar", "Outro"
]

# =====================================================================
# TEXTO OFICIAL FIXO — COMPETÊNCIAS GERAIS DA EDUCAÇÃO BÁSICA (BNCC, 2018)
# Fixado no backend (não gerado pela IA) para garantir fidelidade 100% ao
# texto oficial do MEC em todo Planejamento Bimestral, independente do tema.
# =====================================================================
COMPETENCIAS_GERAIS_BNCC = [
    "Valorizar e utilizar os conhecimentos historicamente construídos sobre o mundo físico, social, cultural e digital para entender e explicar a realidade, continuar aprendendo e colaborar para a construção de uma sociedade justa, democrática e inclusiva.",
    "Exercitar a curiosidade intelectual e recorrer à abordagem própria das ciências, incluindo a investigação, a reflexão, a análise crítica, a imaginação e a criatividade, para investigar causas, elaborar e testar hipóteses, formular e resolver problemas e criar soluções (inclusive tecnológicas) com base nos conhecimentos das diferentes áreas.",
    "Valorizar e fruir as diversas manifestações artísticas e culturais, das locais às mundiais, e também participar de práticas diversificadas da produção artístico-cultural.",
    "Utilizar diferentes linguagens – verbal (oral ou visual-motora, como Libras, e escrita), corporal, visual, sonora e digital –, bem como conhecimentos das linguagens artística, matemática e científica, para se expressar e partilhar informações, experiências, ideias e sentimentos em diferentes contextos e produzir sentidos que levem ao entendimento mútuo.",
    "Compreender, utilizar e criar tecnologias digitais de informação e comunicação de forma crítica, significativa, reflexiva e ética nas diversas práticas sociais (incluindo as escolares) para se comunicar, acessar e disseminar informações, produzir conhecimentos, resolver problemas e exercer protagonismo e autoria na vida pessoal e coletiva.",
    "Valorizar a diversidade de saberes e vivências culturais e apropriar-se de conhecimentos e experiências que lhe possibilitem entender as relações próprias do mundo do trabalho e fazer escolhas alinhadas ao exercício da cidadania e ao seu projeto de vida, com liberdade, autonomia, consciência crítica e responsabilidade.",
    "Argumentar com base em fatos, dados e informações confiáveis, para formular, negociar e defender ideias, pontos de vista e decisões comuns que respeitem e promovam os direitos humanos, a consciência socioambiental e o consumo responsável em âmbito local, regional e global, com posicionamento ético em relação ao cuidado de si mesmo, dos outros e do planeta.",
    "Conhecer-se, apreciar-se e cuidar de sua saúde física e emocional, compreendendo-se na diversidade humana e reconhecendo suas emoções e as dos outros, com autocrítica e capacidade para lidar com elas.",
    "Exercitar a empatia, o diálogo, a resolução de conflitos e a cooperação, fazendo-se respeitar e promovendo o respeito ao outro e aos direitos humanos, com acolhimento e valorização da diversidade de indivíduos e de grupos sociais, seus saberes, identidades, culturas e potencialidades, sem preconceitos de qualquer natureza.",
    "Agir pessoal e coletivamente com autonomia, responsabilidade, flexibilidade, resiliência e determinação, tomando decisões com base em princípios éticos, democráticos, inclusivos, sustentáveis e solidários.",
]

def montar_prova_duas_colunas(html_questoes):
    """
    Recebe o HTML das questões (cada uma em <div class="questao-item">) e o
    gabarito (em <div class="gabarito-prova">), e monta um bloco de texto em
    2 colunas reais (CSS column-count), fonte Arial 12.

    IMPORTANTE: usamos column-count (fluxo de texto tipo "jornal") em vez de
    uma tabela HTML de 2 colunas fixas. Uma tabela força uma divisão rígida
    de questões entre as colunas; quando uma questão é maior que as outras,
    o navegador precisa manter a "linha" da tabela inteira, criando vãos
    enormes na impressão. Com column-count, o texto flui naturalmente e
    quebra de página corretamente, sem espaços em branco indevidos.
    """
    soup = BeautifulSoup(html_questoes, 'html.parser')
    itens = soup.find_all('div', class_='questao-item')
    gabarito_tag = soup.find('div', class_='gabarito-prova')
    gabarito_html = str(gabarito_tag) if gabarito_tag else ''

    fonte_estilo = 'font-family: Arial, Helvetica, sans-serif; font-size: 12pt; line-height: 1.4;'

    if not itens:
        # Rede de segurança: a IA não usou as divs esperadas — devolve sem split, mas já com a fonte correta.
        conteudo_sem_gabarito = html_questoes
        if gabarito_tag:
            conteudo_sem_gabarito = conteudo_sem_gabarito.replace(str(gabarito_tag), '')
        return f'<div style="{fonte_estilo}">{conteudo_sem_gabarito}</div>{gabarito_html}'

    questoes_html = "".join(str(i) for i in itens)

    bloco_colunas = f"""
    <div class="prova-colunas" style="column-count:2; -webkit-column-count:2; column-gap:30px; -webkit-column-gap:30px; column-rule:1px solid #999; column-fill:auto; {fonte_estilo}">
        {questoes_html}
    </div>
    """
    return bloco_colunas + gabarito_html


def montar_html_competencias_gerais():
    ordinais = ["1ª", "2ª", "3ª", "4ª", "5ª", "6ª", "7ª", "8ª", "9ª", "10ª"]
    itens = "".join(
        f"<p><strong>{ordinais[i]}</strong> - {texto}</p>"
        for i, texto in enumerate(COMPETENCIAS_GERAIS_BNCC)
    )
    return f'<h5 class="doc-secao-titulo">Competências Gerais da Educação Básica</h5><div class="doc-secao-corpo">{itens}</div>'

def sanitizar_saida_html(texto):
    """
    Rede de segurança: mesmo instruindo o Gemini a responder em HTML puro,
    modelos de linguagem eventualmente retornam sintaxe Markdown (###, **, *).
    Esta função detecta esse padrão e converte para HTML real antes de renderizar.
    """
    texto = texto.strip()

    # Heurística: se encontrarmos marcadores clássicos de Markdown, convertemos.
    parece_markdown = bool(re.search(r'(^|\n)#{2,6}\s|\*\*[^*]+\*\*|(^|\n)\*\s|(^|\n)-\s', texto))

    if parece_markdown:
        texto = md.markdown(texto, extensions=['tables', 'nl2br', 'sane_lists'])

    return texto.strip()

def obter_fallback_pedagogico(tipo_modulo, tema, erro_adicional=""):
    return f"""
    <h4><i class="fa-solid fa-graduation-cap text-primary me-2"></i> {tipo_modulo} (Modo de Segurança)</h4>
    <p>O sistema não conseguiu conectar ao Gemini em tempo real. Certifique-se de que configurou a variável <strong>GEMINI_API_KEY</strong> corretamente no painel do Render.</p>
    <p><strong>Tema enviado:</strong> {tema}</p>
    {f'<p class="text-danger small"><strong>Detalhes do Erro:</strong> {erro_adicional}</p>' if erro_adicional else ''}
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
    nome_professor = kwargs.get('nome_professor', 'Professor(a)')
    nome_escola = kwargs.get('nome_escola', 'Instituição de Ensino')

    # Campos específicos do Planejamento Bimestral (formato oficial SEMED)
    numero_plano = kwargs.get('numero_plano', '')
    bimestre = kwargs.get('bimestre', '1º BIM')
    data_inicio = kwargs.get('data_inicio', '')
    data_fim = kwargs.get('data_fim', '')
    turma = kwargs.get('turma', '')
    turno = kwargs.get('turno', '')
    modalidade = kwargs.get('modalidade', 'Presencial')
    ano_letivo = kwargs.get('ano_letivo', '')
    inep = kwargs.get('inep', '')
    endereco_escola = kwargs.get('endereco_escola', '')
    cidade_escola = kwargs.get('cidade_escola', '')
    estado_escola = kwargs.get('estado_escola', 'MA')
    zona_escola = kwargs.get('zona_escola', '')
    telefone_escola = kwargs.get('telefone_escola', '')
    email_escola = kwargs.get('email_escola', '')
    observacoes = kwargs.get('observacoes', '')

    if not GEMINI_API_KEY:
        return obter_fallback_pedagogico(tipo_modulo, tema, "A variável GEMINI_API_KEY está ausente no painel do Render."), ''

    # -----------------------------------------------------------------
    # EXTRAÇÃO CIRÚRGICA DA CHAVE COM REGEX (Ignora qualquer formatação de link)
    # -----------------------------------------------------------------
    # O padrão procura pela sequência que começa com AIza ou AQ e pega apenas caracteres válidos de chave
    match = re.search(r'(AIzaSy[A-Za-z0-9_-]+|AQ\.[A-Za-z0-9_-]+)', GEMINI_API_KEY)
    
    if match:
        chave_limpa = match.group(1).strip()
    else:
        # Fallback caso a regex não isole (remove manualmente caracteres de link comuns)
        chave_limpa = GEMINI_API_KEY.replace("[", "").replace("]", "").replace("'", "").replace('"', '')
        if "key=" in chave_limpa:
            chave_limpa = chave_limpa.split("key=")[-1]
        if ")" in chave_limpa:
            chave_limpa = chave_limpa.split(")")[-1]
        chave_limpa = chave_limpa.strip()
    # -----------------------------------------------------------------

    # 2. CONSTRUÇÃO DO PROMPT PEDAGÓGICO
    regras_formato = """
        REGRAS OBRIGATÓRIAS DE FORMATAÇÃO DA SAÍDA:
        - Responda ESTRITAMENTE em HTML puro e semântico (tags: h4, h5, p, strong, em, ul, ol, li, table, thead, tbody, tr, th, td, div).
        - NUNCA utilize sintaxe Markdown (proibido: #, ##, ###, **texto**, *item*, -, ```). Se precisar de negrito use <strong>, se precisar de título use <h4>/<h5>, se precisar de lista use <ul><li>.
        - NUNCA inclua delimitadores de bloco de código como ```html ou ```.
        - Use <table class="tabela-bncc"> quando fizer sentido organizar habilidades BNCC, cronogramas ou critérios de avaliação em formato tabular.
    """
    if tipo_modulo == 'Tira-Dúvidas com IA':
        prompt = f"""
        Você é um Consultor Jurídico-Pedagógico especialista e expert em Legislação Educacional Brasileira.
        Responda com total precisão técnica fundamentando-se OBRIGATORIAMENTE em: BNCC (Base Nacional Comum Curricular), LDB (Lei nº 9.394/96), DCTMA (Documento Curricular do Território Maranhense) e, quando pertinente, na Seção da Educação da Constituição Federal.
        Sempre que citar um desses documentos, indique de forma explícita o artigo, competência ou eixo correspondente.
        Dúvida ou Consulta do Professor: "{tema}"
        {regras_formato}
        """
    elif tipo_modulo == 'Planejamento Bimestral':
        numero_final = numero_plano.strip() or str(random.randint(10000, 99999))
        ano_letivo_final = ano_letivo.strip() or str(datetime.now().year)
        criado_em = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        turma_completa = f"{ano} | ({turma}) | {turno}".upper() if turma or turno else ano.upper()
        periodo_execucao = f"{data_inicio} a {data_fim}" if data_inicio and data_fim else "[preencher período de execução]"

        prompt = f"""
        Atue como um Especialista em Planejamento Pedagógico Escolar, com domínio profundo da BNCC (Base Nacional Comum Curricular), da LDB (Lei nº 9.394/96) e do DCTMA (Documento Curricular do Território Maranhense).
        Gere um PLANEJAMENTO BIMESTRAL completo e oficial, seguindo EXATAMENTE a estrutura, ordem de seções e nível de detalhamento abaixo — este é o modelo oficial usado pela Secretaria Municipal de Educação, e deve ser reproduzido fielmente.

        {regras_formato}
        REGRA ADICIONAL CRÍTICA: Não gere você mesmo a seção "Competências Gerais da Educação Básica". No lugar exato indicado abaixo, insira apenas o marcador literal <!--COMPETENCIAS_GERAIS_AQUI--> (sem nenhum texto ao redor, sem tags H5, apenas o comentário HTML). Esse marcador será substituído automaticamente pelo sistema pelo texto oficial completo.

        ESTRUTURA OBRIGATÓRIA DO DOCUMENTO, NESTA ORDEM EXATA:

        1. <div class="doc-cabecalho-oficial">
           Inclua, em formato de linhas rotuladas (<p><strong>RÓTULO:</strong> valor</p>):
           INEP: {inep or '[preencher]'}
           ESCOLA: {nome_escola}
           ENDEREÇO: {endereco_escola or '[preencher endereço]'}
           CIDADE: {cidade_escola or '[preencher cidade]'} ESTADO: {estado_escola}
           ZONA: {zona_escola or '[preencher]'} TELEFONE: {telefone_escola or '[preencher]'} EMAIL: {email_escola or '[preencher]'}
           </div>

        2. <h2 class="doc-titulo-oficial">PLANO BIMESTRAL #{numero_final}</h2>

        3. <div class="doc-metadata-oficial">
           Em linhas rotuladas, exatamente nesta ordem:
           BIMESTRAL // {modalidade}
           {bimestre} {periodo_execucao}
           TURMA: {turma_completa}
           COMP. CURR.: {disciplina}
           EXECUÇÃO: {periodo_execucao}
           CRIADO EM: {criado_em}
           PROFESSOR(A): {nome_professor}
           ANO LETIVO: {ano_letivo_final}
           </div>

        4. <!--COMPETENCIAS_GERAIS_AQUI-->

        5. <h5 class="doc-secao-titulo">Competências Específicas de {disciplina}</h5>
           Liste, numeradas (1ª, 2ª, 3ª...), as competências específicas oficiais da BNCC para a área de conhecimento à qual "{disciplina}" pertence (ex: Ciências da Natureza, Matemática, Linguagens, Ciências Humanas), voltadas ao Ensino Fundamental — Anos Finais. Seja fiel ao texto oficial, sem inventar.

        6. <h5 class="doc-secao-titulo">Unidades Temáticas</h5>
           Identifique a(s) unidade(s) temática(s) da BNCC relacionada(s) ao tema "{tema}" para a série/ano "{ano}", no formato "Nome da Unidade / {ano}".

        7. <h5 class="doc-secao-titulo">Objetos de Conhecimento</h5>
           Liste os objetos de conhecimento relacionados ao tema, cada um seguido de "UNIDADE: [nome da unidade] / {ano}".

        8. <h5 class="doc-secao-titulo">Habilidades</h5>
           Liste as habilidades da BNCC pertinentes (formato: código - descrição completa da habilidade). Priorize o código informado pelo professor ({bncc if bncc else 'nenhum código específico informado — selecione os mais adequados ao tema'}) e complemente com habilidades relacionadas do mesmo objeto de conhecimento.

        9. <h5 class="doc-secao-titulo">Sugestões Metodológicas</h5>
           Lista <ul><li> com 8 a 10 sugestões práticas e variadas de condução das aulas ao longo do bimestre (leitura, TIC, debates, mapas conceituais, saída de campo, mostra científica, etc.), adaptadas ao tema e à realidade do Maranhão quando pertinente.

        10. <h5 class="doc-secao-titulo">Avaliação</h5>
            Lista <ul><li> com os instrumentos avaliativos do bimestre (ex: Avaliação Bimestral, Seminários, Trabalhos individuais e em grupo, etc.), adequados ao tema.

        11. <h5 class="doc-secao-titulo">Recursos</h5>
            Lista <ul><li> com os recursos didáticos necessários (materiais, equipamentos, tecnologia).

        12. <h5 class="doc-secao-titulo">Referências</h5>
            Liste em linhas simples (sem bullets), formato ABNT simplificado:
            BRASIL. Ministério da Educação. Documento Curricular do Território Maranhense (DCTMA): para o ensino fundamental. Rio de Janeiro: FGV, [ano mais recente conhecido].
            BRASIL. Ministério da Educação. Base Nacional Comum Curricular (BNCC). Brasília, 2018.
            E, se pertinente ao tema/disciplina, uma referência bibliográfica de livro didático real e amplamente reconhecido (não invente autores/obras).

        13. <h5 class="doc-secao-titulo">Observações Pertinentes</h5>
            {f'Inclua o seguinte texto informado pelo professor: "{observacoes}"' if observacoes else 'Deixe um parágrafo curto padrão indicando que não há observações adicionais registradas, ou omita se preferir deixar em branco.'}

        DADOS DE CONFIGURAÇÃO DO ESCOPO:
        - Componente/Disciplina: {disciplina}
        - Ano/Série Escolar: {ano}
        - Tema Central / Objeto de Estudo: {tema}
        - Código de Habilidade BNCC Alvo: {bncc}
        """
    elif tipo_modulo == 'Gerador de Provas':
        prompt = f"""
        Atue como um Especialista em Avaliação Pedagógica, com domínio profundo da BNCC, da LDB (Lei nº 9.394/96) e do DCTMA (Documento Curricular do Território Maranhense).
        Gere uma PROVA/AVALIAÇÃO completa sobre o tema "{tema}", disciplina "{disciplina}", ano/série "{ano}".
        NÃO gere nenhum cabeçalho com nome de escola, professor, aluno ou data — isso já é adicionado automaticamente pelo sistema.

        {regras_formato}

        SUA RESPOSTA DEVE TER DUAS PARTES, NESTA ORDEM, SEPARADAS PELO MARCADOR LITERAL EXATO <!--INFO_PEDAGOGICA--> (sem nenhum texto ao redor do marcador):

        ============ PARTE 1 — A PROVA EM SI (vai para o documento impresso/exportado) ============
        1. Gere exatamente {qtd_questoes} questões no formato de aplicação: {tipo_prova}.
        2. Cada questão DEVE estar envolvida em <div class="questao-item">...</div> (uma div por questão, isso é obrigatório para a diagramação em colunas).
        3. Utilize estritamente numeração sequencial de dois dígitos seguida de ponto (Exemplo: 01., 02., 03.).
        4. Sempre inclua a diretriz BNCC entre parênteses logo após o número. Exemplo: '01. (EF09MA02) '.
        5. Todo o texto do enunciado da pergunta DEVE estar encapsulado dentro da tag HTML <strong>...</strong>.
        6. Para questões objetivas, organize alternativas perfeitamente alinhadas verticalmente de a) até d) separadas por quebras de linha <br>.
        7. Para questões discursivas ou subjetivas, adicione o espaço para escrita do aluno aplicando a tag: <div class="linha-resposta"></div> repetida 3 vezes consecutivas.
        8. Após a última questão, inclua <div class="gabarito-prova"><h5>Gabarito</h5>[resposta correta de cada questão, apenas número + alternativa, de forma resumida]</div>.

        ============ PARTE 2 — INFORMAÇÕES PEDAGÓGICAS (fica visível só na tela do sistema, NUNCA é exportada/impressa) ============
        Após o marcador <!--INFO_PEDAGOGICA-->, gere, cada uma como <h5>[Título]</h5>:
        - Objetivos: o que se espera avaliar com esta prova.
        - Competências e Habilidades da BNCC: competência(s) geral(is) e habilidade(s) específica(s) (código + descrição) trabalhadas, priorizando o código informado ({bncc if bncc else 'nenhum informado — selecione os mais adequados ao tema'}).
        - Fundamentação Legal: artigo pertinente da LDB (Lei 9.394/96) e eixo/orientação do DCTMA relacionados ao tema.
        - Configuração Utilizada: resuma em lista os parâmetros desta prova — Disciplina: {disciplina}; Ano/Série: {ano}; Nível: {nivel}; Formato: {tipo_prova}; Quantidade de questões: {qtd_questoes}.
        - Metodologia de Aplicação: sugestões de como aplicar esta avaliação em sala (tempo sugerido, orientações antes da aplicação, critérios de correção).
        """
    elif tipo_modulo == 'Simulados':
        tipo_simulado = kwargs.get('tipo_simulado', 'Simulado Geral / Diagnóstico')
        duracao_simulado = kwargs.get('duracao_simulado', '').strip()
        qtd_questoes_simulado = kwargs.get('qtd_questoes_simulado', '20').strip() or '20'
        duracao_sugerida = duracao_simulado
        if not duracao_sugerida:
            try:
                duracao_sugerida = f"aproximadamente {int(qtd_questoes_simulado) * 3} minutos"
            except ValueError:
                duracao_sugerida = "a critério do professor"

        prompt = f"""
        Atue como um Especialista em Avaliação Pedagógica e Elaboração de Simulados, com domínio profundo da BNCC, da LDB (Lei nº 9.394/96) e do DCTMA (Documento Curricular do Território Maranhense).
        Gere um SIMULADO completo sobre o(s) tema(s)/conteúdo(s) "{tema}", disciplina "{disciplina}", ano/série "{ano}".
        Tipo de simulado: {tipo_simulado}.
        NÃO gere nenhum cabeçalho com nome de escola, professor, aluno ou data — isso já é adicionado automaticamente pelo sistema.

        {regras_formato}

        SUA RESPOSTA DEVE TER DUAS PARTES, NESTA ORDEM, SEPARADAS PELO MARCADOR LITERAL EXATO <!--INFO_PEDAGOGICA--> (sem nenhum texto ao redor do marcador):

        ============ PARTE 1 — O SIMULADO EM SI (vai para o documento impresso/exportado) ============
        1. Inicie com <div class="instrucoes-simulado"><p><strong>Duração sugerida:</strong> {duracao_sugerida}</p><p><strong>Instruções:</strong> [orientações curtas e claras ao aluno sobre como responder, adequadas ao tipo de simulado "{tipo_simulado}"]</p></div>
        2. Gere exatamente {qtd_questoes_simulado} questões, cobrindo de forma equilibrada o(s) conteúdo(s)/tema(s) informado(s). Se mais de um conteúdo/tema foi informado, distribua as questões proporcionalmente entre eles.
        3. Varie o nível de dificuldade ao longo do simulado (fácil, médio, difícil) de forma progressiva ou intercalada, mesmo que o nível informado seja único — isso é característico de simulados reais. Se o nível informado for "Misto", isso é ainda mais importante.
        4. Cada questão DEVE estar envolvida em <div class="questao-item">...</div> (uma div por questão, obrigatório para a diagramação em colunas).
        5. Utilize estritamente numeração sequencial de dois dígitos seguida de ponto (Exemplo: 01., 02., 03.).
        6. Sempre inclua a diretriz BNCC entre parênteses logo após o número. Exemplo: '01. (EF09MA02) '.
        7. Todo o texto do enunciado da pergunta DEVE estar encapsulado dentro da tag HTML <strong>...</strong>.
        8. Para questões objetivas, organize alternativas perfeitamente alinhadas verticalmente de a) até d) separadas por quebras de linha <br>.
        9. Para questões discursivas, adicione <div class="linha-resposta"></div> repetida 3 vezes consecutivas.
        10. Após a última questão, inclua <div class="gabarito-prova"><h5>Gabarito</h5>[resposta correta de cada questão, apenas número + alternativa, de forma resumida]</div>.

        ============ PARTE 2 — INFORMAÇÕES PEDAGÓGICAS (fica visível só na tela do sistema, NUNCA é exportada/impressa) ============
        Após o marcador <!--INFO_PEDAGOGICA-->, gere, cada uma como <h5>[Título]</h5>:
        - Objetivos: o que se espera diagnosticar/revisar com este simulado.
        - Matriz de Referência: uma <table> com colunas "Questão", "Habilidade BNCC", "Nível de Dificuldade", uma linha por questão gerada — replicando o formato de matriz de referência usado em simulados oficiais (tipo SAEB/ENEM).
        - Fundamentação Legal: artigo pertinente da LDB (Lei 9.394/96) e eixo/orientação do DCTMA relacionados ao(s) tema(s).
        - Configuração Utilizada: resuma em lista — Disciplina: {disciplina}; Ano/Série: {ano}; Tipo de Simulado: {tipo_simulado}; Nível: {nivel}; Quantidade de questões: {qtd_questoes_simulado}; Duração sugerida: {duracao_sugerida}.
        - Metodologia de Aplicação: sugestões de como aplicar este simulado (condições de sala, correção, uso dos resultados para intervenção pedagógica).
        """
    else:
        prompt = f"""
        Atue como um Especialista em Design Pedagógico e Elaboração de Conteúdo Escolar Avançado, com domínio profundo da BNCC, da LDB (Lei nº 9.394/96) e do DCTMA (Documento Curricular do Território Maranhense).
        Gere o conteúdo completo e detalhado para o documento estruturado do módulo '{tipo_modulo}'.
        NÃO gere nenhum cabeçalho com nome de escola, professor, aluno ou data — o cabeçalho do documento já é adicionado automaticamente pelo sistema. Comece diretamente pelo conteúdo pedagógico.

        FUNDAMENTAÇÃO LEGAL OBRIGATÓRIA:
        Todo o conteúdo pedagógico deve estar alinhado e referenciar explicitamente, quando aplicável:
        1. BNCC — cite a(s) competência(s) geral(is) e a(s) habilidade(s) específica(s) trabalhada(s).
        2. LDB (Lei nº 9.394/96) — cite o artigo pertinente aos princípios/fins da educação relacionados ao tema.
        3. DCTMA — cite o eixo ou orientação curricular do território maranhense relacionado.
        Inclua uma seção final <h5>Fundamentação Legal</h5> resumindo essas referências.

        DADOS DE CONFIGURAÇÃO DO ESCOPO:
        - Componente/Disciplina: {disciplina}
        - Ano/Série Escolar: {ano}
        - Tema Central / Objeto de Estudo: {tema}
        - Código de Habilidade BNCC Alvo: {bncc}
        - Nível de Rigor Cognitivo: {nivel}
        {regras_formato}
        """
        if tipo_modulo == 'Banco de Atividades':
            tipos_selecionados = kwargs.get('tipos_atividade', []) or ['Questões objetivas']
            lista_tipos = ", ".join(tipos_selecionados)
            prompt += f"""
            DIRETRIZES DO BANCO DE ATIVIDADES:
            1. O professor selecionou os seguintes TIPOS DE ATIVIDADE, que devem OBRIGATORIAMENTE estar presentes no material, cada um em sua própria seção com <h5>[Nome do tipo de atividade]</h5>: {lista_tipos}.
            2. Adapte cada tipo de atividade ao ano/série "{ano}" e ao tema "{tema}" — para anos iniciais/alfabetização, use atividades mais visuais e lúdicas; para anos finais/médio, mais analíticas.
            3. Se o nível de dificuldade for "Misto", varie a dificuldade das questões dentro de cada seção (inclua fácil, médio e difícil).
            4. Para "Complete as lacunas", use "_______" para os espaços em branco.
            5. Para "Ligue as colunas", monte duas colunas usando uma <table>.
            6. Para "Verdadeiro ou Falso", numere as afirmações e inclua parênteses "( )" antes de cada uma para marcação.
            7. Para "Caça-palavras" e "Cruzadinha", gere a LISTA de palavras-chave relacionadas ao tema (não é necessário desenhar a grade visualmente, apenas a lista de palavras e uma breve instrução de como montá-la).
            8. Para atividades práticas/ilustradas/recorte e cole/pintura educativa, descreva claramente as instruções passo a passo para o professor aplicar em sala.
            9. Ao final de TODAS as seções com questões que tenham resposta certa (objetivas, lacunas, V/F, ligue as colunas, sequência lógica, problemas matemáticos), inclua uma seção final única <h5>Gabarito</h5> reunindo as respostas de todas essas atividades.
            """
        elif tipo_modulo == 'Projetos Interdisciplinares':
            duracao = kwargs.get('duracao', '')
            objetivo_geral_prof = kwargs.get('objetivo', '')
            tipos_projeto_sel = kwargs.get('tipos_projeto', []) or ['Projeto Interdisciplinar']
            lista_tipos_projeto = ", ".join(tipos_projeto_sel)
            prompt += f"""
            DIRETRIZES DO GERADOR DE PROJETOS PEDAGÓGICOS:
            O professor quer um projeto do(s) seguinte(s) tipo(s)/formato(s): {lista_tipos_projeto}. Combine as características desses formatos de forma coerente se mais de um for selecionado.
            Duração prevista informada pelo professor: {duracao or 'não informada — sugira uma duração adequada ao escopo do tema'}.
            Objetivo inicial informado pelo professor (use como norte, mas expanda): {objetivo_geral_prof or 'não informado — infira a partir do tema'}.

            ESTRUTURA OBRIGATÓRIA, NESTA ORDEM, cada uma como <h5>[Título da Seção]</h5>:
            1. Justificativa
            2. Objetivo Geral
            3. Objetivos Específicos (lista <ul><li>)
            4. Competências da BNCC (numeradas, relacionadas ao tema e à área)
            5. Habilidades da BNCC (código + descrição, relacionadas ao tema e ano/série "{ano}")
            6. Metodologia
            7. Cronograma (apresente como <table> com colunas Etapa / Descrição / Período, distribuído ao longo da duração informada)
            8. Recursos (lista <ul><li>)
            9. Desenvolvimento (descrição detalhada de como o projeto se desenrola do início ao fim)
            10. Avaliação
            11. Produto Final (o que será entregue/apresentado ao final)
            12. Referências (formato ABNT simplificado, incluindo BNCC e DCTMA; não invente autores)
            """
        elif tipo_modulo == 'Alfabetização e Reforço de Leitura':
            nome_aluno = kwargs.get('nome_aluno', '').strip()
            nivel_leitura = kwargs.get('nivel_leitura', '')
            dificuldades_observadas = kwargs.get('dificuldades_observadas', '')
            focos_selecionados = kwargs.get('focos_alfabetizacao', []) or ['Consciência Fonológica (rimas, sons, sílabas)']
            lista_focos = ", ".join(focos_selecionados)
            duracao_alfab = kwargs.get('duracao_alfabetizacao', '')
            eh_aluno_mais_velho = False
            try:
                eh_aluno_mais_velho = int(re.search(r'\d+', ano).group()) >= 4 if ano and re.search(r'\d+', ano) else False
            except Exception:
                eh_aluno_mais_velho = False

            prompt += f"""
            DIRETRIZES DO PLANO DE ALFABETIZAÇÃO E REFORÇO DE LEITURA:
            Este é um plano de INTERVENÇÃO INDIVIDUALIZADA para um aluno com defasagem de leitura/escrita, não uma atividade de sala genérica.

            DADOS DO ALUNO:
            - Nome (se informado): {nome_aluno or 'não identificado — trate de forma genérica como "o(a) aluno(a)"'}
            - Ano/Série atual: {ano}
            - Nível de leitura/escrita diagnosticado pelo professor: {nivel_leitura or 'não informado — infira um nível plausível a partir das dificuldades descritas'}
            - Dificuldades observadas pelo professor: {dificuldades_observadas or 'não detalhadas — baseie-se no nível informado'}
            - Foco(s) de intervenção priorizado(s): {lista_focos}
            - Duração prevista do plano: {duracao_alfab or 'sugira uma duração adequada (geralmente 4 a 8 semanas)'}
            - Contexto/interesses do aluno informados pelo professor (use para escolher temas de textos e exemplos motivadores): {tema or 'não informado — escolha temas neutros e universalmente interessantes para a idade'}

            {"ATENÇÃO CRÍTICA: o aluno está no " + ano + ", ou seja, é mais velho que a idade típica de alfabetização inicial. NÃO use temas, personagens ou materiais infantilizados (nada de 'bichinhos fofos' ou temas de educação infantil). Use textos, palavras e contextos adequados à idade real do aluno (esportes, música, tecnologia, cotidiano adolescente, temas de interesse da faixa etária), mesmo trabalhando habilidades básicas de leitura. Isso é essencial para não constranger o aluno diante dos colegas." if eh_aluno_mais_velho else "Adeque a linguagem e os temas à faixa etária da educação infantil/anos iniciais, com abordagem lúdica."}

            ESTRUTURA OBRIGATÓRIA, cada uma como <h5>[Título]</h5>:
            1. Diagnóstico e Leitura da Situação — interprete o nível/dificuldades informados e explique o que isso significa na prática.
            2. Objetivos da Intervenção (geral e específicos).
            3. Habilidades da BNCC Relacionadas — competências/habilidades de Língua Portuguesa (alfabetização/leitura) pertinentes ao nível diagnosticado, com código quando aplicável.
            4. Estratégias e Metodologia — métodos de alfabetização reconhecidos (consciência fonológica, método fônico, silabação, leitura compartilhada, etc.), adaptados ao nível e à idade real do aluno.
            5. Sequência de Atividades Práticas — organize em blocos (ex: Semana 1, Semana 2...) com atividades concretas e progressivas, do mais simples ao mais complexo.
            6. Recursos Necessários.
            7. Envolvimento da Família — orientações simples para os responsáveis reforçarem em casa.
            8. Avaliação de Progresso — como o professor vai medir a evolução (indicadores observáveis, não apenas provas).
            9. Referências (formato ABNT simplificado; inclua BNCC, e se pertinente, autores reconhecidos de alfabetização como Magda Soares ou Emilia Ferreiro — não invente nomes/obras).
            """
        elif tipo_modulo == 'Plano de Aula':
            prompt += """
            SEÇÃO OBRIGATÓRIA — METODOLOGIAS E SUGESTÕES DE AULAS DIFERENCIADAS:
            Inclua, antes da conclusão do plano, uma seção <h5>Sugestões de Aulas Diferenciadas</h5> com pelo menos 3 a 4 propostas concretas e variadas para trabalhar o tema de formas alternativas à aula expositiva tradicional, por exemplo (adapte ao tema e ano/série informados):
            - Aula prática/experimental (uso de materiais concretos, experimentos, manipuláveis).
            - Metodologia ativa (sala de aula invertida, aprendizagem baseada em problemas/projetos, gamificação).
            - Atividade em grupo/colaborativa (debate, júri simulado, oficina, estudo de caso).
            - Uso de tecnologia/recursos digitais (aplicativos, vídeos, simuladores, jogos educativos).
            - Conexão com o cotidiano/comunidade local (saída de campo, entrevista, estudo do meio, quando aplicável ao contexto maranhense).
            Apresente cada sugestão em formato de lista <ul><li>, com um parágrafo curto (2-3 linhas) explicando como aplicá-la e qual habilidade/competência da BNCC ela reforça.

            SEÇÃO FINAL OBRIGATÓRIA — REFERÊNCIAS:
            Ao final do documento, após todo o conteúdo pedagógico, inclua uma seção <h5>Referências</h5> contendo:
            1. As referências normativas/legais utilizadas, no formato ABNC simplificado, por exemplo:
               BRASIL. Ministério da Educação. Base Nacional Comum Curricular (BNCC). Brasília: MEC, 2018.
               BRASIL. Lei nº 9.394, de 20 de dezembro de 1996. Lei de Diretrizes e Bases da Educação Nacional (LDB). Brasília, 1996.
               MARANHÃO. Secretaria de Estado da Educação. Documento Curricular do Território Maranhense (DCTMA). São Luís, [ano de publicação mais recente conhecido].
            2. Quaisquer referências bibliográficas pedagógicas adicionais (autores, teóricos ou materiais didáticos) efetivamente utilizados como base conceitual para o conteúdo gerado, também em formato ABNT simplificado, listadas em <ul><li>.
            3. Não invente nomes de autores ou obras específicas que não sejam amplamente reconhecidas na área; se não houver referência bibliográfica adicional além das normativas, inclua apenas as normativas.
            """
        else:
            prompt += f"\nEstruture o documento de forma oficial e profissional com cabeçalhos h4, h5, parágrafos bem espaçados e listas dinâmicas."

    # 3. ENDPOINT DA API DO GEMINI COM A URL 100% HIGIENIZADA
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={chave_limpa}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            resultado = response.json()
            texto_gerado = resultado['candidates'][0]['content']['parts'][0]['text']
            texto_gerado = texto_gerado.replace("```html", "").replace("```", "").strip()
            texto_gerado = sanitizar_saida_html(texto_gerado)
            # Substitui o marcador pelo texto oficial fixo das Competências Gerais da Educação Básica
            if '<!--COMPETENCIAS_GERAIS_AQUI-->' in texto_gerado:
                texto_gerado = texto_gerado.replace('<!--COMPETENCIAS_GERAIS_AQUI-->', montar_html_competencias_gerais())

            info_pedagogica = ''
            if tipo_modulo in ('Gerador de Provas', 'Simulados'):
                if '<!--INFO_PEDAGOGICA-->' in texto_gerado:
                    parte_prova, parte_info = texto_gerado.split('<!--INFO_PEDAGOGICA-->', 1)
                else:
                    parte_prova, parte_info = texto_gerado, ''
                texto_gerado = montar_prova_duas_colunas(parte_prova)
                info_pedagogica = parte_info.strip()

            return texto_gerado, info_pedagogica
        else:
            return obter_fallback_pedagogico(tipo_modulo, tema, f"Código {response.status_code} - Resposta: {response.text}"), ''
            
    except Exception as e:
        return obter_fallback_pedagogico(tipo_modulo, tema, f"Falha de conexão física: {str(e)}"), ''

# =====================================================================
# EXPORTAÇÃO — DOCX e PDF (preservando cabeçalhos, tabelas, listas, negrito)
# =====================================================================
def _definir_colunas_secao(section, num_colunas):
    """Configura o número de colunas (estilo jornal) de uma seção do Word via XML."""
    sectPr = section._sectPr
    cols = sectPr.find(qn('w:cols'))
    if cols is None:
        cols = OxmlElement('w:cols')
        sectPr.append(cols)
    cols.set(qn('w:num'), str(num_colunas))
    cols.set(qn('w:space'), '480')

def _adicionar_no_docx(documento, node):
    """Converte um nó de questão (strong/br/div.linha-resposta/texto) em um parágrafo do Word."""
    p = documento.add_paragraph()
    for filho in node.children:
        nome = getattr(filho, 'name', None)
        if nome == 'strong' or nome == 'b':
            run = p.add_run(filho.get_text())
            run.bold = True
        elif nome == 'br':
            p.add_run().add_break()
        elif nome == 'div' and 'linha-resposta' in (filho.get('class') or []):
            documento.add_paragraph('_' * 55)
        elif nome is None:
            texto = str(filho)
            if texto.strip():
                p.add_run(texto)
        else:
            texto = filho.get_text()
            if texto.strip():
                p.add_run(texto)
    documento.add_paragraph("")

def gerar_docx(titulo, escola, professor, html_conteudo, tipo_modulo='', disciplina='', ano=''):
    documento = Document()

    p_escola = documento.add_paragraph()
    p_escola.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_escola = p_escola.add_run(escola or "Instituição de Ensino")
    r_escola.bold = True
    r_escola.font.size = Pt(15)

    if tipo_modulo in ('Gerador de Provas', 'Simulados'):
        rotulo_titulo = "AVALIAÇÃO DE" if tipo_modulo == 'Gerador de Provas' else "SIMULADO DE"
        p_titulo = documento.add_paragraph()
        p_titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_titulo = p_titulo.add_run(f"{rotulo_titulo} {(disciplina or '').upper()}" + (f" — {ano}" if ano else ""))
        r_titulo.bold = True
        r_titulo.font.size = Pt(13)

        p_prof = documento.add_paragraph()
        p_prof.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_prof = p_prof.add_run(f"Professor(a): {professor}")
        r_prof.italic = True
        r_prof.font.size = Pt(10)

        documento.add_paragraph("")

        # Campos de identificação (Aluno / Turma / Data / Nota)
        tabela_id = documento.add_table(rows=2, cols=2)
        tabela_id.cell(0, 0).text = "ALUNO(A): " + "_" * 38
        tabela_id.cell(0, 1).text = "TURMA: " + "_" * 10
        tabela_id.cell(1, 0).text = "DATA: ____/____/______"
        tabela_id.cell(1, 1).text = "NOTA: " + "_" * 12
        documento.add_paragraph("")

        soup = BeautifulSoup(html_conteudo, 'html.parser')
        itens = soup.find_all('div', class_='questao-item')
        gabarito_tag = soup.find('div', class_='gabarito-prova')

        # Seção em 2 colunas reais do Word para as questões
        secao_questoes = documento.add_section(WD_SECTION.CONTINUOUS)
        _definir_colunas_secao(secao_questoes, 2)

        estilo_normal = documento.styles['Normal']
        estilo_normal.font.name = 'Arial'
        estilo_normal.font.size = Pt(12)

        if itens:
            for item in itens:
                _adicionar_no_docx(documento, item)
        else:
            documento.add_paragraph(soup.get_text())

        # Volta para 1 coluna antes do gabarito
        secao_gabarito = documento.add_section(WD_SECTION.CONTINUOUS)
        _definir_colunas_secao(secao_gabarito, 1)

        if gabarito_tag:
            documento.add_paragraph("")
            h_gab = documento.add_paragraph()
            r_gab = h_gab.add_run("Gabarito")
            r_gab.bold = True
            r_gab.font.size = Pt(12)
            gabarito_copia = BeautifulSoup(str(gabarito_tag), 'html.parser')
            titulo_existente = gabarito_copia.find('h5')
            if titulo_existente:
                titulo_existente.decompose()
            conversor = HtmlToDocx()
            conversor.add_html_to_document(str(gabarito_copia), documento)

    else:
        p_titulo = documento.add_paragraph()
        p_titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_titulo = p_titulo.add_run(titulo or tipo_modulo or "Documento Pedagógico")
        r_titulo.bold = True
        r_titulo.font.size = Pt(14)

        p_prof = documento.add_paragraph()
        p_prof.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_prof = p_prof.add_run(f"Professor(a): {professor}")
        r_prof.italic = True

        documento.add_paragraph("")
        conversor = HtmlToDocx()
        conversor.add_html_to_document(html_conteudo, documento)

    buffer = BytesIO()
    documento.save(buffer)
    buffer.seek(0)
    return buffer

def gerar_pdf(titulo, escola, professor, html_conteudo, tipo_modulo='', disciplina='', ano=''):
    if tipo_modulo in ('Gerador de Provas', 'Simulados'):
        rotulo_titulo_pdf = "Avaliação de" if tipo_modulo == 'Gerador de Provas' else "Simulado de"
        bloco_cabecalho = f"""
        <div class="cabecalho-pdf">
            <h1>{escola}</h1>
            <h2 style="font-size:13pt; text-transform:uppercase; letter-spacing:1px; margin:4px 0;">{rotulo_titulo_pdf} {(disciplina or '').upper()}{f' — {ano}' if ano else ''}</h2>
            <p style="font-size:10pt; color:#52627e;">Professor(a): {professor}</p>
            <table style="border:none; margin-top:10px;">
                <tr>
                    <td style="border:none; width:65%;">ALUNO(A): {'_' * 45}</td>
                    <td style="border:none; width:35%;">TURMA: {'_' * 10}</td>
                </tr>
                <tr>
                    <td style="border:none;">DATA: ____/____/______</td>
                    <td style="border:none;">NOTA: {'_' * 12}</td>
                </tr>
            </table>
        </div>
        """
    else:
        bloco_cabecalho = f"""
        <div class="cabecalho-pdf">
            <h1>{titulo or 'Documento Pedagógico'}</h1>
            <p><strong>Instituição de Ensino:</strong> {escola}<br/><strong>Professor(a):</strong> {professor}</p>
        </div>
        """

    html_completo = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; color: #0f1f3d; }}
        h1 {{ font-size: 16pt; text-align: center; color: #0e2a5e; margin-bottom: 2px; }}
        h4, h5 {{ color: #123a7a; margin-top: 14px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #999; padding: 5px 8px; font-size: 10pt; }}
        th {{ background-color: #eef2fa; }}
        .cabecalho-pdf {{ text-align: center; margin-bottom: 18px; border-bottom: 1px solid #999; padding-bottom: 10px; }}
    </style>
    </head>
    <body>
        {bloco_cabecalho}
        {html_conteudo}
    </body>
    </html>
    """
    buffer = BytesIO()
    pisa.CreatePDF(src=html_completo, dest=buffer, encoding='utf-8')
    buffer.seek(0)
    return buffer

# =====================================================================
# INICIALIZAÇÃO DO BANCO DE DADOS (SQLite)
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

    # Histórico + Biblioteca (favoritos) de materiais gerados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materiais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_email TEXT NOT NULL,
            tipo_modulo TEXT,
            titulo TEXT,
            disciplina TEXT,
            ano TEXT,
            conteudo_html TEXT,
            favorito INTEGER DEFAULT 0,
            criado_em TEXT
        )
    ''')

    # Banco de Questões reutilizáveis
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banco_questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_email TEXT NOT NULL,
            ano TEXT,
            disciplina TEXT,
            conteudo TEXT,
            bncc TEXT,
            dificuldade TEXT,
            enunciado_html TEXT,
            criado_em TEXT
        )
    ''')

    # Migração segura: adiciona a coluna info_pedagogica se o banco já existia sem ela
    try:
        cursor.execute("ALTER TABLE materiais ADD COLUMN info_pedagogica TEXT")
    except sqlite3.OperationalError:
        pass  # coluna já existe

    conn.commit()
    conn.close()

init_db()

# =====================================================================
# ROTAS FLASK
# =====================================================================
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
            session.permanent = True
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

    # Campos específicos do Planejamento Bimestral
    numero_plano = request.form.get('numero_plano', '').strip()
    bimestre = request.form.get('bimestre', '1º BIM').strip()
    data_inicio = request.form.get('data_inicio', '').strip()
    data_fim = request.form.get('data_fim', '').strip()
    turma = request.form.get('turma', '').strip()
    turno = request.form.get('turno', '').strip()
    modalidade = request.form.get('modalidade', 'Presencial').strip()
    ano_letivo = request.form.get('ano_letivo', '').strip()
    inep = request.form.get('inep', '').strip()
    endereco_escola = request.form.get('endereco_escola', '').strip()
    cidade_escola = request.form.get('cidade_escola', '').strip()
    estado_escola = request.form.get('estado_escola', 'MA').strip()
    zona_escola = request.form.get('zona_escola', '').strip()
    telefone_escola = request.form.get('telefone_escola', '').strip()
    email_escola = request.form.get('email_escola', '').strip()
    observacoes = request.form.get('observacoes', '').strip()

    # Campos específicos do Banco de Atividades e Projetos
    tipos_atividade = request.form.getlist('tipos_atividade')
    tipos_projeto = request.form.getlist('tipos_projeto')
    duracao = request.form.get('duracao', '').strip()
    objetivo = request.form.get('objetivo', '').strip()

    # Campos específicos do módulo de Alfabetização e Reforço de Leitura
    nome_aluno = request.form.get('nome_aluno', '').strip()
    nivel_leitura = request.form.get('nivel_leitura', '').strip()
    dificuldades_observadas = request.form.get('dificuldades_observadas', '').strip()
    focos_alfabetizacao = request.form.getlist('focos_alfabetizacao')
    duracao_alfabetizacao = request.form.get('duracao_alfabetizacao', '').strip()

    # Campos específicos do módulo de Simulados
    tipo_simulado = request.form.get('tipo_simulado', 'Simulado Geral / Diagnóstico').strip()
    duracao_simulado = request.form.get('duracao_simulado', '').strip()
    qtd_questoes_simulado = request.form.get('qtd_questoes_simulado', '20').strip()

    material_id = None
    info_pedagogica = ""

    pode_gerar = tema or (form_type == 'alfabetizacao' and (nivel_leitura or dificuldades_observadas or nome_aluno))
    if request.method == 'POST' and pode_gerar:
        conteudo, info_pedagogica = executar_geracao_ia(
            tipo_modulo=config_modulo['nome'],
            disciplina=disciplina,
            ano=ano,
            tema=tema,
            bncc=bncc,
            tipo_prova=tipo_prova,
            qtd_questoes=qtd_questoes,
            nivel=nivel,
            nome_professor=session.get('user_name', 'Professor(a)'),
            nome_escola=session.get('user_school', 'Instituição de Ensino'),
            numero_plano=numero_plano,
            bimestre=bimestre,
            data_inicio=data_inicio,
            data_fim=data_fim,
            turma=turma,
            turno=turno,
            modalidade=modalidade,
            ano_letivo=ano_letivo,
            inep=inep,
            endereco_escola=endereco_escola,
            cidade_escola=cidade_escola,
            estado_escola=estado_escola,
            zona_escola=zona_escola,
            telefone_escola=telefone_escola,
            email_escola=email_escola,
            observacoes=observacoes,
            tipos_atividade=tipos_atividade,
            tipos_projeto=tipos_projeto,
            duracao=duracao,
            objetivo=objetivo,
            nome_aluno=nome_aluno,
            nivel_leitura=nivel_leitura,
            dificuldades_observadas=dificuldades_observadas,
            focos_alfabetizacao=focos_alfabetizacao,
            duracao_alfabetizacao=duracao_alfabetizacao,
            tipo_simulado=tipo_simulado,
            duracao_simulado=duracao_simulado,
            qtd_questoes_simulado=qtd_questoes_simulado
        )

        # Registra automaticamente no Histórico / Biblioteca
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO materiais (usuario_email, tipo_modulo, titulo, disciplina, ano, conteudo_html, favorito, criado_em, info_pedagogica)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
            ''', (
                session.get('user_email', ''), config_modulo['nome'], tema, disciplina, ano,
                conteudo, datetime.now().strftime('%d/%m/%Y %H:%M'), info_pedagogica
            ))
            material_id = cursor.lastrowid
            conn.commit()
            conn.close()
        except Exception:
            material_id = None

    return render_template(
        'dashboard.html',
        form_type=form_type,
        config=config_modulo,
        conteudo=conteudo,
        material_id=material_id,
        info_pedagogica=info_pedagogica,
        tema=tema,
        disciplina=disciplina if disciplina else "Componente Curricular",
        ano=ano,
        bncc=bncc,
        tipo_prova=tipo_prova,
        qtd_questoes=qtd_questoes,
        nivel=nivel,
        numero_plano=numero_plano,
        bimestre=bimestre,
        data_inicio=data_inicio,
        data_fim=data_fim,
        turma=turma,
        turno=turno,
        modalidade=modalidade,
        ano_letivo=ano_letivo,
        inep=inep,
        endereco_escola=endereco_escola,
        cidade_escola=cidade_escola,
        estado_escola=estado_escola,
        zona_escola=zona_escola,
        telefone_escola=telefone_escola,
        email_escola=email_escola,
        observacoes=observacoes,
        tipos_atividade=tipos_atividade,
        tipos_projeto=tipos_projeto,
        duracao=duracao,
        objetivo=objetivo,
        nome_aluno=nome_aluno,
        nivel_leitura=nivel_leitura,
        dificuldades_observadas=dificuldades_observadas,
        focos_alfabetizacao=focos_alfabetizacao,
        duracao_alfabetizacao=duracao_alfabetizacao,
        tipo_simulado=tipo_simulado,
        duracao_simulado=duracao_simulado,
        qtd_questoes_simulado=qtd_questoes_simulado,
        TIPOS_ATIVIDADE=TIPOS_ATIVIDADE,
        TIPOS_PROJETO=TIPOS_PROJETO,
        NIVEIS_LEITURA=NIVEIS_LEITURA,
        FOCOS_ALFABETIZACAO=FOCOS_ALFABETIZACAO,
        TIPOS_SIMULADO=TIPOS_SIMULADO,
        app_name="Professor IA",
        name=session.get('user_name', 'Samuel Araújo Sousa'),     
        school=session.get('user_school', 'U.E. Prof. João Martins Neto')  
    )

@app.route('/exportar/<int:material_id>/<formato>')
def exportar_material(material_id, formato):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materiais WHERE id = ? AND usuario_email = ?", (material_id, session.get('user_email', '')))
    material = cursor.fetchone()
    conn.close()

    if not material:
        return redirect(url_for('dashboard'))

    titulo = material['titulo'] or material['tipo_modulo']
    escola = session.get('user_school', '')
    professor = session.get('user_name', '')
    nome_arquivo_base = re.sub(r'[^a-zA-Z0-9]+', '_', titulo)[:60] or 'documento'

    if formato == 'docx':
        buffer = gerar_docx(titulo, escola, professor, material['conteudo_html'], material['tipo_modulo'], material['disciplina'], material['ano'])
        return send_file(
            buffer, as_attachment=True, download_name=f"{nome_arquivo_base}.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    elif formato == 'pdf':
        buffer = gerar_pdf(titulo, escola, professor, material['conteudo_html'], material['tipo_modulo'], material['disciplina'], material['ano'])
        return send_file(buffer, as_attachment=True, download_name=f"{nome_arquivo_base}.pdf", mimetype='application/pdf')
    else:
        return redirect(url_for('dashboard'))

@app.route('/biblioteca')
def biblioteca():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    apenas_favoritos = request.args.get('favoritos') == '1'
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if apenas_favoritos:
        cursor.execute("SELECT * FROM materiais WHERE usuario_email = ? AND favorito = 1 ORDER BY id DESC", (session.get('user_email', ''),))
    else:
        cursor.execute("SELECT * FROM materiais WHERE usuario_email = ? ORDER BY id DESC", (session.get('user_email', ''),))
    materiais = cursor.fetchall()
    conn.close()

    return render_template(
        'biblioteca.html', materiais=materiais, apenas_favoritos=apenas_favoritos,
        app_name="Professor IA", name=session.get('user_name', ''), school=session.get('user_school', '')
    )

@app.route('/biblioteca/ver/<int:material_id>')
def ver_material(material_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materiais WHERE id = ? AND usuario_email = ?", (material_id, session.get('user_email', '')))
    material = cursor.fetchone()
    conn.close()

    if not material:
        return redirect(url_for('biblioteca'))

    return render_template(
        'material.html', material=material,
        app_name="Professor IA", name=session.get('user_name', ''), school=session.get('user_school', '')
    )

@app.route('/biblioteca/favoritar/<int:material_id>', methods=['POST'])
def favoritar_material(material_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT favorito FROM materiais WHERE id = ? AND usuario_email = ?", (material_id, session.get('user_email', '')))
    row = cursor.fetchone()
    if row:
        novo_valor = 0 if row[0] == 1 else 1
        cursor.execute("UPDATE materiais SET favorito = ? WHERE id = ?", (novo_valor, material_id))
        conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('biblioteca'))

@app.route('/biblioteca/editar/<int:material_id>', methods=['POST'])
def editar_material(material_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    novo_titulo = request.form.get('title', '').strip()
    novo_conteudo = request.form.get('content', '').strip()
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE materiais SET titulo = ?, conteudo_html = ? WHERE id = ? AND usuario_email = ?",
        (novo_titulo, novo_conteudo, material_id, session.get('user_email', ''))
    )
    conn.commit()
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {'status': 'ok', 'material_id': material_id}

    return redirect(url_for('ver_material', material_id=material_id))

@app.route('/biblioteca/excluir/<int:material_id>', methods=['POST'])
def excluir_material(material_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM materiais WHERE id = ? AND usuario_email = ?", (material_id, session.get('user_email', '')))
    conn.commit()
    conn.close()
    return redirect(url_for('biblioteca'))

@app.route('/banco-questoes')
def banco_questoes():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    filtro_ano = request.args.get('ano', '').strip()
    filtro_disciplina = request.args.get('disciplina', '').strip()
    filtro_conteudo = request.args.get('conteudo', '').strip()
    filtro_bncc = request.args.get('bncc', '').strip()
    filtro_dificuldade = request.args.get('dificuldade', '').strip()

    query = "SELECT * FROM banco_questoes WHERE usuario_email = ?"
    params = [session.get('user_email', '')]
    if filtro_ano:
        query += " AND ano LIKE ?"; params.append(f"%{filtro_ano}%")
    if filtro_disciplina:
        query += " AND disciplina LIKE ?"; params.append(f"%{filtro_disciplina}%")
    if filtro_conteudo:
        query += " AND conteudo LIKE ?"; params.append(f"%{filtro_conteudo}%")
    if filtro_bncc:
        query += " AND bncc LIKE ?"; params.append(f"%{filtro_bncc}%")
    if filtro_dificuldade:
        query += " AND dificuldade = ?"; params.append(filtro_dificuldade)
    query += " ORDER BY id DESC"

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    questoes = cursor.fetchall()
    conn.close()

    return render_template(
        'banco_questoes.html', questoes=questoes,
        filtro_ano=filtro_ano, filtro_disciplina=filtro_disciplina, filtro_conteudo=filtro_conteudo,
        filtro_bncc=filtro_bncc, filtro_dificuldade=filtro_dificuldade,
        app_name="Professor IA", name=session.get('user_name', ''), school=session.get('user_school', '')
    )

@app.route('/banco-questoes/salvar', methods=['POST'])
def salvar_banco_questoes():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO banco_questoes (usuario_email, ano, disciplina, conteudo, bncc, dificuldade, enunciado_html, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session.get('user_email', ''),
        request.form.get('ano', ''),
        request.form.get('disciplina', ''),
        request.form.get('tema', ''),
        request.form.get('bncc', ''),
        request.form.get('nivel', ''),
        request.form.get('conteudo_html', ''),
        datetime.now().strftime('%d/%m/%Y %H:%M')
    ))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for('banco_questoes'))

@app.route('/banco-questoes/excluir/<int:questao_id>', methods=['POST'])
def excluir_questao(questao_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM banco_questoes WHERE id = ? AND usuario_email = ?", (questao_id, session.get('user_email', '')))
    conn.commit()
    conn.close()
    return redirect(url_for('banco_questoes'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)