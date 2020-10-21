from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, RadioField, ValidationError
from wtforms.validators import InputRequired, Email, Length, EqualTo
from dist import sake_distance
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

import os
import psycopg2
import pandas as pd

app = Flask(__name__)

ENV = 'dev'

# Set the dubugging mode and the SQLAlchemy database URI
# production (prod): The PostgreSQL server on heroku
# Development (dev): The local postreSQL server
if ENV=='prod':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

app.secret_key = os.urandom(32)
app.permanent_session_lifetime = timedelta(minutes=5)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column("id", db.Integer, primary_key=True)
    username = db.Column("username", db.String(15), unique=True)
    email = db.Column("email", db.String(50), unique=True)
    password = db.Column(db.String(80))

    def __repr__(self):
        return '<User %r>' % self.username

class Sake(db.Model):
    __tablename__ = 'sake'
    index = db.Column(db.Integer, primary_key=True)
    Sake_name = db.Column(db.String)
    Sake_Product_Name = db.Column(db.String)
    Type = db.Column(db.String)
    SMV = db.Column(db.Numeric(precision=8, scale=2))
    Acidity = db.Column(db.Numeric(precision=8, scale=2))
    Amakara = db.Column(db.Numeric(precision=8, scale=3))
    Notan = db.Column(db.Numeric(precision=8, scale=3))
    ABV = db.Column(db.Numeric(precision=8, scale=2))
    Taste_like = db.Column(db.Integer)
    Taste_dislike = db.Column(db.Integer)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class SearchForm(FlaskForm):
    search = StringField('', [InputRequired()], render_kw={"placeholder": "Sake Name (in Japanese)"})

class SelectSakeForm(FlaskForm):
    selectsake = RadioField(validators=[InputRequired()])

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])
    remember = BooleanField('Remember me') # This may need to be used in the later version

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])
    confirm  = PasswordField("Confirm password", validators=[InputRequired(),
    Length(min=8,max=80), EqualTo('password', message="Password must match")])

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')

# Home Page
@app.route('/', methods=['GET', 'POST'])
def index():
    form = SearchForm()
    if request.method == 'POST' and form.validate_on_submit():
        results = []
        search_string = form.data['search']
        if search_string:
            qry = Sake.query.filter_by(Sake_name=search_string)
            results = qry.all()

        if not results:
            flash('No results found!')
            return redirect('/')
        else:
            session['search_string'] = search_string
            return redirect(url_for('search'))

    return render_template("index.html", form=form)


# Print Search Results
@app.route('/search', methods=['GET', 'POST'])
def search():
    results = Sake.query.filter_by(Sake_name=session.get('search_string', None)).all()
    form = SelectSakeForm()
    form.selectsake.choices = [(row.index, row.Sake_Product_Name) for row in results]

    if request.method == 'POST':
        if not form.validate_on_submit():
            flash('Select one Sake!')
            return redirect(url_for('search'))
        else:
            # recsakeid is the selected Sake id for distance calculation
            session['recsakeid'] = request.form['selectsake']
            # print('sake id for recommend:', request.form['selectsake'])
            # Here calculate the distances based on recsakeid
            dists, indices = sake_distance(db, session.get('recsakeid', None))
            if indices:
                sake_recommend = [Sake.query.filter(Sake.index==idx).first() for idx in indices]
            return render_template('recommend.html', recommend=zip(dists, sake_recommend))

    return render_template('search.html', form=form, table=zip(form.selectsake, results))

# Print popular items
@app.route('/hot', methods=['GET'])
def hot():
    hotitems = Sake.query.filter(Sake.Taste_like + Sake.Taste_dislike > 800).order_by((Sake.Taste_like + Sake.Taste_dislike).desc()).all()
    return render_template('hot.html', hotitems=hotitems)

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                # return redirect(url_for('dashboard'))
                flash("Login Successful!")
                return redirect(url_for('account'))

        # return '<h1>Invalid username or password</h1>'
        flash("Invalid username or password")
        return render_template('login.html', form=form)
        #return '<h1>' + form.username.data + ' ' + form.password.data + '</h1>'

    return render_template('login.html', form=form)

# Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("New account has been created!")
        return redirect(url_for('index'))

    return render_template('register.html', form=form)

# User Account Page
@app.route('/account')
@login_required
def account():
    return render_template('account.html', name=current_user.username)

# User logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash(f"You have been logged out", "info")
    return redirect(url_for('index'))

@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    app.run(port=33507)
