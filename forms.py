from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, IntegerField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Email
from models import User

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
