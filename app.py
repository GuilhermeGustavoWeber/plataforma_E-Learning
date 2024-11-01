from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import PickleType
from io import BytesIO

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
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    duracao = db.Column(db.Integer, nullable=False)  # em horas
    instrutor = db.Column(db.String(100), nullable=False)
    aulas = db.relationship('Aula', backref='curso', lazy=True)

class Aula(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id'), nullable=False)


class Inscricao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    curso_id = db.Column(db.Integer, db.ForeignKey('curso.id'))
    progresso = db.Column(db.Float, default=0)
    aulas_completadas = db.Column(MutableList.as_mutable(PickleType), default=[])  # Armazena os IDs das aulas como uma lista


class AulaCompleta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inscricao_id = db.Column(db.Integer, db.ForeignKey('inscricao.id'))
    aula_id = db.Column(db.Integer, db.ForeignKey('aula.id'))


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


@app.route('/curso/conteudo/<int:curso_id>')
@login_required
def conteudo_curso(curso_id):
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, curso_id=curso_id).first()
    curso = Curso.query.get_or_404(curso_id)

    # Verifique se o usuário está inscrito
    if not inscricao:
        flash("Você precisa se inscrever no curso para acessar o conteúdo.")
        return redirect(url_for('detalhes_curso', curso_id=curso_id))

    return render_template("conteudo_curso.html", curso=curso, inscrito=True)


@app.route('/video_aula/<int:aula_id>', methods=['GET', 'POST'])
@login_required
def video_aula(aula_id):
    aula = Aula.query.get_or_404(aula_id)
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, curso_id=aula.curso_id).first()

    # Verifique se a inscrição existe
    if inscricao is None:
        # Aqui você pode decidir o que fazer se a inscrição não existir
        # Por exemplo, redirecionar para uma página de erro ou exibir uma mensagem
        flash("Você não está inscrito neste curso.", "danger")
        return redirect(url_for('detalhes_curso', curso_id=aula.curso_id))

    return render_template("video_aula.html", aula=aula, inscricao=inscricao)  # Passando a inscrição para o template


@app.route('/curso/<int:curso_id>')
@login_required
def detalhes_curso(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, curso_id=curso.id).first()
    aulas = Aula.query.filter_by(curso_id=curso.id).all()  # Obter todas as aulas do curso
    return render_template("detalhes_curso.html", curso=curso, inscricao=inscricao, aulas=aulas)


@app.route('/completar_aula/<int:aula_id>', methods=['POST'])
@login_required
def completar_aula(aula_id):
    # Buscando a aula pelo ID
    aula = Aula.query.get_or_404(aula_id)

    # Verifica se a aula existe
    if not aula:
        flash('A aula não foi encontrada.')
        return redirect(url_for('alguma_rota'))  # Redirecione para uma rota apropriada

    # Buscando a inscrição do usuário
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, curso_id=aula.curso_id).first()

    # Verifica se a inscrição existe
    if inscricao:
        # Garantindo que aulas_completadas seja uma lista vazia se for None
        aulas_completadas = inscricao.aulas_completadas if inscricao.aulas_completadas else []

        # Adiciona a aula atual à lista de aulas completadas se ainda não estiver lá
        if aula.id not in aulas_completadas:
            aulas_completadas.append(aula.id)
            inscricao.aulas_completadas = aulas_completadas  # Atualiza a inscrição

            # Calculando o total de aulas do curso
            curso = Curso.query.get(aula.curso_id)  # Buscando o curso associado à aula
            total_aulas = len(curso.aulas)  # Contando o número total de aulas no curso

            # Atualiza o progresso
            inscricao.progresso = (len(aulas_completadas) / total_aulas) * 100

            db.session.commit()  # Salva as alterações no banco de dados

            # Verifique se o número de aulas completadas é menor que o total de aulas
            if len(aulas_completadas) < total_aulas:
                flash('Aula completada com sucesso!')
            else:
                flash('Você completou todas as aulas do curso!')
        else:
            flash('Esta aula já foi completada.')

    return redirect(url_for('video_aula', aula_id=aula_id))  # Redireciona para a aula


@app.route('/reverter_aula/<int:aula_id>', methods=["POST"])
@login_required
def reverter_aula(aula_id):
    aula = Aula.query.get_or_404(aula_id)
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, curso_id=aula.curso_id).first()

    if inscricao:
        # Calcular o novo progresso baseado no número de aulas
        total_aulas = Aula.query.filter_by(curso_id=aula.curso_id).count()
        aulas_completadas = inscricao.aulas_completadas  # Usar a coluna de aulas completadas

        # Decrementar o número de aulas completadas e atualizar o progresso
        if aulas_completadas > 0:
            aulas_completadas -= 1
            inscricao.aulas_completadas = aulas_completadas
            inscricao.progresso = (aulas_completadas / total_aulas) * 100
            db.session.commit()
            flash("Aula revertida com sucesso!")

    return redirect(url_for('detalhes_curso', curso_id=aula.curso_id))


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


@app.route('/certificado/<int:curso_id>')
@login_required
def gerar_certificado(curso_id):
    inscricao = Inscricao.query.filter_by(usuario_id=current_user.id, curso_id=curso_id).first()

    if inscricao and inscricao.progresso >= 100:
        # Cria um objeto BytesIO para o PDF
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "Certificado de Conclusão")
        c.drawString(100, 725, f"Este certificado é concedido a {current_user.nome}")
        c.drawString(100, 700, f"Concluiu o curso: {Curso.query.get(curso_id).nome}")
        c.save()
        buffer.seek(0)  # Move o ponteiro para o início do buffer

        # Define o nome do arquivo para download
        filename = f"certificado_{current_user.id}_{curso_id}.pdf"
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

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


@app.context_processor
def inject_year():
    return {'year': datetime.now().year}


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.run(debug=True)
