import os
from flask import Flask, render_template, session, url_for, redirect, request, abort, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv


load_dotenv()

#credentials
db_user = os.environ['DB_USER']
db_password = os.environ['DB_PASSWORD']
db_name = os.environ['DB_NAME']

db = SQLAlchemy()
def create_app():
    app = Flask(__name__)
    app.config.from_object('config')


    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://{db_user}:{db_password}@localhost/{db_name}".format(
        db_user=db_user, db_password=db_password, db_name=db_name)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route('/users')
    def users():
        from database import list_users
        return {'users': list_users()}

    @app.errorhandler(401)
    def FUN_401(error):
        return render_template("page_401.html"), 401


    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.route("/login", methods = ["POST"])
    def login():
        from database import list_users, verify
        id_submitted = request.form.get("id")
        if (id_submitted in list_users()) and verify(id_submitted, request.form.get("pw")):
            session['current_user'] = id_submitted
            return(redirect(url_for("home")))
        else:
            flash("Invalid Credentials")
            return redirect(url_for("home"))
        
    @app.route("/logout/")
    def logout():
        session.pop("current_user", None)
        return(redirect(url_for("home")))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        from werkzeug.security import generate_password_hash
        from models import user
        from sqlalchemy.exc import IntegrityError

        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            email = request.form.get("email")

            # existing_user = user.query.filter_by(username=username).first()
            # if existing_user:
            #     flash("Username already exists. Please choose different username")
            #     return redirect(url_for("register"))
            
            hashed_password = generate_password_hash(password)
            new_user = user(username=username, password=hashed_password, email=email)
            
            try:
                db.session.add(new_user)
                db.session.commit()
                flash("User registered successfully!")
                return redirect(url_for("login"))
            except IntegrityError:
                db.session.rollback()
                flash('Username or Email already exists please choose another.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Error: {str(e)}', 'danger')
        return render_template("register.html")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
