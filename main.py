from flask import Flask, render_template, redirect, request
from flask import session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import InputRequired, Length, Email, EqualTo
from app import db, app
from models import User, Book
from forms import LoginForm, RegistrationForm, AddBookForm, RateReviewForm
from hashutils import check_pw_hash

# routes: index, reading now, coming up, full list, settings (sub settings
# options for weights, categories, priorities, ratios?), subscribable
# reading lists, . . .

# TODO: create route/handler and template for reading-history


@app.before_request
def require_login():

    if not ("user" in session or request.endpoint in ["login", "register"]):
        return redirect(url_for("login"))


@app.route("/", methods=["GET"])
@app.route("/home", methods=["GET"])
def home():

    email = session["user"]
    user = User.query.filter_by(email=email).first()
    master_list = Book.query.filter_by(user=user.id, read=False).all()
    current_list = []

    for i in range(3):

        if master_list[i].category == 1:
            category = "5 Mins to Kill"
            style = "table-success"

        elif master_list[i].category == 2: 
            category = "Relax/Escape"
            style = "table-info"

        elif master_list[i].category == 3:
            category = "Focused Learning"
            style = "table-warning"

        else:
            category = "None"
            style = "table-light"

        current_list.append(
                           {"title": master_list[i].title,
                            "author": master_list[i].author,
                            "category": category, 
                            "style": style}
                            )


    return render_template("home.html", current_list=current_list)


@app.route("/login", methods=["GET", "POST"])
def login():

    form = LoginForm()
    if request.method == "GET":
        return render_template("login.html", title="Log In", form=form)

    else:

        email = form.email.data.lower()
        password = form.password.data

        if not User.query.filter_by(email=email):
            flash("Invalid username or password.", "error")
            return render_template("login.html", title="Log In", form=form)

        user = User.query.filter_by(email=email).first()

        if not check_pw_hash(password, user.pw_hash):

            flash("Invalid username or password.", "error")
            return render_template("login.html", title="Log In", form=form)

        session["user"] = email
        return redirect(url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():

    form = RegistrationForm()

    if request.method == "GET":
        return render_template("register.html", title="Register", form=form)

    if form.validate_on_submit():

        first_name = form.first_name.data
        last_name = form.last_name.data
        email = form.email.data.lower()
        password = form.password.data

        # final step in validation: unique email/not existing user
        if User.query.filter_by(email=email).first():

            flash("A user with that email address already exists!", "error")

            return render_template("register.html", title="Register",
                                   form=form)

        else:
            # password hashed by constructor of User model
            user = User(first_name, last_name, email, password)
            db.session.add(user)
            db.session.commit()

            flash(f"Account created for {email}!")
            session["user"] = email

            return redirect(url_for("home"))

    else:

        for error in form.errors.items():

            flash(f"{error[1][0]}!", "error")

        return render_template("register.html", title="Register", form=form)


@app.route("/logout", methods=["GET"])
def logout():

    del session["user"]

    return redirect(url_for("login"))


@app.route("/edit-list", methods=["GET", "POST"])
def edit_list():

# TODO: Refactor to move processing from templates to main
# TODO: Make adding a book a modal 
# TODO: Give the reading list table its own screen; allow change of 
# category via dropdown selection in table row

    # get user
    email = session["user"]
    user = User.query.filter_by(email=email).first()
    current_list = Book.query.filter_by(user=user.id, read=False).all()
    form = AddBookForm()

    if request.method == "GET":
        return render_template("edit-list.html", form=form,
                               current_list=current_list)

    if form.validate_on_submit():

        # get form data
        title = form.title.data
        author = form.author.data
        category = form.category.data
        user = user.id
        read = False
        rating = None
        review = None
        isbn = form.isbn.data

        book = Book(title, author, category, user, read, rating, review, isbn)
        print(type(book.category))

        db.session.add(book)
        db.session.commit()

        flash(f"{title} added to reading list!")

        return redirect(url_for("edit_list"))

    for error in form.errors.items():

        flash(f"{error[1][0]}!", "error")

    return render_template("edit-list.html", form=form,
                           current_list=current_list)


@app.route("/remove-book", methods=["GET"])
def remove_book():

    if request.args:

        book_id = request.args.get("id")
        book = Book.query.get(book_id)

        db.session.delete(book)
        db.session.commit()

        flash(f"{book.title} removed from reading list!", "info")

    return redirect(url_for("edit_list"))


@app.route("/reading-history", methods=["GET", "POST"])
def reading_history():

    form = RateReviewForm()

    if request.args.get("id"):

        book_id = request.args.get("id")
        book = Book.query.get(book_id)

        # send user to rating and review form
        return render_template("rate-review.html", form=form, book=book)

    if request.method == "POST":

        rating = form.rating.data
        review = form.review.data
        book_id = form.book_id.data

        book = Book.query.get(book_id)

        book.rating = rating
        book.review = review
        book.read = True

        db.session.commit()
        flash(f"{book.title} added to your reading history.", "info")

    # user should fall through to this point if GET with no args or POST after
    # form data has been validated and db has been updated
    user_email = session["user"]
    user = User.query.filter_by(email=user_email).first()
    history = Book.query.filter_by(user=user.id, read=True)

    return render_template("reading-history.html", history=history)


if __name__ == "__main__":
    app.run()
