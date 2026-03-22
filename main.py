from flask import Flask, render_template, redirect, url_for, flash, request, abort, make_response, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from flask_restful import Api, Resource, reqparse, abort as rest_abort
from wtforms import StringField, PasswordField, TextAreaField, SelectField, IntegerField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Email
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import asyncio
import aiohttp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cookbook.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице'

api = Api(app)


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

    def to_dict(self, only=None):
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'recipes_count': len(self.recipes)
        }
        if only:
            return {k: v for k, v in data.items() if k in only}
        return data

    def __repr__(self):
        return f'<User> {self.id} {self.username} {self.email}'


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

    def to_dict(self, only=None):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'ingredients': self.ingredients.split('\n'),
            'instructions': self.instructions.split('\n'),
            'cooking_time': self.cooking_time,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'author': self.author.username if self.author else None,
            'author_id': self.user_id
        }
        if only:
            return {k: v for k, v in data.items() if k in only}
        return data

    def __repr__(self):
        return f'<Recipe> {self.id} {self.title}'


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
    remember_me = BooleanField('Запомнить меня')
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


def abort_if_recipe_not_found(recipe_id):
    recipe = Recipe.query.get(recipe_id)
    if not recipe:
        rest_abort(404, message=f"Recipe {recipe_id} not found")


parser = reqparse.RequestParser()
parser.add_argument('title', required=True, help='Title cannot be blank')
parser.add_argument('description', required=True, help='Description cannot be blank')
parser.add_argument('ingredients', required=True, help='Ingredients cannot be blank')
parser.add_argument('instructions', required=True, help='Instructions cannot be blank')
parser.add_argument('cooking_time', required=True, type=int, help='Cooking time must be integer')
parser.add_argument('category', required=True, help='Category cannot be blank')
parser.add_argument('user_id', required=True, type=int, help='User ID must be integer')


class RecipeResource(Resource):

    def get(self, recipe_id):
        abort_if_recipe_not_found(recipe_id)
        recipe = Recipe.query.get(recipe_id)
        return jsonify({'recipe': recipe.to_dict()})

    def put(self, recipe_id):
        abort_if_recipe_not_found(recipe_id)
        args = parser.parse_args()

        recipe = Recipe.query.get(recipe_id)
        recipe.title = args['title']
        recipe.description = args['description']
        recipe.ingredients = args['ingredients']
        recipe.instructions = args['instructions']
        recipe.cooking_time = args['cooking_time']
        recipe.category = args['category']

        db.session.commit()
        return jsonify({'success': 'Recipe updated', 'id': recipe.id})

    def delete(self, recipe_id):
        abort_if_recipe_not_found(recipe_id)

        recipe = Recipe.query.get(recipe_id)
        db.session.delete(recipe)
        db.session.commit()
        return jsonify({'success': 'Recipe deleted'})


class RecipeListResource(Resource):

    def get(self):
        recipes = Recipe.query.order_by(Recipe.created_at.desc()).all()
        return jsonify({'recipes': [
            recipe.to_dict(only=('id', 'title', 'description', 'cooking_time', 'category', 'author')) for recipe in
            recipes]})

    def post(self):
        args = parser.parse_args()
        user = User.query.get(args['user_id'])
        if not user:
            rest_abort(404, message=f"User {args['user_id']} not found")

        recipe = Recipe(
            title=args['title'],
            description=args['description'],
            ingredients=args['ingredients'],
            instructions=args['instructions'],
            cooking_time=args['cooking_time'],
            category=args['category'],
            user_id=args['user_id']
        )

        db.session.add(recipe)
        db.session.commit()

        return jsonify({'id': recipe.id, 'message': 'Recipe created successfully'})


class UserResource(Resource):

    def get(self, user_id):
        user = User.query.get(user_id)
        if not user:
            rest_abort(404, message=f"User {user_id} not found")
        return jsonify({'user': user.to_dict()})


class UserRecipesResource(Resource):

    def get(self, user_id):
        user = User.query.get(user_id)
        if not user:
            rest_abort(404, message=f"User {user_id} not found")

        recipes = Recipe.query.filter_by(user_id=user_id).order_by(Recipe.created_at.desc()).all()
        return jsonify({'recipes': [recipe.to_dict(only=('id', 'title', 'description', 'cooking_time', 'category')) for
                                    recipe in recipes]})


api.add_resource(RecipeListResource, '/api/v1/recipes')
api.add_resource(RecipeResource, '/api/v1/recipes/<int:recipe_id>')
api.add_resource(UserResource, '/api/v1/users/<int:user_id>')
api.add_resource(UserRecipesResource, '/api/v1/users/<int:user_id>/recipes')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()
    print("База данных инициализирована")


@app.route('/')
def index():
    search_query = request.args.get('q', '')

    if current_user.is_authenticated:
        if search_query:
            recipes = Recipe.query.filter(
                Recipe.user_id == current_user.id,
                Recipe.title.ilike(f'%{search_query}%')
            ).order_by(Recipe.created_at.desc()).all()
        else:
            recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.created_at.desc()).all()
    else:
        recipes = []

    visits_count = session.get('visits_count', 0)
    session['visits_count'] = visits_count + 1

    return render_template('index.html', recipes=recipes, search_query=search_query)


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


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        if form.password.data != form.confirm_password.data:
            return render_template('register.html', title='Регистрация',
                                   form=form, message="Пароли не совпадают")

        if User.query.filter_by(email=form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form, message="Такой пользователь уже есть")

        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash(f'С возвращением, {user.username}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            return render_template('login.html', title='Авторизация',
                                   form=form, message='Неверный email или пароль')

    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы. До свидания!', 'info')
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

    if recipe.user_id != current_user.id:
        flash('У вас нет доступа к этому рецепту', 'danger')
        return redirect(url_for('index'))

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


@app.route('/api/docs')
def api_docs():
    return render_template('api_docs.html')


async def fetch_recipe_data_async(session, recipe_id):
    url = f"http://localhost:5000/api/v1/recipes/{recipe_id}"
    async with session.get(url) as response:
        return await response.json()


def run_async_recipe_fetch(recipe_ids):

    async def fetch_all():
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_recipe_data_async(session, rid) for rid in recipe_ids]
            results = await asyncio.gather(*tasks)
            return results

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(fetch_all())


@app.route('/async_demo')
def async_demo():
    recipes = Recipe.query.limit(3).all()
    recipe_ids = [r.id for r in recipes]

    if recipe_ids:
        results = run_async_recipe_fetch(recipe_ids)
    else:
        results = []

    return render_template('async_demo.html', results=results, recipe_ids=recipe_ids)


@app.route('/cookie_test')
def cookie_test():
    visits_count = int(request.cookies.get('visits_count', 0))

    if visits_count:
        res = make_response(render_template('cookie_test.html', visits_count=visits_count + 1))
        res.set_cookie('visits_count', str(visits_count + 1), max_age=60 * 60 * 24 * 365 * 2)
    else:
        res = make_response(render_template('cookie_test.html', visits_count=1))
        res.set_cookie('visits_count', '1', max_age=60 * 60 * 24 * 365 * 2)

    return res


@app.route('/session_test')
def session_test():
    visits_count = session.get('visits_count', 0)
    session['visits_count'] = visits_count + 1
    session.permanent = True
    return render_template('session_test.html', visits_count=visits_count + 1)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad Request'}), 400)


if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1', debug=True)
