import os
import re
import unittest
from datetime import date, timedelta

os.environ['EDUTRACK_DB'] = 'sqlite:///:memory:'  # antes do import: não toca no edutrack.db real

from app import Materia, Tarefa, app, db  # noqa: E402


class EduTrackTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        with app.app_context():
            db.drop_all()
            db.create_all()
        self.c = app.test_client()
        self.token = re.search(r'name="csrf_token" value="(\w+)"', self.c.get('/').text).group(1)

    def post(self, url, **dados):
        return self.c.post(url, data={'csrf_token': self.token, **dados}, follow_redirects=True)

    def materia(self, nome='PW3'):
        self.post('/materias', nome=nome)
        with app.app_context():
            return Materia.query.filter_by(nome=nome).one().id

    def tarefa(self, mid, **extra):
        dados = {'titulo': 'Trabalho', 'materia_id': mid, 'prioridade': 'media', **extra}
        return self.post('/tarefas', **dados)

    def test_post_sem_csrf_e_rejeitado(self):
        self.assertEqual(self.c.post('/materias', data={'nome': 'X'}).status_code, 400)

    def test_materia_duplicada_ou_vazia(self):
        self.materia('PW3')
        self.assertIn('já existe', self.post('/materias', nome='pw3').text)
        self.assertIn('Informe um nome', self.post('/materias', nome='  ').text)
        with app.app_context():
            self.assertEqual(Materia.query.count(), 1)

    def test_ciclo_da_tarefa(self):
        mid = self.materia()
        self.assertIn('Trabalho', self.tarefa(mid).text)
        with app.app_context():
            tid = Tarefa.query.one().id
        self.post(f'/tarefas/{tid}/alternar')
        with app.app_context():
            self.assertTrue(db.session.get(Tarefa, tid).concluida)
        self.post(f'/tarefas/{tid}/editar', titulo='Novo', materia_id=mid, prioridade='alta')
        with app.app_context():
            self.assertEqual(db.session.get(Tarefa, tid).titulo, 'Novo')
        self.post(f'/tarefas/{tid}/excluir')
        with app.app_context():
            self.assertEqual(Tarefa.query.count(), 0)

    def test_validacao_da_tarefa(self):
        mid = self.materia()
        self.assertIn('título', self.tarefa(mid, titulo=' ').text)
        self.assertIn('Prioridade inválida', self.tarefa(mid, prioridade='x').text)
        self.assertIn('Data inválida', self.tarefa(mid, prazo='32/13/2026').text)
        self.assertIn('matéria válida', self.tarefa(999).text)
        with app.app_context():
            self.assertEqual(Tarefa.query.count(), 0)

    def test_atrasada_e_filtros(self):
        mid = self.materia()
        ontem = (date.today() - timedelta(days=1)).isoformat()
        self.tarefa(mid, titulo='Velha', prazo=ontem)
        self.tarefa(mid, titulo='Recente')
        html = self.c.get('/?status=atrasadas').text
        self.assertIn('Velha', html)
        self.assertNotIn('Recente', html)
        self.assertIn('Recente', self.c.get('/?q=rece').text)

    def test_excluir_materia_leva_as_tarefas(self):
        mid = self.materia()
        self.tarefa(mid)
        self.post(f'/materias/{mid}/excluir')
        with app.app_context():
            self.assertEqual(Tarefa.query.count(), 0)

    def test_voltar_ignora_url_externa(self):
        mid = self.materia()
        r = self.c.post('/tarefas', data={'csrf_token': self.token, 'titulo': 'T', 'materia_id': mid,
                                          'voltar': '//evil.com'})
        self.assertEqual(r.headers['Location'], '/')

    def test_excluir_por_get_nao_existe(self):
        self.assertEqual(self.c.get('/tarefas/1/excluir').status_code, 405)


if __name__ == '__main__':
    unittest.main()
