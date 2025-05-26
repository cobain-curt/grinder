from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-me')

# Конфигурация базы данных (SQLite или URL из .env для PostgreSQL)
basedir = os.path.abspath(os.path.dirname(__file__))
db_uri = os.getenv('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель для хранения сообщений
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, nullable=False)
    user_name = db.Column(db.String)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    replied = db.Column(db.Boolean, default=False)
    reply_text = db.Column(db.Text)
    replied_at = db.Column(db.DateTime)

# Настройка Telegram Bot API
BOT_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

def send_message(chat_id, text):
    """Отправка текстового сообщения пользователю через Telegram API."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    try:
        res = requests.get(url, params=payload)
        return res.json()
    except Exception as e:
        print('Failed to send message:', e)

@app.route('/')
def index():
    return 'Bot is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик входящих запросов от Telegram (Webhook)."""
    data = request.get_json()
    if not data:
        return jsonify({'status': 'no data'})
    if 'message' in data:
        message = data['message']
        chat_id = message['chat']['id']
        user = message['from']
        user_name = user.get('username') or f"{user.get('first_name','')} {user.get('last_name','')}"
        text = message.get('text', '')
        # Сохраняем входящее сообщение в базу
        msg = Message(user_id=str(chat_id), user_name=user_name, text=text)
        db.session.add(msg)
        db.session.commit()
        # Здесь можно добавлять логику ответа ботом (например, с помощью ChatGPT)
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'no message'})

# Простой механизм авторизации администратора
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'password')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Неверные учётные данные')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

def login_required(f):
    """Декоратор проверки логина для защищённых маршрутов админа."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@login_required
def dashboard():
    """Список всех входящих сообщений (панель администратора)."""
    messages = Message.query.order_by(Message.timestamp.desc()).all()
    return render_template('dashboard.html', messages=messages)

@app.route('/message/<int:message_id>', methods=['GET', 'POST'])
@login_required
def message_detail(message_id):
    """Просмотр конкретного сообщения и отправка ответа."""
    msg = Message.query.get_or_404(message_id)
    if request.method == 'POST':
        reply_text = request.form.get('reply')
        # Отправка ответа пользователю через Telegram
        send_message(msg.user_id, reply_text)
        # Обновляем запись в базе данных
        msg.replied = True
        msg.reply_text = reply_text
        msg.replied_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('message_detail.html', msg=msg)

@app.route('/stats')
@login_required
def stats():
    """
    Пример отображения статической страницы с графиками.
    (В папке static/ могут быть картинки, например из аналитики.)
    """
    return render_template('stats.html')


