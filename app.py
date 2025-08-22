from flask import Flask, render_template, url_for, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin, LoginManager, login_required, current_user, login_user, logout_user
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
db = SQLAlchemy(app)
app.app_context().push()
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # папка для картинок
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # обмеження 2Мб
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Articles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    intro = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now)
    image = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return '<Article %r>' % self.id
    

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    def check_password(self, password):
        return self.password == password

    def __repr__(self):
        return '<User %r>' % self.id


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.role == "admin":
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or '/')
        else:
            return "Access denied"

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


@app.route('/')
@app.route('/home')
def index():
    return render_template("index.html")


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/posts')
def posts():
    articles = Articles.query.order_by(Articles.date.desc()).all()
    return render_template("posts.html", articles=articles)


@app.route('/posts/<int:id>')
def post_detail(id):
    article = Articles.query.get(id)
    return render_template("post_detail.html", article=article)


@app.route('/posts/<int:id>/del')
def post_delete(id):
    article = Articles.query.get_or_404(id)
    try:
        db.session.delete(article)
        db.session.commit()
        return redirect('/posts')
    except Exception:
        return 'Виникла помилка при видаленні статті'
    

@app.route('/posts/<int:id>/image-delete')
def image_delete(id):
    image_del = Articles.query.get_or_404(id)
    if image_del:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_del.image)
        if os.path.exists(image_path):
            os.remove(image_path)
    image_del.image = None
    try:
        db.session.commit()
        return redirect(url_for('post_update', id=id))
    except Exception:
        return 'Виникла помилка при видаленні зображення'


@app.route('/posts/<int:id>/update', methods=['POST', 'GET'])
def post_update(id):
    article = Articles.query.get(id)
    if request.method == 'POST':
        article.title = request.form.get('title')
        article.intro = request.form.get('intro')
        article.text = request.form.get('text')
        # робота з файлом
        image_file = request.files.get('image')
        if image_file and image_file.filename != '' and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            article.image = filename
        try:
            db.session.commit()
            return redirect('/posts')
        except Exception:
            return 'Виникла помилка при редагуванні статті'
    else:
        return render_template("post_update.html", article=article)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/create-article', methods=['POST', 'GET'])
@login_required
def create_article():
    if request.method == 'POST':
        title = request.form['title']
        intro = request.form['intro']
        text = request.form['text']
        # робота з файлом
        image_file = request.files.get('image')
        image_filename = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename  # шлях відносно static/
        article = Articles(title=title, intro=intro, text=text, image=image_filename)
        try:
            db.session.add(article)
            db.session.commit()
            return redirect('/posts')
        except Exception:
            return 'Виникла помилка при додаванні статті'
    else:
        return render_template("create-article.html")
    

@app.route('/admin')
def admin():
    return render_template("admin.html")


if __name__ == "__main__":
    app.run(debug=True)
