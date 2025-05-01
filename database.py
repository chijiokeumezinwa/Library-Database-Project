import hashlib
from models import user
from app import create_app, db

app = create_app()

def list_users():
    # Query to get all user IDs
    with app.app_context():
        users = user.query.with_entities(user.user_id).all()
        return [u.user_id for u in users]
   
def verify(id, pw):
    with app.app_context():
        user = user.query.filter_by(id=id).first()  # Retrieve the user by ID

        if user:
            stored_password_hash = user.pw
            provided_password_hash = hashlib.sha256(pw.encode()).hexdigest()

            return stored_password_hash == provided_password_hash

        return False  # If no user found