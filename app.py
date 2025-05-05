import os
from flask import Flask, render_template, session, url_for, redirect, request, abort, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv


load_dotenv()

#credentials
db_user = os.environ['DB_USER']
db_password = os.environ['DB_PASSWORD']
db_name = os.environ['DB_NAME']

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config')


    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://{db_user}:{db_password}@localhost/{db_name}".format(
        db_user=db_user, db_password=db_password, db_name=db_name)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    migrate.init_app(app,db)

    with app.app_context():
        db.create_all()

    @app.route('/users')
    def users():
        from models import user
        print(f"Current session user: {session.get('current_user')}")  # Debugging
        current_user = user.query.filter_by(username=session.get("current_user")).first()
        
        if current_user is None:
            flash("You need to be logged in to view this page. ")
            return redirect(url_for('login'))
        
        if not current_user.is_admin:
            flash("You do not have permission to view this page.")
            return redirect(url_for('home'))            
                    
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

    @app.route("/login", methods = ["GET","POST"])
    def login():
        from database import list_users, verify

        #handle post request
        if request.method == "POST":
            username_submitted = request.form.get("id").strip()
            password_submitted = request.form.get("pw").strip()

            # Debugging: Print username and password submitted
            print(f"Username Submitted: {username_submitted}")
            print(f"Password Submitted: {password_submitted}")
            if (username_submitted in list_users()) and verify(username_submitted, password_submitted):
                session['current_user'] = username_submitted
                print(f"Current session user: {session['current_user']}")  # Debugging
                flash("Login successful!") 
                return(redirect(url_for("home")))
            else:
                flash("Invalid Credentials")
                return redirect(url_for("login"))
        #handle get request
        return render_template("login.html")

            
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
            # Debugging: Print username and password submitted
            print(f"Username Submitted: {username}")
            print(f"Password Submitted: {password}")
            existing_user = user.query.filter_by(username=username).first()
            existing_email = user.query.filter_by(email=email).first()
            if existing_user:
                flash("Username already exists. Please choose different username")
                return redirect(url_for("register"))
            if existing_email:
                flash("Email already exists. Please choose different email address")
                return redirect(url_for("register"))

            hashed_password = generate_password_hash(password, method='scrypt')
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

    @app.route("/admin/")
    def admin():
        from database import list_users
        if session.get("current_user", None) == "ADMIN":
            user_list = list_users()
            user_table = zip(range(1, len(user_list)+1),\
                            user_list,\
                            [x + y for x,y in zip(["/delete_user/"] * len(user_list), user_list)])
            return render_template("admin.html", users = user_table)
        else:
            return abort(401)
    
    @app.route('/profile')
    def profile():
        if 'current_user' not in session:
            flash("You need to be logged in to view your profile.")
            return redirect(url_for('login'))

        # Continue with logic for displaying user profile
        return render_template('profile.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
