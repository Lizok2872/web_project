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
