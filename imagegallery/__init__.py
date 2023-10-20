from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from imagegallery.config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()


def db_init(app):
    db.init_app(app)

    with app.app_context():
        db.create_all()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    bcrypt.init_app(app)
    mail.init_app(app)

    from imagegallery.users.routes import users
    from imagegallery.posts.routes import post
    from imagegallery.main.routes import main
    from imagegallery.errors.handlers import errors
    app.register_blueprint(users)
    app.register_blueprint(post)
    app.register_blueprint(main)
    app.register_blueprint(errors)

    return app
