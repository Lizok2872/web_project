class Route
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
    
