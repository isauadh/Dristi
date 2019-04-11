import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request
from dristi import app, db, bcrypt, mail
from dristi.forms import RegistrationForm, LoginForm, UpdateAccountForm, RequestResetForm, ResetPasswordForm
from dristi.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message

from urllib.request import urlopen as uReq
from bs4 import BeautifulSoup as soup
import json

my_url = 'https://www.cinemark.com/west-texas/cinemark-tinseltown-lubbock-and-xd'
uClient = uReq(my_url)
page_html = uClient.read()
uClient.close()
page_soup = soup(page_html, "html.parser")
containers = page_soup.findAll("div", {"class" : "col-xs-12 col-sm-10"})

Movies = {}

Movies['Title'] = []
Movies['Rating'] = []
Movies['Runtime'] = []
Movies['Showtimes'] = []
Movies['Poster'] = []
for container in containers:
    title_container = container.findAll("div", {"class" : "movieBlockInfo"})
    title = title_container[0].div.a.text.strip('\n')
    
    rating_container = container.findAll("span", {"class" : "showtimeMovieRating"})
    rating = rating_container[0].text
    
    runtime_container = container.findAll("span", {"class": "showtimeMovieRuntime"})
    runtime = runtime_container[0].text
    
    img_container = container.findAll("source", {"media" : "(min-width: 450px)"})
    img_soup = soup(str(img_container[0]))
    img = img_soup.source['srcset']

    times = []
    showtimes = container.findAll("div", {"class" : "showtime"})
    for showtime in showtimes:
        times.append(str(showtime.a.text.strip('\n\r\t": ')))
    
    Movies['Title'].append(str(title))
    Movies['Rating'].append(str(rating))
    Movies['Runtime'].append(str(runtime))
    Movies['Showtimes'].append(times)
    Movies['Poster'].append(img)

temp = {}
posts = []
for i in range(0,len(Movies['Title'])):
  for key, value in Movies.items():
    temp[key] = value[i]
  posts.append(temp)
  temp = {}


@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html', posts=posts)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, rating=form.rating.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('my_taste'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/My Taste")
@login_required
def my_taste():
    taste = current_user.rating
    return render_template('my_taste.html', title='My Taste', posts=posts, taste=taste)



@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.rating = form.rating.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link: {url_for('reset_token', token=token, _external=True)}
    If you did not make this request then simply ignore this email and no changes will be made.'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user =User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_request.html', form =form, title='Reset Password')

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)