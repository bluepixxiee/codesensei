from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random
import os
import requests

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # gamification
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    streak = db.Column(db.Integer, default=0)
    last_review_date = db.Column(db.Date, default=None)
    total_reviews = db.Column(db.Integer, default=0)
    total_issues_found = db.Column(db.Integer, default=0)
    missions_completed = db.Column(db.Integer, default=0)

    # skill mastery (0-100)
    security_mastery = db.Column(db.Float, default=0.0)
    bug_mastery = db.Column(db.Float, default=0.0)
    performance_mastery = db.Column(db.Float, default=0.0)
    style_mastery = db.Column(db.Float, default=0.0)

    reviews = db.relationship('Review', backref='user', lazy=True)
    missions = db.relationship('Mission', backref='user', lazy=True)

class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)  # 'signup' or 'login'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)

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

class Mission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    buggy_code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), default="normal")  # easy/normal/boss
    xp_reward = db.Column(db.Integer, default=100)
    weakness_type = db.Column(db.String(50), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    user_solution = db.Column(db.Text, nullable=True)
    hints = db.Column(db.Text, nullable=True)          # JSON list of hint strings
    what_to_learn = db.Column(db.Text, nullable=True)  # single sentence
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp_code, purpose, name="there"):
    print(f"OTP for {email}: {otp_code}")
    return True

def create_otp(email, purpose):
    # delete any existing unused OTPs for this email and purpose
    OTP.query.filter_by(email=email, purpose=purpose, is_used=False).delete()
    db.session.commit()

    otp_code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    otp = OTP(
        email=email,
        otp_code=otp_code,
        purpose=purpose,
        expires_at=expires_at
    )
    db.session.add(otp)
    db.session.commit()
    return otp_code

def verify_otp(email, otp_code, purpose):
    otp = OTP.query.filter_by(
        email=email,
        otp_code=otp_code,
        purpose=purpose,
        is_used=False
    ).first()

    if not otp:
        return False, "Invalid OTP."
    if datetime.utcnow() > otp.expires_at:
        return False, "OTP has expired. Please request a new one."

    otp.is_used = True
    db.session.commit()
    return True, "OTP verified."

def register_user(name, email, password):
    existing = User.query.filter_by(email=email).first()
    if existing:
        return False, "Email already registered."
    hashed = generate_password_hash(password)
    user = User(name=name, email=email, password=hashed, is_verified=False)
    db.session.add(user)
    db.session.commit()
    return True, user

def login_user_check(email, password):
    user = User.query.filter_by(email=email).first()
    if not user:
        return False, "Email not found."
    if not check_password_hash(user.password, password):
        return False, "Incorrect password."
    return True, user

def get_user_by_email(email):
    return User.query.filter_by(email=email).first()