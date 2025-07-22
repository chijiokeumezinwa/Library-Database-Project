import sys
import os

# Add your project directory to the Python path
project_home = u'/home/ubuntu/projects/Library-Database-Project'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import the create_app function from app.py
from app import create_app

# Create the Flask application instance and name it 'application'
# Gunicorn looks for a callable named 'application' by default
application = create_app()