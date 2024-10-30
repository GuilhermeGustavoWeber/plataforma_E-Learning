from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "super secret key"

# Configurar o banco de dados SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cursos.sqlite3"
db = SQLAlchemy(app)

# Configurar o LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Modelos do banco de dados
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


# Rotas da aplicação
@app.route('/')
def index():
    return render_template("index.html")


@app.route('/cursos')
def lista_cursos():
    cursos = Curso.query.all()
    return render_template("cursos.html", cursos=cursos)


@app.route('/inscrever/<int:curso_id>', methods=["POST"])
@login_required
def inscrever_curso(curso_id):
    nova_inscricao = Inscricao(usuario_id=current_user.id, curso_id=curso_id)
    db.session.add(nova_inscricao)
    db.session.commit()
    flash("Inscrição realizada com sucesso!")
    return redirect(url_for('lista_cursos'))


@app.route('/curso/<int:curso_id>')
def detalhes_curso(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    return render_template("detalhes_curso.html", curso=curso)


@app.route('/progresso/<int:curso_id>', methods=["POST"])
@login_required
def atualizar_progresso(curso_id):
    progresso = request.form.get("progresso")
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, curso_id=curso_id).first()
    if inscricao:
        inscricao.progresso = float(progresso)
        db.session.commit()
        flash("Progresso atualizado com sucesso!")
    return redirect(url_for('detalhes_curso', curso_id=curso_id))


@app.route('/teste/<int:curso_id>', methods=["GET", "POST"])
@login_required
def teste_curso(curso_id):
    if request.method == "POST":
        nota = request.form.get("nota")
        comentario = request.form.get("comentario")
        avaliacao = Avaliacao(curso_id=curso_id, usuario_id=current_user.id, nota=nota, comentario=comentario)
        db.session.add(avaliacao)
        db.session.commit()
        flash("Teste realizado com sucesso!")
        return redirect(url_for('detalhes_curso', curso_id=curso_id))

    return render_template("teste.html", curso_id=curso_id)


@app.route('/certificado/<int:curso_id>')
@login_required
def gerar_certificado(curso_id):
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, curso_id=curso_id).first()

    if inscricao and inscricao.progresso >= 100:
        caminho_certificado = f"certificados/certificado_{current_user.id}_{curso_id}.pdf"
        c = canvas.Canvas(caminho_certificado, pagesize=letter)
        c.drawString(100, 750, "Certificado de Conclusão")
        c.drawString(100, 725, f"Este certificado é concedido a {current_user.nome}")
        c.drawString(100, 700, f"Concluiu o curso: {Curso.query.get(curso_id).nome}")
        c.save()

        return send_file(caminho_certificado, as_attachment=True)

    flash("Você deve completar o curso antes de obter o certificado.")
    return redirect(url_for('detalhes_curso', curso_id=curso_id))


@app.route('/feedback/<int:curso_id>', methods=["POST"])
@login_required
def feedback_curso(curso_id):
    comentario = request.form.get("comentario")
    avaliacao = Avaliacao(curso_id=curso_id, usuario_id=current_user.id, comentario=comentario)
    db.session.add(avaliacao)
    db.session.commit()
    flash("Feedback enviado com sucesso!")
    return redirect(url_for('detalhes_curso', curso_id=curso_id))


# Rotas para login e registro de usuário
@app.route('/registrar', methods=["GET", "POST"])
def registrar():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        novo_usuario = Usuario(nome=nome, email=email, senha=senha)
        db.session.add(novo_usuario)
        db.session.commit()

        flash("Registro realizado com sucesso! Você pode se inscrever em cursos agora.")
        return redirect(url_for('index'))

    return render_template("registrar.html")


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(email=email, senha=senha).first()

        if usuario:
            login_user(usuario)
            flash("Login realizado com sucesso!")
            return redirect(url_for('index'))
        else:
            flash("Credenciais inválidas. Tente novamente.")

    return render_template("login.html")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logout realizado com sucesso!")
    return redirect(url_for('index'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.run(debug=True)
