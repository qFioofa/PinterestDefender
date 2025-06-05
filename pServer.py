import os
import sqlite3
from werkzeug import Response
from pDataBase import pDataBase
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.datastructures.file_storage import FileStorage
from werkzeug.utils import secure_filename

class pFiles:
    @staticmethod
    def allowed_file(filename : str, ALLOWED_EXTENSIONS: set[str] = {'png', 'jpg', 'jpeg', 'gif'}) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class appWrapper:

    app = Flask(__name__)

    @staticmethod
    def init(secret_key  : str = "__secret_key__", upload_folder : str = "static/uploads" ) -> None:
        appWrapper.app.secret_key = secret_key
        print("Inited")
        appWrapper.app.config['UPLOAD_FOLDER'] = upload_folder


class pServer:

    @staticmethod
    def run(debug : bool = False) -> None:
        appWrapper.app.run(debug=debug)

    @staticmethod
    def get_app() -> None | Flask:
        return appWrapper.app

    @appWrapper.app.route('/')
    @staticmethod
    def index(html_file : str = "index.html") -> str:
        conn: sqlite3.Connection = pDataBase.get_db_connection()
        posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
        conn.close()
        return render_template(html_file, posts=posts)


    @appWrapper.app.route('/register', methods=['GET', 'POST'])
    @staticmethod
    def register(html_file : str = "register.html") -> Response | str:
        if request.method == 'POST':
            username: str = request.form['username']
            password: str = request.form['password']

            conn: sqlite3.Connection = pDataBase.get_db_connection()
            try:
                conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                            (username, password))
                conn.commit()
            finally:
                conn.close()
            return redirect(url_for('login'))
        return render_template(html_file)


    @appWrapper.app.route('/login', methods=['GET', 'POST'])
    @staticmethod
    def login(html_file : str = "login.html") -> Response | str:
        if request.method == 'POST':
            username: str = request.form['username']
            password: str = request.form['password']

            conn: sqlite3.Connection = pDataBase.get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ?',
                                (username,)
                        ).fetchone()
            conn.close()

            if user and user['password'] == password:
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('index'))
            else:
                return "Неверный логин или пароль"
        return render_template(html_file)

    @appWrapper.app.route('/create_post', methods=['GET', 'POST'])
    @staticmethod
    def create_post(html_file : str = "create_post.html") -> Response | str:
        if 'user_id' not in session:
            return redirect(url_for('login'))

        if request.method == 'POST':
            title: str = request.form['title']
            content: str = request.form['content']
            author = session['username']
            image: FileStorage = request.files['image']

            image_url = None
            if image and pFiles.allowed_file(image.filename):
                filename: str = secure_filename(image.filename)
                image.save(os.path.join(appWrapper.app.config['UPLOAD_FOLDER'], filename))
                image_url: str = f"uploads/{filename}"

            conn: sqlite3.Connection = pDataBase.get_db_connection()
            try:
                conn.execute('INSERT INTO posts (title, content, author, image_url) VALUES (?, ?, ?, ?)',
                            (title, content, author, image_url))
                conn.commit()
            finally:
                conn.close()
            return redirect(url_for('index'))

        return render_template(html_file)

    @appWrapper.app.route('/logout')
    @staticmethod
    def logout() -> Response:
        session.clear()
        return redirect(url_for('index'))