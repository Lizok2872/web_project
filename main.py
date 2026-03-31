import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, make_response, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_restful import Api
from models import db, User, Recipe
from forms import RegistrationForm, LoginForm, RecipeForm
from api import RecipeListResource, RecipeResource, UserResource, UserRecipesResource
from what import What

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cookbook.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице'
api = Api(app)
api.add_resource(RecipeListResource, '/api/v1/recipes')
api.add_resource(RecipeResource, '/api/v1/recipes/<int:recipe_id>')
api.add_resource(UserResource, '/api/v1/users/<int:user_id>')
api.add_resource(UserRecipesResource, '/api/v1/users/<int:user_id>/recipes')


    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    
    with app.app_context():
        db.create_all()
    
    
    
    async def fetch_recipe_data_async(session, recipe_id):
        url = f"http://localhost:8080/api/v1/recipes/{recipe_id}"
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
        if recipe.use_id != current_user.id:
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
        if recipe.user_i != current_user.id:
            flash('У вас нет прав для удаления этого рецепта', 'danger')
            return redirect(url_for('index'))
        db.session.delete(recipe)
        db.session.commit()
        flash(' Рецепт успешно удален!', 'success')
        return redirect(url_for('index'))
    
    
    @app.route('/api/docs')
    def api_docs():
        return render_template('api_docs.html')
    
    
    @app.route('/async_demo')
    def async_demo():
        recipes = Recipe.query.limit(3).all()
        recipe_ids = [r.id for r in recipes]
        if recipe_ids:
            results = run_async_recipe_fetch(recipe_ids)
        else:
            results = []
        return render_template('async_demo.html', results=results, recipe_ids=recipe_ids)
    
    
    @app.errorhandler(404)
    def not_found(error):
        return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad Request'}), 400)

if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1', debug=True)
