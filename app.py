import os
from flask import Flask, render_template, session, url_for, redirect, request, abort, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

load_dotenv()

#credentials

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config')

     # Debugging: Check if environment variables are loaded correctly
    print(f"DB_USER: {os.getenv('DB_USER')}")
    print(f"DB_PASSWORD: {os.getenv('DB_PASSWORD')}")
    print(f"DB_HOST: {os.getenv('DB_HOST')}")
    print(f"DB_NAME: {os.getenv('DB_NAME')}")
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_name = os.getenv('DB_NAME')


    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
    # app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqldb://{db_user}:{db_password}@localhost/{db_name}".format(
    #     db_user=db_user, db_password=db_password, db_name=db_name)
    
    # app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
    db.init_app(app)
    migrate.init_app(app,db)
    mail.init_app(app)

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
        from models import user, Book
        current_user = None

        if 'current_user' in session:
            current_user = user.query.filter_by(username=session['current_user']).first()

        # Fetch all books in the library system
        all_books = Book.query.all()

        # Optionally filter books based on the number of copies available
        available_books = [book for book in all_books if book.copies_available > 0]
        return render_template('index.html', current_user=current_user, available_books=available_books)

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
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            email = request.form.get("email", "").strip()
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

    @app.route("/admin/")
    def admin():
        from models import user, admin_request

        current_user = user.query.filter_by(username=session.get("current_user")).first()
        
        if not current_user or not current_user.is_admin:
            flash("You are not authorized to view this page.")
            return abort(401)
        
        # Retrieve pending admin requests, and eagerly load the associated user
        requests = admin_request.query.filter_by(status='Pending').all()

        for request in requests:
            request.user = user.query.get(request.user_id)

        return render_template("admin.html", requests=requests)
    
    @app.route('/admin_request', methods=['GET', 'POST'])
    def request_admin_request():
        from models import user, admin_request
        if 'current_user' not in session:
            flash("You need to be logged in to request admin status.")
            return redirect(url_for('login'))
        
        current_user = user.query.filter_by(username=session['current_user']).first()
        if not current_user:
            flash("User not found.")
            return redirect(url_for('login'))
        existing_request = admin_request.query.filter_by(user_id=current_user.user_id).first()
        # If the request exists, get its status
        if existing_request:
            request_status = existing_request.status
        else:
            request_status = None

        if request.method == 'POST':
            
            if existing_request:
                flash("You already submitted an admin request.")
                return redirect(url_for('profile'))
            #create and save new admin request
            new_request = admin_request(user_id=current_user.user_id, status='Pending')
            db.session.add(new_request)
            db.session.commit()

            flash("Your admin request has been submitted. You will be notified once it is reviewed.")
            return redirect(url_for('profile'))
        return render_template('admin_request.html', username=current_user.username, request_status=request_status)
    
    @app.route('/approve_admin_request/<int:request_id>')
    def approve_admin_request(request_id):
        from models import admin_request, user

        # Ensure the current user is an admin
        current_user = user.query.filter_by(username=session.get("current_user")).first()
        if not current_user or not current_user.is_admin:
            flash("You are not authorized to perform this action.")
            return abort(401)

        # Find the admin request and approve it
        request = admin_request.query.get(request_id)
        if request:
            user_to_approve = user.query.get(request.user_id)
            if user_to_approve:
                user_to_approve.is_admin = True  # Grant admin status
                request.status = 'Approved'  # Update the request status to Approved
                db.session.commit()
                flash(f"Admin request for {user_to_approve.username} has been approved.")
            else:
                flash("User associated with this request not found.")
        return redirect(url_for('admin'))

    @app.route('/deny_admin_request/<int:request_id>')
    def deny_admin_request(request_id):
        from models import admin_request, user

        # Ensure the current user is an admin
        current_user = user.query.filter_by(username=session.get("current_user")).first()
        if not current_user or not current_user.is_admin:
            flash("You are not authorized to perform this action.")
            return abort(401)

        # Find the admin request and deny it
        request = admin_request.query.get(request_id)
        if request:
            request.status = 'Denied'  # Mark the request as Denied
            db.session.commit()
            flash("Admin request has been denied.")
        return redirect(url_for('admin'))

    @app.route('/profile')
    def profile():
        from models import user, Loan, Reservation, Book
        if 'current_user' not in session:
            flash("You need to be logged in to view your profile.")
            return redirect(url_for('login'))

        # Continue with logic for displaying user profile
        current_user=user.query.filter_by(username=session['current_user']).first()
        
        if not current_user:
            flash("User not found.")
            return redirect(url_for('login'))
        # Get all books that the current user has loaned
        loaned_books = Loan.query.filter_by(user_id=current_user.user_id).all()
        
        # Get all books that the current user has reserved
        reserved_books = Reservation.query.filter_by(user_id=current_user.user_id, status='Pending').all()

        # Get the book details for each loan and reservation
        loaned_books_details = [Book.query.get(loan.book_id) for loan in loaned_books]
        reserved_books_details = [Book.query.get(reservation.book_id) for reservation in reserved_books]

        
        return render_template('profile.html', username=current_user.username, loaned_books=loaned_books_details, 
                               reserved_books=reserved_books_details)

    @app.route('/edit_profile', methods=['GET', 'POST'])
    def edit_profile():
        from models import user
        from werkzeug.security import generate_password_hash
        from sqlalchemy import and_

        if 'current_user' not in session:
            flash("You need to be logged in.")
            return redirect(url_for('login'))

        current_user = user.query.filter_by(username=session['current_user']).first()
        if not current_user:
            flash("User not found.")
            return redirect(url_for('login'))

        if request.method == "POST":
            new_username = request.form.get("new_username", "").strip()
            new_password = request.form.get("new_password", "").strip()

            # Check if new username is taken by someone else
            if new_username and new_username != current_user.username:
                existing_user = user.query.filter(and_(user.username == new_username, user.user_id != current_user.user_id)).first()
                if existing_user:
                    flash("Username already taken. Please choose a different one.", "danger")
                    return redirect(url_for('edit_profile'))

                current_user.username = new_username
                session["current_user"] = new_username  # update session

            if new_password:
                current_user.password = generate_password_hash(new_password)

            db.session.commit()
            flash("Profile updated successfully.")
            return redirect(url_for('profile'))

        return render_template("edit_profile.html", username=current_user.username)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
