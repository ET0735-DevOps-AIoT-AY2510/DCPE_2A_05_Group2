# Purpose of this file: 
# Initialises Flask app + SQLAlchemy

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager

db = SQLAlchemy()
DB_NAME = "database.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'qwertyuiop'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    # Register the user interface app
    from .routes import directories
    app.register_blueprint(directories)

    # Register the staff interface app
    from .staff_routes import staff_directories
    app.register_blueprint(staff_directories)

    login_manager = LoginManager()
    login_manager.login_view = 'directories.login'
    login_manager.init_app(app)

    # User Loader Function
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return app

def create_database(app):
    if not path.exists('website/' + DB_NAME):
        with app.app_context():
            db.create_all()
        print('Created Database')
