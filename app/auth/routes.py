from flask import render_template, url_for, flash, redirect, request
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.auth import auth_bp
from app.auth.forms import RegistrationForm, LoginForm, ChangePasswordForm
from app.models.user import User

@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)

@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('auth/login.html', title='Login', form=form)

@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@auth_bp.route("/change-password", methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if check_password_hash(current_user.password_hash, form.current_password.data):
            current_user.password_hash = generate_password_hash(form.new_password.data)
            db.session.commit()
            flash('Your password has been successfully updated!', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Update Failed. Current password is incorrect.', 'danger')
    return render_template('auth/change_password.html', title='Change Password', form=form)
