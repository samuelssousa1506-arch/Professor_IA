import os
import re
import sqlite3
import random
import time
import requests
import markdown as md
from io import BytesIO
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect, generate_csrf
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from htmldocx import HtmlToDocx
from xhtml2pdf import pisa
from bs4 import BeautifulSoup
import bleach

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_mestra_professor_ia_2026")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

csrf = CSRFProtect(app)

# 1. MAPEAMENTO DAS CHAVES DE IA
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "").strip()

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
    'alfabetizacao': {'nome': 'Alfabetização e Reforço de Leitura', 'icone': 'fa-spell-check'},
    'sequencia': {'nome': 'Sequência Didática', 'icone': 'fa-layer-group'},
    'diagnostico': {'nome': 'Diagnóstico da Turma', 'icone': 'fa-chart-pie'},
    'assistente': {'nome': 'Assistente Pedagógico', 'icone': 'fa-robot'},
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

# =====================================================================
# FUNÇÕES AUXILIARES (mantidas e adaptadas)
# =====================================================================

def sanitizar_saida_html(texto):
    texto = texto.strip()
    parece_markdown = bool(re.search(r'(^|\n)#{2,6}\s|\*\*[^*]+\*\*|(^|\n)\*\s|(^|\n)-\s', texto))
    if parece_markdown:
        texto = md.markdown(texto, extensions=['tables', 'nl2br', 'sane_lists'])
    # Sanitização com bleach (remove scripts)
    allowed_tags = ['h4','h5','h6','p','strong','em','ul','ol','li','table','thead','tbody','tr','th','td','div','span','br','a','img','blockquote','pre','code']
    allowed_attrs = {'*': ['class'], 'a': ['href'], 'img': ['src', 'alt']}
    texto = bleach.clean(texto, tags=allowed_tags, attributes=allowed_attrs, strip=True)
    return texto

def montar_html_competencias_gerais():
    ordinais = ["1ª", "2ª", "3ª", "4ª", "5ª", "6ª", "7ª", "8ª", "9ª", "10ª"]
    itens = "".join(
        f"<p><strong>{ordinais[i]}</strong> - {texto}</p>"
        for i, texto in enumerate(COMPETENCIAS_GERAIS_BNCC)
    )
    return f'<h5 class="doc-secao-titulo">Competências Gerais da Educação Básica</h5><div class="doc-secao-corpo">{itens}</div>'

def montar_prova_duas_colunas(html_questoes):
    soup = BeautifulSoup(html_questoes, 'html.parser')
    itens = soup.find_all('div', class_='questao-item')
    gabarito_tag = soup.find('div', class_='gabarito-prova')
    gabarito_html = str(gabarito_tag) if gabarito_tag else ''
    fonte_estilo = 'font-family: Arial, Helvetica, sans-serif; font-size: 12pt; line-height: 1.4;'
    if not itens:
        conteudo_sem_gabarito = html_questoes
        if gabarito_tag:
            conteudo_sem_gabarito = conteudo_sem_gabarito.replace(str(gabarito_tag), '')
        return f'<div style="{fonte_estilo}">{conteudo_sem_gabarito}</div>', gabarito_html
    questoes_html = "".join(str(i) for i in itens)
    bloco_colunas = f"""
    <div class="prova-colunas" style="column-count:2; -webkit-column-count:2; column-gap:30px; -webkit-column-gap:30px; column-rule:1px solid #999; {fonte_estilo}">
        {questoes_html}
    </div>
    """
    return bloco_colunas, gabarito_html

def obter_fallback_pedagogico(tipo_modulo, tema, erro_adicional=""):
    sobrecarga = "503" in erro_adicional and ("UNAVAILABLE" in erro_adicional or "overloaded" in erro_adicional.lower() or "high demand" in erro_adicional.lower())
    limite_requisicoes = "429" in erro_adicional
    falha_conexao = "Falha de conexão física" in erro_adicional or "timed out" in erro_adicional.lower() or "timeout" in erro_adicional.lower()
    if sobrecarga:
        mensagem_principal = "Os servidores de IA estão temporariamente sobrecarregados (alta demanda no momento). O sistema já tentou os provedores configurados automaticamente, mas nenhum respondeu a tempo. Isso normalmente se resolve em poucos minutos — tente gerar novamente."
    elif limite_requisicoes:
        mensagem_principal = "Foi atingido um limite de requisições em um dos provedores de IA configurados. Aguarde um instante antes de tentar novamente, ou verifique sua cota no painel do provedor correspondente."
    elif falha_conexao:
        mensagem_principal = "O sistema não conseguiu estabelecer conexão com os servidores de IA a tempo (timeout de rede). Isso pode ser uma instabilidade temporária de rede — tente gerar novamente em alguns instantes."
    else:
        mensagem_principal = "O sistema não conseguiu gerar o conteúdo com nenhum dos provedores de IA configurados. Certifique-se de que as variáveis <strong>GEMINI_API_KEY</strong> (e, se estiver usando, <strong>MISTRAL_API_KEY</strong>) estão configuradas corretamente no painel do Render."
    return f"""
    <h4><i class="fa-solid fa-graduation-cap text-primary me-2"></i> {tipo_modulo} (Modo de Segurança)</h4>
    <p>{mensagem_principal}</p>
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
    # Campos específicos
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
    # Campos específicos de sequência didática
    qtd_aulas = kwargs.get('qtd_aulas', '5')
    duracao = kwargs.get('duracao', '')
    objetivo_geral = kwargs.get('objetivo_geral', '')
    objetivos_especificos = kwargs.get('objetivos_especificos', '')
    perfil_turma = kwargs.get('perfil_turma', '')
    dificuldades = kwargs.get('dificuldades', '')
    recursos = kwargs.get('recursos', '')
    metodologia = kwargs.get('metodologia', '')
    # Campos de diagnóstico
    qtd_alunos = kwargs.get('qtd_alunos', '')
    dificuldades_diagnostico = kwargs.get('dificuldades_diagnostico', '')
    habilidades_consolidadas = kwargs.get('habilidades_consolidadas', '')
    habilidades_dificuldade = kwargs.get('habilidades_dificuldade', '')
    nivel_geral = kwargs.get('nivel_geral', '')
    observacoes_diagnostico = kwargs.get('observacoes_diagnostico', '')

    if not GEMINI_API_KEY:
        return obter_fallback_pedagogico(tipo_modulo, tema, "A variável GEMINI_API_KEY está ausente no painel do Render."), ''

    match = re.search(r'(AIzaSy[A-Za-z0-9_-]+|AQ\.[A-Za-z0-9_-]+)', GEMINI_API_KEY)
    if match:
        chave_limpa = match.group(1).strip()
    else:
        chave_limpa = GEMINI_API_KEY.replace("[", "").replace("]", "").replace("'", "").replace('"', '')
        if "key=" in chave_limpa:
            chave_limpa = chave_limpa.split("key=")[-1]
        if ")" in chave_limpa:
            chave_limpa = chave_limpa.split(")")[-1]
        chave_limpa = chave_limpa.strip()

    # CONSTRUÇÃO DO PROMPT
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
           Liste, numeradas (1ª, 2ª, 3ª...), as competências específicas oficiais da BNCC para a área de conhecimento à qual "{disciplina}" pertence, voltadas ao Ensino Fundamental — Anos Finais.

        6. <h5 class="doc-secao-titulo">Unidades Temáticas</h5>
           Identifique a(s) unidade(s) temática(s) da BNCC relacionada(s) ao tema "{tema}" para a série/ano "{ano}".

        7. <h5 class="doc-secao-titulo">Objetos de Conhecimento</h5>
           Liste os objetos de conhecimento relacionados ao tema.

        8. <h5 class="doc-secao-titulo">Habilidades</h5>
           Liste as habilidades da BNCC pertinentes (formato: código - descrição), priorizando {bncc if bncc else 'as mais adequadas'}.

        9. <h5 class="doc-secao-titulo">Sugestões Metodológicas</h5>
           Lista <ul><li> com 8 a 10 sugestões práticas.

        10. <h5 class="doc-secao-titulo">Avaliação</h5>
            Lista <ul><li> com os instrumentos avaliativos.

        11. <h5 class="doc-secao-titulo">Recursos</h5>
            Lista <ul><li> com os recursos didáticos.

        12. <h5 class="doc-secao-titulo">Referências</h5>
            Liste em linhas simples, formato ABNT simplificado: BNCC, DCTMA, e bibliografia pertinente.

        13. <h5 class="doc-secao-titulo">Observações Pertinentes</h5>
            {f'Inclua o seguinte texto informado pelo professor: "{observacoes}"' if observacoes else 'Sem observações adicionais.'}
        """
    elif tipo_modulo == 'Gerador de Provas':
        prompt = f"""
        Atue como um Especialista em Avaliação Pedagógica. Gere uma PROVA/AVALIAÇÃO completa sobre o tema "{tema}", disciplina "{disciplina}", ano/série "{ano}".
        NÃO gere cabeçalho — o sistema adiciona automaticamente.
        {regras_formato}

        SUA RESPOSTA DEVE TER DUAS PARTES, SEPARADAS PELO MARCADOR LITERAL <!--INFO_PEDAGOGICA-->:

        ============ PARTE 1 — A PROVA EM SI ============
        1. Gere exatamente {qtd_questoes} questões no formato {tipo_prova}.
        2. Cada questão DEVE estar em <div class="questao-item">...</div>.
        3. Numere com dois dígitos: 01., 02., etc.
        4. Inclua (código BNCC) após o número: '01. (EF09MA02) '.
        5. O enunciado em <strong>.
        6. Para objetivas, use a) até d) com <br>.
        7. Para discursivas, gere <div class="linha-resposta"></div> conforme o espaço esperado.
        8. Após a última questão, inclua <div class="gabarito-prova"><h5>Gabarito</h5>[respostas]</div>.

        ============ PARTE 2 — INFORMAÇÕES PEDAGÓGICAS ============
        Após o marcador, gere <h5>Objetivos</h5>, <h5>Competências e Habilidades</h5> (priorizando {bncc if bncc else 'as adequadas'}), <h5>Fundamentação Legal</h5>, <h5>Configuração Utilizada</h5>, <h5>Metodologia de Aplicação</h5>.
        """
    elif tipo_modulo == 'Simulados':
        tipo_simulado = kwargs.get('tipo_simulado', 'Simulado Geral / Diagnóstico')
        duracao_simulado = kwargs.get('duracao_simulado', '').strip()
        qtd_questoes_simulado = kwargs.get('qtd_questoes_simulado', '20').strip() or '20'
        duracao_sugerida = duracao_simulado or f"aproximadamente {int(qtd_questoes_simulado) * 3} minutos"
        prompt = f"""
        Atue como Especialista em Simulados. Gere um SIMULADO sobre "{tema}", disciplina "{disciplina}", ano "{ano}".
        Tipo: {tipo_simulado}. NÃO gere cabeçalho.
        {regras_formato}

        SUA RESPOSTA DEVE TER DUAS PARTES, SEPARADAS POR <!--INFO_PEDAGOGICA-->:

        ============ PARTE 1 — SIMULADO ============
        1. Inicie com <div class="instrucoes-simulado"><p><strong>Duração:</strong> {duracao_sugerida}</p><p><strong>Instruções:</strong> ...</p></div>
        2. Gere {qtd_questoes_simulado} questões em <div class="questao-item">.
        3. Numere 01., 02., etc. Inclua código BNCC.
        4. Use <strong> para o enunciado, e alternativas a) a d) com <br>.
        5. Para discursivas, use <div class="linha-resposta">.
        6. Inclua <div class="gabarito-prova"><h5>Gabarito</h5>[respostas]</div>.

        ============ PARTE 2 — INFORMAÇÕES PEDAGÓGICAS ============
        Após o marcador, gere <h5>Objetivos</h5>, <h5>Matriz de Referência</h5> (tabela com questões, habilidades, dificuldade), <h5>Fundamentação Legal</h5>, <h5>Configuração</h5>, <h5>Metodologia de Aplicação</h5>.
        """
    elif tipo_modulo == 'Sequência Didática':
        prompt = f"""
        Atue como Especialista em Planejamento de Ensino. Gere uma SEQUÊNCIA DIDÁTICA para {disciplina}, {ano}, tema "{tema}".
        Dados: Habilidade BNCC: {bncc if bncc else 'selecione as adequadas'}; Aulas: {qtd_aulas}; Duração: {duracao or 'a definir'};
        Objetivo geral: {objetivo_geral or 'infira'}; Objetivos específicos: {objetivos_especificos or 'descreva 3-5'};
        Perfil da turma: {perfil_turma or 'heterogênea'}; Dificuldades: {dificuldades or 'não informadas'};
        Recursos: {recursos or 'básicos'}; Metodologia: {metodologia or 'ativas'}.
        {regras_formato}

        ESTRUTURA OBRIGATÓRIA:
        <h5>Identificação</h5> (disciplina, ano, tema, duração, aulas)
        <h5>Justificativa</h5>
        <h5>Objetivo Geral</h5>
        <h5>Objetivos Específicos</h5> (lista)
        <h5>Habilidades BNCC</h5> (código + descrição)
        <h5>Conteúdos</h5> (lista)
        <h5>Metodologia</h5> (descrição geral)
        <h5>Desenvolvimento (Aula a Aula)</h5> (subseções <h6>Aula X</h6>)
        <h5>Recursos</h5> (lista)
        <h5>Avaliação</h5>
        <h5>Inclusão/Adaptações</h5>
        <h5>Referências</h5>
        """
    elif tipo_modulo == 'Diagnóstico da Turma':
        prompt = f"""
        Atue como Especialista em Diagnóstico Pedagógico. Com base nos dados do professor, elabore DIAGNÓSTICO e PLANO DE INTERVENÇÃO para {disciplina}, {ano}.
        Dados: Alunos: {qtd_alunos or 'não informado'}; Dificuldades: {dificuldades_diagnostico or 'não informadas'};
        Habilidades consolidadas: {habilidades_consolidadas or 'não informadas'};
        Habilidades com dificuldade: {habilidades_dificuldade or 'não informadas'};
        Nível geral: {nivel_geral or 'não informado'}; Observações: {observacoes_diagnostico or ''}.
        {regras_formato}

        ESTRUTURA OBRIGATÓRIA em duas partes:

        PARTE 1 — DIAGNÓSTICO:
        <h5>Panorama Geral</h5>
        <h5>Pontos Fortes</h5> (lista)
        <h5>Principais Dificuldades</h5> (lista)
        <h5>Habilidades Prioritárias</h5> (lista)
        <h5>Necessidades de Intervenção</h5>

        PARTE 2 — PLANO DE INTERVENÇÃO:
        <h5>Objetivos da Intervenção</h5>
        <h5>Estratégias e Metodologias</h5>
        <h5>Atividades Sugeridas</h5> (organizadas)
        <h5>Diferenciação e Inclusão</h5>
        <h5>Acompanhamento e Avaliação</h5>
        <h5>Indicadores de Progresso</h5>
        <h5>Referências</h5>
        """
    else:
        # Para os demais módulos (plano, atividades, etc.) — mantém o prompt genérico
        prompt = f"""
        Atue como Especialista em Design Pedagógico, com domínio da BNCC, LDB e DCTMA.
        Gere o conteúdo completo para o módulo '{tipo_modulo}'.
        DADOS: Tema: {tema}, Disciplina: {disciplina}, Ano: {ano}, BNCC: {bncc if bncc else 'selecione as adequadas'}, Nível: {nivel}.
        {regras_formato}
        """ + (f" DIRETRIZES ESPECÍFICAS: {kwargs.get('diretrizes_extra', '')}" if kwargs.get('diretrizes_extra') else "")

    # CADEIA DE PROVEDORES (fallback automático)
    payload_gemini = {"contents": [{"parts": [{"text": prompt}]}]}
    headers_gemini = {'Content-Type': 'application/json'}
    mistral_chave_limpa = MISTRAL_API_KEY.replace("[", "").replace("]", "").replace("'", "").replace('"', "").strip()
    payload_mistral = {"model": "mistral-small-latest", "messages": [{"role": "user", "content": prompt}]}
    headers_mistral = {'Content-Type': 'application/json', 'Authorization': f'Bearer {mistral_chave_limpa}'}

    def _extrair_texto_gemini(resultado):
        return resultado['candidates'][0]['content']['parts'][0]['text']
    def _extrair_texto_mistral(resultado):
        return resultado['choices'][0]['message']['content']

    PROVEDORES_EM_CASCATA = [
        {"nome": "gemini-3.5-flash", "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={chave_limpa}", "headers": headers_gemini, "payload": payload_gemini, "extrair": _extrair_texto_gemini, "ativo": bool(chave_limpa)},
        {"nome": "gemini-2.5-flash-lite", "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={chave_limpa}", "headers": headers_gemini, "payload": payload_gemini, "extrair": _extrair_texto_gemini, "ativo": bool(chave_limpa)},
        {"nome": "mistral-small-latest", "url": "https://api.mistral.ai/v1/chat/completions", "headers": headers_mistral, "payload": payload_mistral, "extrair": _extrair_texto_mistral, "ativo": bool(mistral_chave_limpa)},
    ]

    MAX_TENTATIVAS_POR_PROVEDOR = 2
    ultimo_erro = ""
    for provedor in PROVEDORES_EM_CASCATA:
        if not provedor["ativo"]:
            continue
        for tentativa in range(1, MAX_TENTATIVAS_POR_PROVEDOR + 1):
            try:
                response = requests.post(provedor["url"], headers=provedor["headers"], json=provedor["payload"], timeout=60)
                if response.status_code == 200:
                    resultado = response.json()
                    texto_gerado = provedor["extrair"](resultado)
                    texto_gerado = texto_gerado.replace("```html", "").replace("```", "").strip()
                    texto_gerado = sanitizar_saida_html(texto_gerado)
                    if '<!--COMPETENCIAS_GERAIS_AQUI-->' in texto_gerado:
                        texto_gerado = texto_gerado.replace('<!--COMPETENCIAS_GERAIS_AQUI-->', montar_html_competencias_gerais())
                    info_pedagogica = ''
                    if tipo_modulo in ('Gerador de Provas', 'Simulados'):
                        if '<!--INFO_PEDAGOGICA-->' in texto_gerado:
                            parte_prova, parte_info = texto_gerado.split('<!--INFO_PEDAGOGICA-->', 1)
                        else:
                            parte_prova, parte_info = texto_gerado, ''
                        texto_gerado, gabarito_extraido = montar_prova_duas_colunas(parte_prova)
                        bloco_gabarito_tela = f'<div class="gabarito-tela">{gabarito_extraido}</div>' if gabarito_extraido else ''
                        info_pedagogica = (bloco_gabarito_tela + parte_info.strip()).strip()
                    return texto_gerado, info_pedagogica
                if response.status_code in (503, 429):
                    ultimo_erro = f"Código {response.status_code} - Provedor {provedor['nome']} - Resposta: {response.text}"
                    if tentativa < MAX_TENTATIVAS_POR_PROVEDOR:
                        time.sleep(2 * tentativa)
                        continue
                    break
                ultimo_erro = f"Código {response.status_code} - Provedor {provedor['nome']} - Resposta: {response.text}"
                break
            except Exception as e:
                ultimo_erro = f"Falha de conexão física - Provedor {provedor['nome']}: {str(e)}"
                if tentativa < MAX_TENTATIVAS_POR_PROVEDOR:
                    time.sleep(2 * tentativa)
                    continue
                break
    return obter_fallback_pedagogico(tipo_modulo, tema, ultimo_erro + " (cascata de provedores esgotada)"), ''

# =====================================================================
# EXPORTAÇÃO — DOCX e PDF (mantido igual)
# =====================================================================
def _definir_colunas_secao(section, num_colunas):
    sectPr = section._sectPr
    cols = sectPr.find(qn('w:cols'))
    if cols is None:
        cols = OxmlElement('w:cols')
        sectPr.append(cols)
    cols.set(qn('w:num'), str(num_colunas))
    cols.set(qn('w:space'), '480')

def _adicionar_no_docx(documento, node):
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
        tabela_id = documento.add_table(rows=2, cols=2)
        tabela_id.cell(0, 0).text = "ALUNO(A): " + "_" * 38
        tabela_id.cell(0, 1).text = "TURMA: " + "_" * 10
        tabela_id.cell(1, 0).text = "DATA: ____/____/______"
        tabela_id.cell(1, 1).text = "NOTA: " + "_" * 12
        documento.add_paragraph("")
        soup = BeautifulSoup(html_conteudo, 'html.parser')
        itens = soup.find_all('div', class_='questao-item')
        gabarito_tag = soup.find('div', class_='gabarito-prova')
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
        if gabarito_tag:
            secao_gabarito = documento.add_section(WD_SECTION.CONTINUOUS)
            _definir_colunas_secao(secao_gabarito, 1)
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
                <tr><td style="border:none; width:65%;">ALUNO(A): {'_' * 45}</td><td style="border:none; width:35%;">TURMA: {'_' * 10}</td></tr>
                <tr><td style="border:none;">DATA: ____/____/______</td><td style="border:none;">NOTA: {'_' * 12}</td></tr>
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
    <head><meta charset="utf-8">
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
# INICIALIZAÇÃO DO BANCO DE DADOS (com migrações seguras)
# =====================================================================
DB_PATH = os.environ.get('DATABASE_PATH', 'database.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Tabela usuarios com novas colunas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            escola TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            role TEXT DEFAULT 'professor',
            ativo INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Adicionar colunas se não existirem (migração)
    for col in ['role', 'ativo', 'created_at', 'updated_at']:
        try:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass

    # Verificar se existe usuário admin, senão criar um padrão
    cursor.execute("SELECT * FROM usuarios WHERE email = 'admin@professor.ia'")
    if not cursor.fetchone():
        senha_hash = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO usuarios (nome, escola, email, senha, role)
            VALUES ('Administrador', 'Sistema', 'admin@professor.ia', ?, 'admin')
        ''', (senha_hash,))
        print("Usuário admin criado: admin@professor.ia / admin123")

    # Tabela materiais (já existe, adicionar coluna pasta_id se não existir)
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
            criado_em TEXT,
            info_pedagogica TEXT,
            pasta_id INTEGER DEFAULT NULL,
            FOREIGN KEY (pasta_id) REFERENCES pastas(id)
        )
    ''')
    try:
        cursor.execute("ALTER TABLE materiais ADD COLUMN pasta_id INTEGER")
    except sqlite3.OperationalError:
        pass

    # Tabela pastas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pastas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_email TEXT NOT NULL,
            nome TEXT NOT NULL,
            cor TEXT DEFAULT '#6c757d'
        )
    ''')

    # Tabela banco_questoes (já existe, não precisa mexer)
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

    conn.commit()
    conn.close()

init_db()

# =====================================================================
# FUNÇÕES DE AUTENTICAÇÃO E AUTORIZAÇÃO
# =====================================================================
def get_usuario(email):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def usuario_eh_admin(email):
    user = get_usuario(email)
    return user and user['role'] == 'admin' and user['ativo'] == 1

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        if not usuario_eh_admin(session.get('user_email')):
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def get_materiais_usuario(email, pasta_id=None, favorito=None, tipo=None, disciplina=None, ano=None, search=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT * FROM materiais WHERE usuario_email = ?"
    params = [email]
    if pasta_id is not None:
        query += " AND pasta_id = ?"
        params.append(pasta_id)
    if favorito is not None:
        query += " AND favorito = ?"
        params.append(1 if favorito else 0)
    if tipo:
        query += " AND tipo_modulo = ?"
        params.append(tipo)
    if disciplina:
        query += " AND disciplina LIKE ?"
        params.append(f"%{disciplina}%")
    if ano:
        query += " AND ano LIKE ?"
        params.append(f"%{ano}%")
    if search:
        query += " AND (titulo LIKE ? OR disciplina LIKE ? OR ano LIKE ? OR tipo_modulo LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term, search_term])
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    materiais = cursor.fetchall()
    conn.close()
    return materiais

def get_pastas_usuario(email):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pastas WHERE usuario_email = ? ORDER BY nome", (email,))
    pastas = cursor.fetchall()
    conn.close()
    return pastas

# =====================================================================
# ROTAS
# =====================================================================

@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    email = session.get('user_email')
    user = get_usuario(email)
    materiais = get_materiais_usuario(email)
    favoritos = get_materiais_usuario(email, favorito=True)
    recentes = materiais[:5]
    planos = [m for m in materiais if m['tipo_modulo'] == 'Plano de Aula'][:5]
    avaliacoes = [m for m in materiais if m['tipo_modulo'] == 'Gerador de Provas'][:5]
    sequencias = [m for m in materiais if m['tipo_modulo'] == 'Sequência Didática'][:5]
    diagnosticos = [m for m in materiais if m['tipo_modulo'] == 'Diagnóstico da Turma'][:5]
    return render_template('home.html',
                           user=user,
                           materiais=recentes,
                           favoritos=favoritos,
                           planos=planos,
                           avaliacoes=avaliacoes,
                           sequencias=sequencias,
                           diagnosticos=diagnosticos,
                           total_materiais=len(materiais),
                           app_name="Professor IA",
                           name=user['nome'],
                           school=user['escola'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    sucesso = request.args.get('sucesso')
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('senha', '').strip()
        user = get_usuario(email)
        if user and user['ativo'] == 1 and check_password_hash(user['senha'], password):
            session.permanent = True
            session['logged_in'] = True
            session['user_email'] = email
            session['user_name'] = user['nome']
            session['user_school'] = user['escola']
            session['user_role'] = user['role']
            return redirect(url_for('home'))
        else:
            erro = "E-mail ou senha incorretos, ou conta inativa."
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
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                senha_hash = generate_password_hash(senha)
                cursor.execute(
                    "INSERT INTO usuarios (nome, escola, email, senha, role) VALUES (?, ?, ?, ?, 'professor')",
                    (nome, escola, email, senha_hash)
                )
                conn.commit()
                conn.close()
                return redirect(url_for('login', sucesso="Conta criada com sucesso! Faça login."))
            except sqlite3.IntegrityError:
                erro = "Este e-mail já está cadastrado no sistema."
    return render_template('cadastro.html', erro=erro)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# =====================================================================
# DASHBOARD DO GERADOR (mantido e corrigido)
# =====================================================================
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    form_type = request.args.get('form_type') or request.form.get('form_type') or 'plano'
    if form_type not in MODULOS:
        form_type = 'plano'
    config_modulo = MODULOS[form_type]
    conteudo = ""
    # Coleta de parâmetros do formulário
    tema = request.form.get('tema', '').strip()
    disciplina = request.form.get('disciplina', '').strip()
    ano = request.form.get('ano', '').strip()
    bncc = request.form.get('bncc', '').strip()
    tipo_prova = request.form.get('tipo_prova', '').strip()
    qtd_questoes = request.form.get('qtd_questoes', '').strip()
    nivel = request.form.get('nivel', '').strip()
    # Campos específicos
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
    tipos_atividade = request.form.getlist('tipos_atividade')
    tipos_projeto = request.form.getlist('tipos_projeto')
    duracao = request.form.get('duracao', '').strip()
    objetivo = request.form.get('objetivo', '').strip()
    nome_aluno = request.form.get('nome_aluno', '').strip()
    nivel_leitura = request.form.get('nivel_leitura', '').strip()
    dificuldades_observadas = request.form.get('dificuldades_observadas', '').strip()
    focos_alfabetizacao = request.form.getlist('focos_alfabetizacao')
    duracao_alfabetizacao = request.form.get('duracao_alfabetizacao', '').strip()
    tipo_simulado = request.form.get('tipo_simulado', 'Simulado Geral / Diagnóstico').strip()
    duracao_simulado = request.form.get('duracao_simulado', '').strip()
    qtd_questoes_simulado = request.form.get('qtd_questoes_simulado', '20').strip()
    # Novos campos para sequência didática
    qtd_aulas = request.form.get('qtd_aulas', '5').strip()
    objetivo_geral = request.form.get('objetivo_geral', '').strip()
    objetivos_especificos = request.form.get('objetivos_especificos', '').strip()
    perfil_turma = request.form.get('perfil_turma', '').strip()
    dificuldades = request.form.get('dificuldades', '').strip()
    recursos = request.form.get('recursos', '').strip()
    metodologia = request.form.get('metodologia', '').strip()
    # Diagnóstico
    qtd_alunos = request.form.get('qtd_alunos', '').strip()
    dificuldades_diagnostico = request.form.get('dificuldades_diagnostico', '').strip()
    habilidades_consolidadas = request.form.get('habilidades_consolidadas', '').strip()
    habilidades_dificuldade = request.form.get('habilidades_dificuldade', '').strip()
    nivel_geral = request.form.get('nivel_geral', '').strip()
    observacoes_diagnostico = request.form.get('observacoes_diagnostico', '').strip()

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
            duracao=duracao,                 # única ocorrência
            objetivo=objetivo,
            nome_aluno=nome_aluno,
            nivel_leitura=nivel_leitura,
            dificuldades_observadas=dificuldades_observadas,
            focos_alfabetizacao=focos_alfabetizacao,
            duracao_alfabetizacao=duracao_alfabetizacao,
            tipo_simulado=tipo_simulado,
            duracao_simulado=duracao_simulado,
            qtd_questoes_simulado=qtd_questoes_simulado,
            # Novos (sem duplicação)
            qtd_aulas=qtd_aulas,
            objetivo_geral=objetivo_geral,
            objetivos_especificos=objetivos_especificos,
            perfil_turma=perfil_turma,
            dificuldades=dificuldades,
            recursos=recursos,
            metodologia=metodologia,
            qtd_alunos=qtd_alunos,
            dificuldades_diagnostico=dificuldades_diagnostico,
            habilidades_consolidadas=habilidades_consolidadas,
            habilidades_dificuldade=habilidades_dificuldade,
            nivel_geral=nivel_geral,
            observacoes_diagnostico=observacoes_diagnostico
        )
        # Salvar na biblioteca
        try:
            conn = sqlite3.connect(DB_PATH)
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
        except Exception as e:
            print("Erro ao salvar material:", e)
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
        qtd_aulas=qtd_aulas,
        objetivo_geral=objetivo_geral,
        objetivos_especificos=objetivos_especificos,
        perfil_turma=perfil_turma,
        dificuldades=dificuldades,
        recursos=recursos,
        metodologia=metodologia,
        qtd_alunos=qtd_alunos,
        dificuldades_diagnostico=dificuldades_diagnostico,
        habilidades_consolidadas=habilidades_consolidadas,
        habilidades_dificuldade=habilidades_dificuldade,
        nivel_geral=nivel_geral,
        observacoes_diagnostico=observacoes_diagnostico,
        TIPOS_ATIVIDADE=TIPOS_ATIVIDADE,
        TIPOS_PROJETO=TIPOS_PROJETO,
        NIVEIS_LEITURA=NIVEIS_LEITURA,
        FOCOS_ALFABETIZACAO=FOCOS_ALFABETIZACAO,
        TIPOS_SIMULADO=TIPOS_SIMULADO,
        app_name="Professor IA",
        name=session.get('user_name', ''),
        school=session.get('user_school', '')
    )

# =====================================================================
# ASSISTENTE PEDAGÓGICO
# =====================================================================
@app.route('/assistente', methods=['GET', 'POST'])
@login_required
def assistente():
    resposta = ""
    if request.method == 'POST':
        pergunta = request.form.get('pergunta', '').strip()
        if pergunta:
            conteudo, _ = executar_geracao_ia(
                tipo_modulo='Tira-Dúvidas com IA',
                tema=pergunta,
                nome_professor=session.get('user_name', 'Professor(a)'),
                nome_escola=session.get('user_school', 'Instituição de Ensino')
            )
            resposta = conteudo
    return render_template('assistente.html', resposta=resposta, name=session.get('user_name', ''))

# =====================================================================
# BIBLIOTECA 2.0
# =====================================================================
@app.route('/biblioteca')
@login_required
def biblioteca():
    email = session.get('user_email')
    search = request.args.get('search', '').strip()
    tipo = request.args.get('tipo', '').strip()
    disciplina = request.args.get('disciplina', '').strip()
    ano = request.args.get('ano', '').strip()
    favorito = request.args.get('favorito')
    favorito_bool = None
    if favorito == '1':
        favorito_bool = True
    elif favorito == '0':
        favorito_bool = False
    pasta_id = request.args.get('pasta')
    pasta_id = int(pasta_id) if pasta_id and pasta_id.isdigit() else None

    materiais = get_materiais_usuario(email, pasta_id=pasta_id, favorito=favorito_bool, tipo=tipo, disciplina=disciplina, ano=ano, search=search)
    pastas = get_pastas_usuario(email)
    return render_template('biblioteca.html',
                           materiais=materiais,
                           pastas=pastas,
                           search=search,
                           tipo=tipo,
                           disciplina=disciplina,
                           ano=ano,
                           favorito=favorito,
                           pasta_id=pasta_id,
                           name=session.get('user_name', ''),
                           school=session.get('user_school', ''))

@app.route('/biblioteca/ver/<int:material_id>')
@login_required
def ver_material(material_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materiais WHERE id = ? AND usuario_email = ?", (material_id, session.get('user_email', '')))
    material = cursor.fetchone()
    conn.close()
    if not material:
        flash('Material não encontrado.', 'danger')
        return redirect(url_for('biblioteca'))
    return render_template('material.html', material=material, name=session.get('user_name', ''), school=session.get('user_school', ''))

@app.route('/biblioteca/favoritar/<int:material_id>', methods=['POST'])
@login_required
def favoritar_material(material_id):
    conn = sqlite3.connect(DB_PATH)
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
@login_required
def editar_material(material_id):
    novo_titulo = request.form.get('title', '').strip()
    novo_conteudo = request.form.get('content', '').strip()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE materiais SET titulo = ?, conteudo_html = ? WHERE id = ? AND usuario_email = ?",
        (novo_titulo, novo_conteudo, material_id, session.get('user_email', ''))
    )
    conn.commit()
    conn.close()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'ok', 'material_id': material_id})
    return redirect(url_for('ver_material', material_id=material_id))

@app.route('/biblioteca/excluir/<int:material_id>', methods=['POST'])
@login_required
def excluir_material(material_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM materiais WHERE id = ? AND usuario_email = ?", (material_id, session.get('user_email', '')))
    conn.commit()
    conn.close()
    return redirect(url_for('biblioteca'))

@app.route('/biblioteca/duplicar/<int:material_id>', methods=['POST'])
@login_required
def duplicar_material(material_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materiais WHERE id = ? AND usuario_email = ?", (material_id, session.get('user_email', '')))
    original = cursor.fetchone()
    if not original:
        conn.close()
        flash('Material original não encontrado.', 'danger')
        return redirect(url_for('biblioteca'))
    cursor.execute('''
        INSERT INTO materiais (usuario_email, tipo_modulo, titulo, disciplina, ano, conteudo_html, favorito, criado_em, info_pedagogica, pasta_id)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
    ''', (
        original['usuario_email'],
        original['tipo_modulo'],
        original['titulo'] + ' (cópia)',
        original['disciplina'],
        original['ano'],
        original['conteudo_html'],
        datetime.now().strftime('%d/%m/%Y %H:%M'),
        original['info_pedagogica'],
        original['pasta_id']
    ))
    conn.commit()
    conn.close()
    flash('Material duplicado com sucesso!', 'success')
    return redirect(url_for('biblioteca'))

# Rotas para pastas
@app.route('/biblioteca/pastas', methods=['GET', 'POST'])
@login_required
def gerenciar_pastas():
    email = session.get('user_email')
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        cor = request.form.get('cor', '#6c757d').strip()
        if nome:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO pastas (usuario_email, nome, cor) VALUES (?, ?, ?)", (email, nome, cor))
            conn.commit()
            conn.close()
            flash('Pasta criada!', 'success')
        return redirect(url_for('gerenciar_pastas'))
    pastas = get_pastas_usuario(email)
    return render_template('pastas.html', pastas=pastas, name=session.get('user_name', ''))

@app.route('/biblioteca/pastas/excluir/<int:pasta_id>', methods=['POST'])
@login_required
def excluir_pasta(pasta_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE materiais SET pasta_id = NULL WHERE pasta_id = ? AND usuario_email = ?", (pasta_id, session.get('user_email', '')))
    cursor.execute("DELETE FROM pastas WHERE id = ? AND usuario_email = ?", (pasta_id, session.get('user_email', '')))
    conn.commit()
    conn.close()
    flash('Pasta excluída. Materiais movidos para "Sem pasta".', 'info')
    return redirect(url_for('gerenciar_pastas'))

@app.route('/biblioteca/mover/<int:material_id>', methods=['POST'])
@login_required
def mover_material(material_id):
    pasta_id = request.form.get('pasta_id')
    pasta_id = int(pasta_id) if pasta_id and pasta_id.isdigit() else None
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE materiais SET pasta_id = ? WHERE id = ? AND usuario_email = ?", (pasta_id, material_id, session.get('user_email', '')))
    conn.commit()
    conn.close()
    return redirect(url_for('biblioteca'))

# =====================================================================
# EXPORTAÇÃO
# =====================================================================
@app.route('/exportar/<int:material_id>/<formato>')
@login_required
def exportar_material(material_id, formato):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materiais WHERE id = ? AND usuario_email = ?", (material_id, session.get('user_email', '')))
    material = cursor.fetchone()
    conn.close()
    if not material:
        return redirect(url_for('biblioteca'))
    titulo = material['titulo'] or material['tipo_modulo']
    escola = session.get('user_school', '')
    professor = session.get('user_name', '')
    nome_arquivo_base = re.sub(r'[^a-zA-Z0-9]+', '_', titulo)[:60] or 'documento'
    if formato == 'docx':
        buffer = gerar_docx(titulo, escola, professor, material['conteudo_html'], material['tipo_modulo'], material['disciplina'], material['ano'])
        return send_file(buffer, as_attachment=True, download_name=f"{nome_arquivo_base}.docx", mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    elif formato == 'pdf':
        buffer = gerar_pdf(titulo, escola, professor, material['conteudo_html'], material['tipo_modulo'], material['disciplina'], material['ano'])
        return send_file(buffer, as_attachment=True, download_name=f"{nome_arquivo_base}.pdf", mimetype='application/pdf')
    else:
        return redirect(url_for('biblioteca'))

# =====================================================================
# ADAPTAR PARA INCLUSÃO/AEE
# =====================================================================
@app.route('/adaptar/<int:material_id>', methods=['GET', 'POST'])
@login_required
def adaptar_material(material_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materiais WHERE id = ? AND usuario_email = ?", (material_id, session.get('user_email', '')))
    material = cursor.fetchone()
    conn.close()
    if not material:
        flash('Material não encontrado.', 'danger')
        return redirect(url_for('biblioteca'))
    if request.method == 'POST':
        dificuldades = request.form.get('dificuldades', '').strip()
        barreiras = request.form.get('barreiras', '').strip()
        habilidades_preservadas = request.form.get('habilidades_preservadas', '').strip()
        nivel_aluno = request.form.get('nivel_aluno', '').strip()
        recursos_disponiveis = request.form.get('recursos_disponiveis', '').strip()
        observacoes = request.form.get('observacoes', '').strip()
        acoes = request.form.getlist('acoes')
        # Construir prompt específico para adaptação
        prompt_adaptacao = f"""
        Você é um especialista em Educação Inclusiva e AEE.
        Adapte o seguinte material pedagógico para atender às necessidades de um aluno com dificuldades.

        MATERIAL ORIGINAL:
        {material['conteudo_html']}

        INFORMAÇÕES DO ALUNO:
        - Dificuldades observadas: {dificuldades}
        - Barreiras de aprendizagem: {barreiras}
        - Habilidades preservadas: {habilidades_preservadas}
        - Nível do aluno: {nivel_aluno}
        - Recursos disponíveis: {recursos_disponiveis}
        - Observações: {observacoes}

        AÇÕES SELECIONADAS: {', '.join(acoes)}

        {regras_formato}

        Gere uma versão adaptada do material, preservando o objetivo pedagógico original.
        Inclua um cabeçalho com "VERSÃO ADAPTADA PARA INCLUSÃO/AEE".
        Mantenha a estrutura semelhante, mas simplifique a linguagem, instruções, e adicione suportes visuais ou estratégias diferenciadas conforme as ações selecionadas.
        """
        # Usar a mesma função de geração, passando a diretriz extra
        conteudo_adaptado, _ = executar_geracao_ia(
            tipo_modulo='Plano de Inclusão / AEE',
            tema='Adaptação de material',
            disciplina=material['disciplina'],
            ano=material['ano'],
            nome_professor=session.get('user_name', 'Professor(a)'),
            nome_escola=session.get('user_school', 'Instituição de Ensino'),
            diretrizes_extra=prompt_adaptacao
        )
        # Salvar como novo material
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO materiais (usuario_email, tipo_modulo, titulo, disciplina, ano, conteudo_html, favorito, criado_em, info_pedagogica)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
        ''', (
            session.get('user_email', ''),
            'Adaptado para AEE',
            material['titulo'] + ' (adaptado)',
            material['disciplina'],
            material['ano'],
            conteudo_adaptado,
            datetime.now().strftime('%d/%m/%Y %H:%M'),
            ''
        ))
        novo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        flash('Material adaptado com sucesso!', 'success')
        return redirect(url_for('ver_material', material_id=novo_id))
    return render_template('adaptar.html', material=material, name=session.get('user_name', ''))

# =====================================================================
# ADMINISTRAÇÃO
# =====================================================================
@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total_usuarios FROM usuarios")
    total_usuarios = cursor.fetchone()['total_usuarios']
    cursor.execute("SELECT COUNT(*) as total_professores FROM usuarios WHERE role = 'professor'")
    total_professores = cursor.fetchone()['total_professores']
    cursor.execute("SELECT COUNT(*) as total_escolas FROM usuarios GROUP BY escola")
    total_escolas = len(cursor.fetchall())
    cursor.execute("SELECT COUNT(*) as total_materiais FROM materiais")
    total_materiais = cursor.fetchone()['total_materiais']
    cursor.execute("SELECT tipo_modulo, COUNT(*) as total FROM materiais GROUP BY tipo_modulo ORDER BY total DESC")
    materiais_por_modulo = cursor.fetchall()
    cursor.execute("SELECT disciplina, COUNT(*) as total FROM materiais GROUP BY disciplina ORDER BY total DESC")
    materiais_por_disciplina = cursor.fetchall()
    cursor.execute("SELECT usuario_email, COUNT(*) as total FROM materiais GROUP BY usuario_email ORDER BY total DESC")
    materiais_por_professor = cursor.fetchall()
    cursor.execute("SELECT DATE(criado_em) as data, COUNT(*) as total FROM materiais GROUP BY DATE(criado_em) ORDER BY data DESC LIMIT 30")
    materiais_por_periodo = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html',
                           total_usuarios=total_usuarios,
                           total_professores=total_professores,
                           total_escolas=total_escolas,
                           total_materiais=total_materiais,
                           materiais_por_modulo=materiais_por_modulo,
                           materiais_por_disciplina=materiais_por_disciplina,
                           materiais_por_professor=materiais_por_professor,
                           materiais_por_periodo=materiais_por_periodo,
                           name=session.get('user_name', ''))

@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios ORDER BY id")
    usuarios = cursor.fetchall()
    conn.close()
    return render_template('admin_usuarios.html', usuarios=usuarios, name=session.get('user_name', ''))

@app.route('/admin/usuario/<int:id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_usuario(id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT ativo FROM usuarios WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row:
        novo_status = 0 if row[0] == 1 else 1
        cursor.execute("UPDATE usuarios SET ativo = ? WHERE id = ?", (novo_status, id))
        conn.commit()
    conn.close()
    flash('Status do usuário alterado.', 'success')
    return redirect(url_for('admin_usuarios'))

@app.route('/admin/usuario/<int:id>/role', methods=['POST'])
@admin_required
def admin_role_usuario(id):
    nova_role = request.form.get('role', 'professor')
    if nova_role not in ['professor', 'admin']:
        flash('Role inválida.', 'danger')
        return redirect(url_for('admin_usuarios'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET role = ? WHERE id = ?", (nova_role, id))
    conn.commit()
    conn.close()
    flash('Role atualizada.', 'success')
    return redirect(url_for('admin_usuarios'))

# =====================================================================
# BANCO DE QUESTÕES
# =====================================================================
@app.route('/banco-questoes')
@login_required
def banco_questoes():
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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, params)
    questoes = cursor.fetchall()
    conn.close()
    return render_template('banco_questoes.html', questoes=questoes, filtro_ano=filtro_ano, filtro_disciplina=filtro_disciplina, filtro_conteudo=filtro_conteudo, filtro_bncc=filtro_bncc, filtro_dificuldade=filtro_dificuldade, name=session.get('user_name', ''), school=session.get('user_school', ''))

@app.route('/banco-questoes/salvar', methods=['POST'])
@login_required
def salvar_banco_questoes():
    conn = sqlite3.connect(DB_PATH)
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
@login_required
def excluir_questao(questao_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM banco_questoes WHERE id = ? AND usuario_email = ?", (questao_id, session.get('user_email', '')))
    conn.commit()
    conn.close()
    return redirect(url_for('banco_questoes'))

# =====================================================================
# RODANDO O APP
# =====================================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)