import os
from datetime import timedelta
from flask import Flask
from flask_login import LoginManager
from flask_restful import Api
from models import db
from api import RecipeListResource, RecipeResource, UserResource, UserRecipesResource
from login_manager import setup_login_manager
from app_route import app_route
from errorhandler import errorhandler


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'cookbook.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице'

setup_login_manager(login_manager)

api = Api(app)
api.add_resource(RecipeListResource, '/api/v1/recipes')
api.add_resource(RecipeResource, '/api/v1/recipes/<int:recipe_id>')
api.add_resource(UserResource, '/api/v1/users/<int:user_id>')
api.add_resource(UserRecipesResource, '/api/v1/users/<int:user_id>/recipes')

app_route(app)
errorhandler(app)

if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1', debug=True)
