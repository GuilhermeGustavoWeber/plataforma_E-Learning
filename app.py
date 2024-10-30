from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = "super secret key"

# Configurar o banco de dados SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cursos.sqlite3"
db = SQLAlchemy(app)

# Configurar o Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50))
    email = db.Column(db.String(100), unique=True)
    senha = db.Column(db.String(100))
    cursos_inscritos = db.relationship('Inscricao', backref='usuario')

class Curso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50))
    descricao = db.Column(db.String(100))
    duracao = db.Column(db.Integer)  # Duração em horas
    instrutor = db.Column(db.String(50))
    conteudo = db.Column(db.Text)  # Conteúdo do curso
    inscricoes = db.relationship('Inscricao', backref='curso')

class Inscricao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id'))
    progresso = db.Column(db.Float, default=0.0)

class Avaliacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    nota = db.Column(db.Float)
    comentario = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/catalogo')
def catalogo_cursos():
    cursos = Curso.query.all()  # Obtém todos os cursos do banco de dados
    return render_template("catalogo.html", cursos=cursos)  # Renderiza o template com os cursos

@app.route('/inscrever/<int:curso_id>', methods=["POST"])
@login_required
def inscrever_curso(curso_id):
    usuario_id = current_user.id  # Obtendo o ID do usuário autenticado
    nova_inscricao = Inscricao(usuario_id=usuario_id, curso_id=curso_id)
    db.session.add(nova_inscricao)
    db.session.commit()
    flash("Inscrição realizada com sucesso!")
    return redirect(url_for('catalogo_cursos'))

@app.route('/curso/<int:curso_id>')
def detalhes_curso(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    return render_template("detalhes_curso.html", curso=curso)

@app.route('/progresso/<int:curso_id>')
@login_required
def progresso_curso(curso_id):
    usuario_id = current_user.id  # Obtendo o ID do usuário autenticado
    inscricao = Inscricao.query.filter_by(usuario_id=usuario_id, curso_id=curso_id).first()
    return render_template("progresso.html", inscricao=inscricao)

@app.route('/avaliar/<int:curso_id>', methods=["POST"])
@login_required
def avaliar_curso(curso_id):
    usuario_id = current_user.id  # Obtendo o ID do usuário autenticado
    nota = request.form.get("nota")
    comentario = request.form.get("comentario")
    avaliacao = Avaliacao(curso_id=curso_id, usuario_id=usuario_id, nota=nota, comentario=comentario)
    db.session.add(avaliacao)
    db.session.commit()
    flash("Avaliação enviada com sucesso!")
    return redirect(url_for('detalhes_curso', curso_id=curso_id))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Cria todas as tabelas se não existirem
    app.run(debug=True)
