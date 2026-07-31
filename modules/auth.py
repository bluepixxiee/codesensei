from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviews = db.relationship('Review', backref='user', lazy=True)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code_snippet = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), nullable=False)
    review_output = db.Column(db.Text, nullable=False)
    issues_count = db.Column(db.Integer, default=0)
    bug_count = db.Column(db.Integer, default=0)
    security_count = db.Column(db.Integer, default=0)
    performance_count = db.Column(db.Integer, default=0)
    style_count = db.Column(db.Integer, default=0)
    overall_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def register_user(name, email, password):
    existing = User.query.filter_by(email=email).first()
    if existing:
        return False, "Email already registered."
    hashed = generate_password_hash(password)
    user = User(name=name, email=email, password=hashed)
    db.session.add(user)
    db.session.commit()
    return True, user

def login_user(email, password):
    user = User.query.filter_by(email=email).first()
    if not user:
        return False, "Email not found."
    if not check_password_hash(user.password, password):
        return False, "Incorrect password."
    return True, user