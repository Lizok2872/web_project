class Login_required:
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
            flash('✏ Рецепт успешно обновлен!', 'success')
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
        flash('🗑 Рецепт успешно удален!', 'success')
        return redirect(url_for('index'))
