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
            return user.verify_password(pw)
        return False  # If no user found