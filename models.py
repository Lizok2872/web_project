from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

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
