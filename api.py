from flask_restful import Resource, reqparse, abort as rest_abort
from flask import jsonify
from models import Recipe, User, db

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
