from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    lista_materias = ['PW3', 'Inglês', 'Português', 'Geografia', 'Banco de Dados']
    return render_template('index.html', nome_aluno = 'Leonardo', materias = lista_materias) 

if __name__ == '__main__':
    app.run(debug=True)
