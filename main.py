from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
import subprocess
import sys


try:
    import email_validator
except ImportError:
    print("Установка email_validator...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "email-validator"])
    import email_validator

    print("email_validator успешно установлен!")

from wtforms.validators import Email


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cookbook.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recipes = db.relationship('Recipe', backref='author', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Recipe(db.Model):
    __tablename__ = 'recipes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    cooking_time = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<Recipe {self.title}>'


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя',
                           validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Пароль',
                             validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class RecipeForm(FlaskForm):
    title = StringField('Название рецепта', validators=[DataRequired()])
    description = TextAreaField('Краткое описание', validators=[DataRequired()])
    ingredients = TextAreaField('Ингредиенты (каждый с новой строки)',
                                validators=[DataRequired()])
    instructions = TextAreaField('Инструкция приготовления',
                                 validators=[DataRequired()])
    cooking_time = IntegerField('Время приготовления (минуты)',
                                validators=[DataRequired()])
    category = SelectField('Категория',
                           choices=[
                               ('breakfast', ' Завтрак'),
                               ('lunch', ' Обед'),
                               ('dinner', ' Ужин'),
                               ('dessert', ' Десерт'),
                               ('salad', ' Салат'),
                               ('soup', ' Супы'),
                               ('baking', ' Выпечка'),
                               ('drinks', ' Напитки'),
                               ('appetizer', ' Закуски'),
                               ('sauce', ' Соусы')
                           ],
                           validators=[DataRequired()])
    submit = SubmitField('Сохранить рецепт')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if current_user.is_authenticated:
        recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.created_at.desc()).all()
    else:
        recipes = []
    return render_template('index.html', recipes=recipes)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'С возвращением, {user.username}! ', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Неверный email или пароль', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы. До свидания! ', 'info')
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@app.route('/recipe/new', methods=['GET', 'POST'])
@login_required
def new_recipe():
    form = RecipeForm()
    if form.validate_on_submit():
        recipe = Recipe(
            title=form.title.data,
            description=form.description.data,
            ingredients=form.ingredients.data,
            instructions=form.instructions.data,
            cooking_time=form.cooking_time.data,
            category=form.category.data,
            user_id=current_user.id
        )
        db.session.add(recipe)
        db.session.commit()
        flash(' Рецепт успешно добавлен!', 'success')
        return redirect(url_for('index'))
    return render_template('recipe_form.html', form=form, title='Добавить рецепт')


@app.route('/recipe/<int:recipe_id>')
def view_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if current_user.is_authenticated and recipe.user_id != current_user.id:
        flash('У вас нет доступа к этому рецепту', 'danger')
        return redirect(url_for('index'))
    elif not current_user.is_authenticated:
        flash('Пожалуйста, войдите для просмотра рецептов', 'info')
        return redirect(url_for('login'))
    ingredients_list = recipe.ingredients.split('\n')
    return render_template('recipe_detail.html', recipe=recipe, ingredients=ingredients_list)


@app.route('/recipe/<int:recipe_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
        flash('У вас нет прав для редактирования этого рецепта', 'danger')
        return redirect(url_for('index'))
    form = RecipeForm(obj=recipe)
    if form.validate_on_submit():
        recipe.title = form.title.data
        recipe.description = form.description.data
        recipe.ingredients = form.ingredients.data
        recipe.instructions = form.instructions.data
        recipe.cooking_time = form.cooking_time.data
        recipe.category = form.category.data
        db.session.commit()
        flash(' Рецепт успешно обновлен!', 'success')
        return redirect(url_for('view_recipe', recipe_id=recipe.id))
    return render_template('recipe_form.html', form=form, title='Редактировать рецепт')


@app.route('/recipe/<int:recipe_id>/delete', methods=['POST'])
@login_required
def delete_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id:
        flash('У вас нет прав для удаления этого рецепта', 'danger')
        return redirect(url_for('index'))
    db.session.delete(recipe)
    db.session.commit()
    flash(' Рецепт успешно удален!', 'success')
    return redirect(url_for('index'))


@app.route('/search')
def search():
    query = request.args.get('q', '')
    if current_user.is_authenticated and query:
        recipes = Recipe.query.filter(
            Recipe.user_id == current_user.id,
            Recipe.title.ilike(f'%{query}%')
        ).order_by(Recipe.created_at.desc()).all()
    elif current_user.is_authenticated:
        recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.created_at.desc()).all()
    else:
        recipes = []
    return render_template('index.html', recipes=recipes, search_query=query)

BASE_TEMPLATE = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title> Моя Кулинарная Книга</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #ff6b6b;
            --secondary-color: #4ecdc4;
            --accent-color: #ffe66d;
            --dark-color: #2d3436;
            --light-color: #f9f9f9;
        }

        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: var(--dark-color);
        }

        .navbar {
            background: rgba(255, 255, 255, 0.95) !important;
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
        }

        .navbar-brand {
            font-weight: 700;
            font-size: 1.5rem;
            color: var(--primary-color) !important;
        }

        .nav-link {
            font-weight: 500;
            color: var(--dark-color) !important;
            transition: all 0.3s ease;
        }

        .nav-link:hover {
            color: var(--primary-color) !important;
            transform: translateY(-2px);
        }

        .main-content {
            padding: 2rem 0;
        }

        .card {
            border: none;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
        }

        .card:hover {
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        }

        .recipe-card {
            position: relative;
            cursor: pointer;
        }

        .recipe-card .card-body {
            padding: 1.5rem;
        }

        .category-badge {
            position: absolute;
            top: 1rem;
            right: 1rem;
            padding: 0.5rem 1rem;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 600;
            background: var(--primary-color);
            color: white;
            box-shadow: 0 4px 10px rgba(255,107,107,0.3);
        }

        .btn-custom {
            border-radius: 50px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
            border: none;
        }

        .btn-primary-custom {
            background: var(--primary-color);
            color: white;
        }

        .btn-primary-custom:hover {
            background: #ff5252;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255,107,107,0.4);
        }

        .btn-outline-custom {
            background: transparent;
            border: 2px solid var(--primary-color);
            color: var(--primary-color);
        }

        .btn-outline-custom:hover {
            background: var(--primary-color);
            color: white;
            transform: translateY(-2px);
        }

        .form-control, .form-select {
            border-radius: 15px;
            border: 2px solid #e0e0e0;
            padding: 0.75rem 1rem;
            transition: all 0.3s ease;
        }

        .form-control:focus, .form-select:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 0.2rem rgba(255,107,107,0.25);
        }

        .alert {
            border-radius: 15px;
            border: none;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        .hero-section {
            text-align: center;
            padding: 3rem 0;
            color: white;
        }

        .hero-title {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }

        .hero-subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 1.5rem;
            text-align: center;
            color: white;
            transition: all 0.3s ease;
        }

        .stat-card:hover {
            transform: translateY(-5px);
            background: rgba(255,255,255,0.2);
        }

        .stat-number {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        .stat-label {
            font-size: 0.9rem;
            opacity: 0.8;
        }

        .empty-state {
            text-align: center;
            padding: 4rem 2rem;
        }

        .empty-state i {
            font-size: 5rem;
            color: var(--primary-color);
            margin-bottom: 1rem;
        }

        .empty-state h3 {
            margin-bottom: 1rem;
            color: var(--dark-color);
        }

        .empty-state p {
            color: #666;
            margin-bottom: 2rem;
        }

        .floating-action-btn {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: var(--primary-color);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            box-shadow: 0 5px 20px rgba(255,107,107,0.4);
            transition: all 0.3s ease;
            z-index: 1000;
        }

        .floating-action-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 8px 25px rgba(255,107,107,0.5);
            color: white;
        }

        .ingredient-list {
            list-style: none;
            padding: 0;
        }

        .ingredient-list li {
            padding: 0.5rem 0;
            border-bottom: 1px dashed #e0e0e0;
            display: flex;
            align-items: center;
        }

        .ingredient-list li:before {
            content: "•";
            color: var(--primary-color);
            font-weight: bold;
            margin-right: 0.5rem;
        }

        .instruction-step {
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            position: relative;
            padding-left: 3rem;
        }

        .instruction-step:before {
            content: counter(step);
            counter-increment: step;
            position: absolute;
            left: 1rem;
            top: 1.5rem;
            width: 24px;
            height: 24px;
            background: var(--primary-color);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .instructions-container {
            counter-reset: step;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .fade-in {
            animation: fadeIn 0.5s ease forwards;
        }

        .time-badge {
            background: var(--secondary-color);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 50px;
            font-size: 0.9rem;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                <i class="bi bi-journal-bookmark-fill"></i> CookBook
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    {% if current_user.is_authenticated %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('new_recipe') }}">
                            <i class="bi bi-plus-circle"></i> Новый рецепт
                        </a>
                    </li>
                    {% endif %}
                </ul>

                <!-- Поиск -->
                <form class="d-flex mx-auto" action="{{ url_for('search') }}" method="GET" style="width: 300px;">
                    <div class="input-group">
                        <input class="form-control" type="search" name="q" placeholder="Поиск рецептов..." value="{{ search_query or '' }}">
                        <button class="btn btn-primary-custom" type="submit">
                            <i class="bi bi-search"></i>
                        </button>
                    </div>
                </form>

                <ul class="navbar-nav ms-auto">
                    {% if current_user.is_authenticated %}
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-bs-toggle="dropdown">
                            <i class="bi bi-person-circle"></i> {{ current_user.username }}
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="{{ url_for('profile') }}">
                                <i class="bi bi-person"></i> Профиль
                            </a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="{{ url_for('logout') }}">
                                <i class="bi bi-box-arrow-right"></i> Выйти
                            </a></li>
                        </ul>
                    </li>
                    {% else %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('login') }}">
                            <i class="bi bi-box-arrow-in-right"></i> Вход
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('register') }}">
                            <i class="bi bi-person-plus"></i> Регистрация
                        </a>
                    </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <div class="container main-content">
        <!-- Flash сообщения -->
        <div class="row">
            <div class="col-12">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }} alert-dismissible fade show fade-in" role="alert">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
            </div>
        </div>

        <!-- Основной контент -->
        {% block content %}{% endblock %}
    </div>

    <!-- Кнопка быстрого добавления -->
    {% if current_user.is_authenticated %}
    <a href="{{ url_for('new_recipe') }}" class="floating-action-btn" title="Добавить рецепт">
        <i class="bi bi-plus-lg"></i>
    </a>
    {% endif %}

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

INDEX_TEMPLATE = '''{% extends "base.html" %}

{% block content %}
{% if not current_user.is_authenticated %}
    <!-- Hero секция для неавторизованных пользователей -->
    <div class="hero-section">
        <h1 class="hero-title"> Моя Кулинарная Книга</h1>
        <p class="hero-subtitle">Сохраняйте любимые рецепты, делитесь с друзьями, готовьте с удовольствием</p>
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="row g-4">
                    <div class="col-md-4">
                        <div class="stat-card">
                            <div class="stat-number"></div>
                            <div class="stat-label">Сохраняйте рецепты</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="stat-card">
                            <div class="stat-number"></div>
                            <div class="stat-label">Легко находите</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="stat-card">
                            <div class="stat-number"></div>
                            <div class="stat-label">Готовьте с удовольствием</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="mt-5">
            <a href="{{ url_for('register') }}" class="btn btn-primary-custom btn-lg me-3">
                <i class="bi bi-person-plus"></i> Начать
            </a>
            <a href="{{ url_for('login') }}" class="btn btn-outline-custom btn-lg">
                <i class="bi bi-box-arrow-in-right"></i> Войти
            </a>
        </div>
    </div>
{% endif %}

{% if current_user.is_authenticated %}
    <div class="row mb-4">
        <div class="col">
            <h2 class="mb-3">
                {% if search_query %}
                     Результаты поиска: "{{ search_query }}"
                {% else %}
                     Мои рецепты
                {% endif %}
            </h2>
        </div>
    </div>

    {% if recipes %}
        <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
            {% for recipe in recipes %}
                <div class="col fade-in" style="animation-delay: {{ loop.index * 0.1 }}s">
                    <div class="card recipe-card h-100">
                        <div class="card-body">
                            <span class="category-badge">
                                {% if recipe.category == 'breakfast' %} Завтрак
                                {% elif recipe.category == 'lunch' %} Обед
                                {% elif recipe.category == 'dinner' %} Ужин
                                {% elif recipe.category == 'dessert' %} Десерт
                                {% elif recipe.category == 'salad' %} Салат
                                {% elif recipe.category == 'soup' %} Супы
                                {% elif recipe.category == 'baking' %} Выпечка
                                {% elif recipe.category == 'drinks' %} Напитки
                                {% elif recipe.category == 'appetizer' %} Закуски
                                {% elif recipe.category == 'sauce' %} Соусы
                                {% endif %}
                            </span>

                            <h4 class="card-title mb-3">{{ recipe.title }}</h4>

                            <p class="card-text text-muted mb-3">
                                {{ recipe.description[:100] }}{% if recipe.description|length > 100 %}...{% endif %}
                            </p>

                            <div class="d-flex align-items-center mb-3">
                                <span class="time-badge me-2">
                                    <i class="bi bi-clock"></i> {{ recipe.cooking_time }} мин
                                </span>
                                <small class="text-muted">
                                    <i class="bi bi-calendar3"></i> {{ recipe.created_at.strftime('%d.%m.%Y') }}
                                </small>
                            </div>

                            <div class="d-flex justify-content-between align-items-center mt-3">
                                <a href="{{ url_for('view_recipe', recipe_id=recipe.id) }}" class="btn btn-primary-custom">
                                    <i class="bi bi-eye"></i> Смотреть
                                </a>
                                <div>
                                    <a href="{{ url_for('edit_recipe', recipe_id=recipe.id) }}" class="btn btn-outline-warning btn-sm me-1" title="Редактировать">
                                        <i class="bi bi-pencil"></i>
                                    </a>
                                    <form action="{{ url_for('delete_recipe', recipe_id=recipe.id) }}" method="POST" class="d-inline">
                                        <button type="submit" class="btn btn-outline-danger btn-sm" 
                                                onclick="return confirm('Вы уверены, что хотите удалить этот рецепт?')"
                                                title="Удалить">
                                            <i class="bi bi-trash"></i>
                                        </button>
                                    </form>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            {% endfor %}
        </div>
    {% else %}
        <div class="empty-state">
            <i class="bi bi-journal-bookmark-fill"></i>
            {% if search_query %}
                <h3>Рецепты не найдены</h3>
                <p>По запросу "{{ search_query }}" ничего не найдено. Попробуйте изменить поиск.</p>
                <a href="{{ url_for('index') }}" class="btn btn-primary-custom">
                    <i class="bi bi-arrow-left"></i> Все рецепты
                </a>
            {% else %}
                <h3>У вас пока нет рецептов</h3>
                <p>Начните собирать свою кулинарную книгу! Добавьте первый рецепт.</p>
                <a href="{{ url_for('new_recipe') }}" class="btn btn-primary-custom btn-lg">
                    <i class="bi bi-plus-circle"></i> Добавить рецепт
                </a>
            {% endif %}
        </div>
    {% endif %}
{% endif %}
{% endblock %}
'''

REGISTER_TEMPLATE = '''{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card fade-in">
            <div class="card-body p-5">
                <div class="text-center mb-4">
                    <i class="bi bi-person-plus-fill" style="font-size: 3rem; color: var(--primary-color);"></i>
                    <h2 class="mt-3">Регистрация</h2>
                    <p class="text-muted">Присоединяйтесь к сообществу любителей готовить!</p>
                </div>

                <form method="POST" action="">
                    {{ form.hidden_tag() }}

                    <div class="mb-3">
                        <label class="form-label">
                            <i class="bi bi-person"></i> {{ form.username.label.text }}
                        </label>
                        {{ form.username(class="form-control" + (" is-invalid" if form.username.errors else ""), placeholder="Введите имя пользователя") }}
                        {% for error in form.username.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="mb-3">
                        <label class="form-label">
                            <i class="bi bi-envelope"></i> {{ form.email.label.text }}
                        </label>
                        {{ form.email(class="form-control" + (" is-invalid" if form.email.errors else ""), placeholder="Введите email") }}
                        {% for error in form.email.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="mb-3">
                        <label class="form-label">
                            <i class="bi bi-lock"></i> {{ form.password.label.text }}
                        </label>
                        {{ form.password(class="form-control" + (" is-invalid" if form.password.errors else ""), placeholder="Введите пароль") }}
                        {% for error in form.password.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="mb-4">
                        <label class="form-label">
                            <i class="bi bi-lock-fill"></i> {{ form.confirm_password.label.text }}
                        </label>
                        {{ form.confirm_password(class="form-control" + (" is-invalid" if form.confirm_password.errors else ""), placeholder="Подтвердите пароль") }}
                        {% for error in form.confirm_password.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="d-grid">
                        {{ form.submit(class="btn btn-primary-custom btn-lg") }}
                    </div>
                </form>

                <div class="text-center mt-4">
                    <p class="mb-0">Уже есть аккаунт? 
                        <a href="{{ url_for('login') }}" class="text-decoration-none" style="color: var(--primary-color);">
                            Войдите
                        </a>
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

LOGIN_TEMPLATE = '''{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card fade-in">
            <div class="card-body p-5">
                <div class="text-center mb-4">
                    <i class="bi bi-box-arrow-in-right" style="font-size: 3rem; color: var(--primary-color);"></i>
                    <h2 class="mt-3">Добро пожаловать!</h2>
                    <p class="text-muted">Войдите в свою кулинарную книгу</p>
                </div>

                <form method="POST" action="">
                    {{ form.hidden_tag() }}

                    <div class="mb-3">
                        <label class="form-label">
                            <i class="bi bi-envelope"></i> {{ form.email.label.text }}
                        </label>
                        {{ form.email(class="form-control" + (" is-invalid" if form.email.errors else ""), placeholder="Введите email") }}
                        {% for error in form.email.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="mb-4">
                        <label class="form-label">
                            <i class="bi bi-lock"></i> {{ form.password.label.text }}
                        </label>
                        {{ form.password(class="form-control" + (" is-invalid" if form.password.errors else ""), placeholder="Введите пароль") }}
                        {% for error in form.password.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="d-grid">
                        {{ form.submit(class="btn btn-primary-custom btn-lg") }}
                    </div>
                </form>

                <div class="text-center mt-4">
                    <p class="mb-0">Нет аккаунта? 
                        <a href="{{ url_for('register') }}" class="text-decoration-none" style="color: var(--primary-color);">
                            Зарегистрируйтесь
                        </a>
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

PROFILE_TEMPLATE = '''{% extends "base.html" %}

{% block content %}
<div class="row">
    <div class="col-md-4 mb-4">
        <div class="card fade-in">
            <div class="card-body text-center p-4">
                <div class="position-relative d-inline-block">
                    <i class="bi bi-person-circle" style="font-size: 5rem; color: var(--primary-color);"></i>
                </div>
                <h3 class="mt-3">{{ current_user.username }}</h3>
                <p class="text-muted">
                    <i class="bi bi-envelope"></i> {{ current_user.email }}
                </p>
                <div class="d-flex justify-content-center gap-3 mt-3">
                    <div class="text-center">
                        <h4 class="mb-0">{{ current_user.recipes|length }}</h4>
                        <small class="text-muted">Рецептов</small>
                    </div>
                    <div class="text-center">
                        <h4 class="mb-0">{{ current_user.created_at.strftime('%d.%m.%Y') }}</h4>
                        <small class="text-muted">На сайте с</small>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="col-md-8">
        <div class="card fade-in">
            <div class="card-body p-4">
                <h4 class="mb-4">
                    <i class="bi bi-pie-chart-fill" style="color: var(--primary-color);"></i>
                    Статистика
                </h4>

                {% set categories = {
                    'breakfast': {'emoji': '', 'name': 'Завтрак'},
                    'lunch': {'emoji': '', 'name': 'Обед'},
                    'dinner': {'emoji': '', 'name': 'Ужин'},
                    'dessert': {'emoji': '', 'name': 'Десерт'},
                    'salad': {'emoji': '', 'name': 'Салат'},
                    'soup': {'emoji': '', 'name': 'Супы'},
                    'baking': {'emoji': '', 'name': 'Выпечка'},
                    'drinks': {'emoji': '', 'name': 'Напитки'},
                    'appetizer': {'emoji': '', 'name': 'Закуски'},
                    'sauce': {'emoji': '', 'name': 'Соусы'}
                } %}

                <div class="row g-3 mb-4">
                    {% for cat_key, cat_info in categories.items() %}
                        {% set count = current_user.recipes|selectattr('category', 'equalto', cat_key)|list|length %}
                        {% if count > 0 %}
                            <div class="col-md-6">
                                <div class="d-flex align-items-center p-3 bg-light rounded-3">
                                    <span style="font-size: 1.5rem; margin-right: 1rem;">{{ cat_info.emoji }}</span>
                                    <div class="flex-grow-1">
                                        <h6 class="mb-0">{{ cat_info.name }}</h6>
                                    </div>
                                    <span class="badge bg-primary rounded-pill">{{ count }}</span>
                                </div>
                            </div>
                        {% endif %}
                    {% endfor %}
                </div>

                {% if current_user.recipes %}
                    <h5 class="mb-3">
                        <i class="bi bi-clock-history"></i>
                        Последние добавленные
                    </h5>
                    <div class="list-group list-group-flush">
                        {% for recipe in current_user.recipes[:5] %}
                            <a href="{{ url_for('view_recipe', recipe_id=recipe.id) }}" 
                               class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="mb-1">{{ recipe.title }}</h6>
                                    <small class="text-muted">
                                        <i class="bi bi-clock"></i> {{ recipe.cooking_time }} мин
                                    </small>
                                </div>
                                <small class="text-muted">{{ recipe.created_at.strftime('%d.%m.%Y') }}</small>
                            </a>
                        {% endfor %}
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

RECIPE_FORM_TEMPLATE = '''{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card fade-in">
            <div class="card-body p-4">
                <h2 class="mb-4">
                    <i class="bi bi-pencil-square" style="color: var(--primary-color);"></i>
                    {{ title }}
                </h2>

                <form method="POST" action="">
                    {{ form.hidden_tag() }}

                    <div class="mb-3">
                        {{ form.title.label(class="form-label fw-bold") }}
                        {{ form.title(class="form-control" + (" is-invalid" if form.title.errors else ""), placeholder="Например: Борщ, Паста Карбонара...") }}
                        {% for error in form.title.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="mb-3">
                        {{ form.description.label(class="form-label fw-bold") }}
                        {{ form.description(class="form-control" + (" is-invalid" if form.description.errors else ""), rows=3, placeholder="Краткое описание блюда...") }}
                        {% for error in form.description.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="row mb-3">
                        <div class="col-md-6">
                            {{ form.cooking_time.label(class="form-label fw-bold") }}
                            {{ form.cooking_time(class="form-control" + (" is-invalid" if form.cooking_time.errors else ""), type="number", placeholder="В минутах") }}
                            {% for error in form.cooking_time.errors %}
                                <div class="invalid-feedback">{{ error }}</div>
                            {% endfor %}
                        </div>

                        <div class="col-md-6">
                            {{ form.category.label(class="form-label fw-bold") }}
                            {{ form.category(class="form-select" + (" is-invalid" if form.category.errors else "")) }}
                            {% for error in form.category.errors %}
                                <div class="invalid-feedback">{{ error }}</div>
                            {% endfor %}
                        </div>
                    </div>

                    <div class="mb-3">
                        {{ form.ingredients.label(class="form-label fw-bold") }}
                        {{ form.ingredients(class="form-control" + (" is-invalid" if form.ingredients.errors else ""), rows=6, placeholder="Картофель - 500г
Лук - 2 шт
Морковь - 1 шт
...") }}
                        {% for error in form.ingredients.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                        <div class="form-text">
                            <i class="bi bi-info-circle"></i> Каждый ингредиент с новой строки
                        </div>
                    </div>

                    <div class="mb-4">
                        {{ form.instructions.label(class="form-label fw-bold") }}
                        {{ form.instructions(class="form-control" + (" is-invalid" if form.instructions.errors else ""), rows=8, placeholder="1. Подготовьте все ингредиенты...
2. Разогрейте сковороду...
3. ...") }}
                        {% for error in form.instructions.errors %}
                            <div class="invalid-feedback">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="d-flex gap-2">
                        {{ form.submit(class="btn btn-primary-custom btn-lg") }}
                        <a href="{{ url_for('index') }}" class="btn btn-outline-secondary btn-lg">Отмена</a>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

RECIPE_DETAIL_TEMPLATE = '''{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-10">
        <div class="card fade-in">
            <div class="card-body p-5">
                <!-- Заголовок -->
                <div class="mb-4">
                    <div class="d-flex justify-content-between align-items-start">
                        <h1 class="display-5 mb-3">{{ recipe.title }}</h1>
                        <span class="category-badge position-relative" style="top: 0; right: 0;">
                            {% if recipe.category == 'breakfast' %} Завтрак
                            {% elif recipe.category == 'lunch' %} Обед
                            {% elif recipe.category == 'dinner' %} Ужин
                            {% elif recipe.category == 'dessert' %} Десерт
                            {% elif recipe.category == 'salad' %} Салат
                            {% elif recipe.category == 'soup' %} Супы
                            {% elif recipe.category == 'baking' %} Выпечка
                            {% elif recipe.category == 'drinks' %} Напитки
                            {% elif recipe.category == 'appetizer' %} Закуски
                            {% elif recipe.category == 'sauce' %} Соусы
                            {% endif %}
                        </span>
                    </div>

                    <!-- Метки времени -->
                    <div class="d-flex gap-3 mb-4">
                        <span class="time-badge">
                            <i class="bi bi-clock"></i> {{ recipe.cooking_time }} минут
                        </span>
                        <span class="badge bg-light text-dark p-2">
                            <i class="bi bi-calendar3"></i> {{ recipe.created_at.strftime('%d %B %Y') }}
                        </span>
                    </div>
                </div>

                <!-- Описание -->
                {% if recipe.description %}
                <div class="mb-5">
                    <h4 class="mb-3">
                        <i class="bi bi-info-circle-fill" style="color: var(--primary-color);"></i>
                        О рецепте
                    </h4>
                    <div class="p-4 bg-light rounded-3">
                        {{ recipe.description }}
                    </div>
                </div>
                {% endif %}

                <!-- Ингредиенты -->
                <div class="mb-5">
                    <h4 class="mb-3">
                        <i class="bi bi-basket-fill" style="color: var(--primary-color);"></i>
                        Ингредиенты
                    </h4>
                    <div class="row">
                        <div class="col-md-8">
                            <ul class="ingredient-list">
                                {% for ingredient in ingredients %}
                                    {% if ingredient.strip() %}
                                        <li>{{ ingredient }}</li>
                                    {% endif %}
                                {% endfor %}
                            </ul>
                        </div>
                    </div>
                </div>

                <!-- Инструкция -->
                <div class="mb-5">
                    <h4 class="mb-3">
                        <i class="bi bi-list-check" style="color: var(--primary-color);"></i>
                        Инструкция приготовления
                    </h4>
                    <div class="instructions-container">
                        {% set steps = recipe.instructions.split('\\n') %}
                        {% for step in steps %}
                            {% if step.strip() %}
                                <div class="instruction-step">
                                    {{ step }}
                                </div>
                            {% endif %}
                        {% endfor %}
                    </div>
                </div>

                <!-- Кнопки управления (только для автора) -->
                {% if current_user.is_authenticated and current_user.id == recipe.user_id %}
                <div class="border-top pt-4 mt-4">
                    <div class="d-flex gap-2">
                        <a href="{{ url_for('edit_recipe', recipe_id=recipe.id) }}" class="btn btn-warning btn-lg">
                            <i class="bi bi-pencil"></i> Редактировать
                        </a>
                        <form action="{{ url_for('delete_recipe', recipe_id=recipe.id) }}" method="POST" class="d-inline">
                            <button type="submit" class="btn btn-danger btn-lg" 
                                    onclick="return confirm('Вы уверены, что хотите удалить этот рецепт?')">
                                <i class="bi bi-trash"></i> Удалить
                            </button>
                        </form>
                        <a href="{{ url_for('index') }}" class="btn btn-outline-secondary btn-lg ms-auto">
                            <i class="bi bi-arrow-left"></i> Назад
                        </a>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

os.makedirs('templates', exist_ok=True)

with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(BASE_TEMPLATE)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(INDEX_TEMPLATE)

with open('templates/register.html', 'w', encoding='utf-8') as f:
    f.write(REGISTER_TEMPLATE)

with open('templates/login.html', 'w', encoding='utf-8') as f:
    f.write(LOGIN_TEMPLATE)

with open('templates/profile.html', 'w', encoding='utf-8') as f:
    f.write(PROFILE_TEMPLATE)

with open('templates/recipe_form.html', 'w', encoding='utf-8') as f:
    f.write(RECIPE_FORM_TEMPLATE)

with open('templates/recipe_detail.html', 'w', encoding='utf-8') as f:
    f.write(RECIPE_DETAIL_TEMPLATE)

if __name__ == '__main__':
    app.run(debug=True)
