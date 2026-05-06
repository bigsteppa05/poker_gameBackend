from flask import Flask
from app.auth import auth_bp
from app.game import game_bp
from app.bcrypt import bcrypt


def create_app():
    app = Flask(__name__)

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(game_bp, url_prefix='/game')
    bcrypt.init_app(app)

    return app