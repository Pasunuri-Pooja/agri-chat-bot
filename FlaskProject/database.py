# database.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


def init_db(app=None):
    if app:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///agri_chatbot.db"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        db.init_app(app)
        with app.app_context():
            db.create_all()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    chats = db.relationship("ChatHistory", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def create(username, password):
        u = User(username=username)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        return u

    @staticmethod
    def get_by_username(username):
        return User.query.filter_by(username=username).first()


class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create(user_id, msg, resp):
        ch = ChatHistory(user_id=user_id, message=msg, response=resp)
        db.session.add(ch)
        db.session.commit()
        return ch