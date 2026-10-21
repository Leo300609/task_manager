# EduTrack

Gerenciador de tarefas escolares: cadastre matérias e, dentro delas, tarefas com prazo e prioridade.

## Rodar

```bash
python -m venv venv
venv\Scripts\activate        # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
python app.py                # http://127.0.0.1:5000
```

## Testes

```bash
python -m unittest test_app -v
```

## O que tem

- Matérias (nome único) e tarefas (título, descrição, prazo, prioridade, concluída).
- Painel com totais, atrasadas e barra de progresso.
- Filtro por matéria, status e busca por título; tarefas ordenadas por pendência, prazo e prioridade.
- Alterações só via POST com token CSRF; exclusões pedem confirmação.

## Configuração (variáveis de ambiente)

| Variável | Para quê |
| --- | --- |
| `SECRET_KEY` | Chave da sessão/CSRF. **Defina antes de publicar na internet.** |
| `EDUTRACK_DB` | URI do banco (padrão: `edutrack.db` ao lado do `app.py`). |

## Próximos passos possíveis

- Login e várias contas (hoje o nome "Léo" é fixo em `NOME_ALUNO`).
- Migrações com Flask-Migrate se o modelo mudar (hoje `create_all` só cria tabelas novas).
- Visão de calendário e lembretes.
