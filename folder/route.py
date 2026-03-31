class Route:
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
