import os
import secrets
from datetime import date

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from flask_sqlalchemy import SQLAlchemy

NOME_ALUNO = 'Léo'
PRIORIDADES = {'alta': 'Alta', 'media': 'Média', 'baixa': 'Baixa'}
STATUS = {'todas': 'Todas', 'pendentes': 'Pendentes',
          'atrasadas': 'Atrasadas', 'concluidas': 'Concluídas'}

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'EDUTRACK_DB', 'sqlite:///' + os.path.join(basedir, 'edutrack.db'))
# shortcut: chave fixa de desenvolvimento; defina SECRET_KEY antes de publicar na internet
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-troque-em-producao')

db = SQLAlchemy(app)


class Materia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tarefas = db.relationship('Tarefa', backref='materia',
                              cascade='all, delete-orphan')


class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=False, default='')
    prazo = db.Column(db.Date)
    prioridade = db.Column(db.String(10), nullable=False, default='media')
    concluida = db.Column(db.Boolean, nullable=False, default=False)
    materia_id = db.Column(db.Integer, db.ForeignKey('materia.id'), nullable=False)

    @property
    def atrasada(self):
        return bool(not self.concluida and self.prazo and self.prazo < date.today())


# Cria as tabelas que faltarem; as matérias já salvas são preservadas
with app.app_context():
    db.create_all()


# ---------- segurança: CSRF e redirecionamento ----------

@app.before_request
def checar_csrf():
    if request.method == 'POST':
        token = session.get('csrf')
        if not token or not secrets.compare_digest(token, request.form.get('csrf_token', '')):
            abort(400)


@app.context_processor
def contexto():
    session.setdefault('csrf', secrets.token_hex(16))
    return {'csrf_token': session['csrf'], 'PRIORIDADES': PRIORIDADES}


def voltar():
    """Volta para a página de origem (mantendo filtros), só se for um caminho local."""
    destino = request.form.get('voltar', '')
    if destino.startswith('/') and not destino.startswith('//'):
        return redirect(destino)
    return redirect(url_for('index'))


# ---------- validação ----------

def ler_tarefa(form):
    """Devolve (dados, erro). `erro` é None quando o formulário é válido."""
    titulo = form.get('titulo', '').strip()
    if not titulo:
        return None, 'Dê um título para a tarefa.'
    if len(titulo) > 150:
        return None, 'O título pode ter no máximo 150 caracteres.'

    materia = db.session.get(Materia, form.get('materia_id', type=int))
    if not materia:
        return None, 'Escolha uma matéria válida.'

    prioridade = form.get('prioridade', 'media')
    if prioridade not in PRIORIDADES:
        return None, 'Prioridade inválida.'

    prazo = None
    if form.get('prazo'):
        try:
            prazo = date.fromisoformat(form['prazo'])
        except ValueError:
            return None, 'Data inválida.'

    return dict(titulo=titulo, descricao=form.get('descricao', '').strip(),
                prazo=prazo, prioridade=prioridade, materia_id=materia.id), None


# ---------- páginas ----------

@app.route('/')
def index():
    status = request.args.get('status', 'todas')
    materia_id = request.args.get('materia', type=int)
    busca = request.args.get('q', '').strip()

    materias = Materia.query.order_by(Materia.nome).all()
    todas = Tarefa.query.all()
    resumo = {
        'total': len(todas),
        'concluidas': sum(t.concluida for t in todas),
        'atrasadas': sum(t.atrasada for t in todas),
    }
    resumo['pendentes'] = resumo['total'] - resumo['concluidas']
    resumo['progresso'] = round(100 * resumo['concluidas'] / resumo['total']) if todas else 0
    pendentes_por_materia = {m.id: sum(not t.concluida for t in m.tarefas) for m in materias}

    filtros = {
        'pendentes': lambda t: not t.concluida,
        'concluidas': lambda t: t.concluida,
        'atrasadas': lambda t: t.atrasada,
    }
    tarefas = [t for t in todas
               if filtros.get(status, lambda t: True)(t)
               and (not materia_id or t.materia_id == materia_id)
               and busca.lower() in t.titulo.lower()]
    ordem_prioridade = list(PRIORIDADES)
    tarefas.sort(key=lambda t: (t.concluida, t.prazo is None, t.prazo or date.max,
                                ordem_prioridade.index(t.prioridade)))

    return render_template('index.html', nome_aluno=NOME_ALUNO, materias=materias,
                           tarefas=tarefas, resumo=resumo, status=status, STATUS=STATUS,
                           materia_id=materia_id, busca=busca, hoje=date.today(),
                           pendentes_por_materia=pendentes_por_materia)


@app.post('/materias')
def nova_materia():
    nome = request.form.get('nome', '').strip()
    if not nome or len(nome) > 100:
        flash('Informe um nome de matéria com até 100 caracteres.', 'erro')
    elif Materia.query.filter(db.func.lower(Materia.nome) == nome.lower()).first():
        flash(f'A matéria "{nome}" já existe.', 'erro')
    else:
        db.session.add(Materia(nome=nome))
        db.session.commit()
        flash(f'Matéria "{nome}" adicionada.', 'ok')
    return redirect(url_for('index'))


@app.post('/materias/<int:id>/excluir')
def excluir_materia(id):
    materia = db.get_or_404(Materia, id)
    qtd = len(materia.tarefas)
    db.session.delete(materia)
    db.session.commit()
    flash(f'Matéria "{materia.nome}" excluída' + (f' junto com {qtd} tarefa(s).' if qtd else '.'), 'ok')
    return redirect(url_for('index'))


@app.post('/tarefas')
def nova_tarefa():
    dados, erro = ler_tarefa(request.form)
    if erro:
        flash(erro, 'erro')
    else:
        db.session.add(Tarefa(**dados))
        db.session.commit()
        flash('Tarefa adicionada.', 'ok')
    return voltar()


@app.route('/tarefas/<int:id>/editar', methods=['GET', 'POST'])
def editar_tarefa(id):
    tarefa = db.get_or_404(Tarefa, id)
    if request.method == 'POST':
        dados, erro = ler_tarefa(request.form)
        if erro:
            flash(erro, 'erro')
        else:
            for campo, valor in dados.items():
                setattr(tarefa, campo, valor)
            db.session.commit()
            flash('Tarefa atualizada.', 'ok')
            return redirect(url_for('index'))
    materias = Materia.query.order_by(Materia.nome).all()
    return render_template('editar.html', t=tarefa, materias=materias)


@app.post('/tarefas/<int:id>/alternar')
def alternar_tarefa(id):
    tarefa = db.get_or_404(Tarefa, id)
    tarefa.concluida = not tarefa.concluida
    db.session.commit()
    return voltar()


@app.post('/tarefas/<int:id>/excluir')
def excluir_tarefa(id):
    db.session.delete(db.get_or_404(Tarefa, id))
    db.session.commit()
    flash('Tarefa excluída.', 'ok')
    return voltar()


if __name__ == '__main__':
    app.run(debug=True)
