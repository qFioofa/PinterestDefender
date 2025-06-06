import os
import sqlite3
import uuid
import logging
import argon2
from werkzeug import Response
from pDataBase import pDataBase
from flask import Flask, render_template, request, redirect, url_for, session, url_for
from werkzeug.datastructures.file_storage import FileStorage
from werkzeug.utils import secure_filename

class PasswordHasher:
    def __init__(self, time_cost=2, memory_cost=102400, parallelism=8, hash_len=64, salt_len=32):
        self.time_cost = time_cost
        self.memory_cost = memory_cost
        self.parallelism = parallelism
        self.hash_len = hash_len
        self.salt_len = salt_len
        self.hasher = argon2.PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len
        )

    def hash_password(self, password: str) -> str:
        return self.hasher.hash(password.encode('utf-8'))

    def verify_password(self, hashed_password: str, password: str) -> bool:
        try:
            return self.hasher.verify(hashed_password, password.encode('utf-8'))
        except (argon2.exceptions.VerifyMismatchError,
                argon2.exceptions.VerificationError,
                argon2.exceptions.InvalidHash):
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        return self.hasher.check_needs_rehash(hashed_password)

PASSWORD_HASHER = PasswordHasher()

class pFiles:
    @staticmethod
    def allowed_file(filename: str, ALLOWED_EXTENSIONS: set[str] = {'png', 'jpg', 'jpeg', 'gif'}) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class appWrapper:
    app = Flask(__name__)

    @staticmethod
    def init(secret_key: str = "__secret_key__", upload_folder: str = "static/uploads") -> None:
        appWrapper.app.secret_key = os.environ.get('SECRET_KEY', secret_key)
        appWrapper.app.config['UPLOAD_FOLDER'] = os.path.join(
            appWrapper.app.root_path, upload_folder
        )
        appWrapper.app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
        appWrapper.app.config['PASSWORD_HASHER'] = PASSWORD_HASHER
        os.makedirs(appWrapper.app.config['UPLOAD_FOLDER'], exist_ok=True)

class pServer:
    @staticmethod
    def run(debug: bool = False) -> None:
        appWrapper.app.run(debug=debug)

    @staticmethod
    def get_app() -> Flask | None:
        return appWrapper.app

    @appWrapper.app.route('/')
    @staticmethod
    def index(html_file: str = "index.html") -> str:
        try:
            with pDataBase.get_db_connection() as conn:
                posts: list = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
            return render_template(html_file, posts=posts)
        except sqlite3.Error as e:
            logging.error(f"Database error: {str(e)}")
            return render_template("error.html", message="Error loading posts"), 500

    @appWrapper.app.route('/register', methods=['GET', 'POST'])
    @staticmethod
    def register(html_file: str = "register.html") -> Response | str:
        hasher = appWrapper.app.config['PASSWORD_HASHER']

        if request.method == 'POST':
            username: str = request.form.get('username', '').strip()
            password: str = request.form.get('password', '').strip()

            if len(username) < 4 or len(password) < 10:
                return render_template(html_file, error="Username must be 4+ chars, password 10+ chars")

            if not any(char.isdigit() for char in password) or \
               not any(char.isupper() for char in password) or \
               not any(char in "!@#$%^&*(),.?\":{}|<>" for char in password):
                return render_template(html_file, error="Password must contain uppercase, number, and special character")

            hashed_password: str = hasher.hash_password(password)

            try:
                with pDataBase.get_db_connection() as conn:
                    conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                                (username, hashed_password))
                    conn.commit()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                return render_template(html_file, error="Username already exists")
            except sqlite3.Error as e:
                logging.error(f"Registration error: {str(e)}")
                return render_template(html_file, error="Registration failed")
        return render_template(html_file)

    @appWrapper.app.route('/login', methods=['GET', 'POST'])
    @staticmethod
    def login(html_file: str = "login.html") -> Response | str:
        hasher = appWrapper.app.config['PASSWORD_HASHER']

        if request.method == 'POST':
            username: str = request.form.get('username', '').strip()
            password: str = request.form.get('password', '').strip()

            try:
                with pDataBase.get_db_connection() as conn:
                    user = conn.execute(
                        'SELECT * FROM users WHERE username = ?',
                        (username,)
                    ).fetchone()

                if user and hasher.verify_password(user['password'], password):
                    if hasher.needs_rehash(user['password']):
                        new_hash = hasher.hash_password(password)
                        with pDataBase.get_db_connection() as conn:
                            conn.execute(
                                'UPDATE users SET password = ? WHERE id = ?',
                                (new_hash, user['id'])
                            )
                            conn.commit()

                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    return redirect(url_for('index'))
                return render_template(html_file, error="Invalid username or password")
            except sqlite3.Error as e:
                logging.error(f"Login error: {str(e)}")
                return render_template(html_file, error="Login failed")
        return render_template(html_file)

    @appWrapper.app.route('/create_post', methods=['GET', 'POST'])
    @staticmethod
    def create_post(html_file: str = "create_post.html") -> Response | str:
        if 'user_id' not in session:
            return redirect(url_for('login'))

        if request.method == 'POST':
            title: str = request.form.get('title', '').strip()
            content: str = request.form.get('content', '').strip()
            author: str = session['username']
            image: FileStorage = request.files.get('image')

            if not title or not content:
                return render_template(html_file, error="Title and content are required")

            image_url = None
            if image and image.filename != '':
                if not pFiles.allowed_file(image.filename):
                    return render_template(html_file, error="Invalid file type")

                ext: str = image.filename.rsplit('.', 1)[1].lower()
                filename: str = f"{uuid.uuid4().hex}.{ext}"
                secure_name: str = secure_filename(filename)
                file_path: str = os.path.join(appWrapper.app.config['UPLOAD_FOLDER'], secure_name)

                image.save(file_path)
                image_url: str = f"uploads/{secure_name}"

            try:
                with pDataBase.get_db_connection() as conn:
                    conn.execute(
                        'INSERT INTO posts (title, content, author, image_url) VALUES (?, ?, ?, ?)',
                        (title, content, author, image_url)
                    )
                    conn.commit()
                return redirect(url_for('index'))
            except sqlite3.Error as e:
                logging.error(f"Post creation error: {str(e)}")
                if image_url:
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
                return render_template(html_file, error="Failed to create post")
        return render_template(html_file)

    @appWrapper.app.route('/logout')
    @staticmethod
    def logout() -> Response:
        session.clear()
        return redirect(url_for('index'))