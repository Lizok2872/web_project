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
from login_manager import Login
from app.route import Route2
from errorhandler import Errorhandler
from login_required import Required
from route import Route


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

    
        

if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1', debug=True)
