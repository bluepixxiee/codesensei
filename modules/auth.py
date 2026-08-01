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
    reviews = db.relationship('Review', backref='user', lazy=True)

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

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp_code, purpose, name="there"):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_server = "smtp-relay.brevo.com"
    smtp_port = 587
    smtp_login = os.environ.get("BREVO_LOGIN")
    smtp_password = os.environ.get("BREVO_SMTP_KEY")
    sender_email = os.environ.get("SENDER_EMAIL")

    if purpose == "signup":
        subject = "Verify your CodeSensei account"
    else:
        subject = "Your CodeSensei login OTP"

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; background: #05010f; color: #f5f3ee; padding: 40px; border-radius: 16px;">
      <div style="text-align: center; margin-bottom: 32px;">
        <h1 style="font-size: 24px; color: #a78bfa; margin: 0;">⚡ CodeSensei</h1>
      </div>
      <h2 style="font-size: 20px; margin-bottom: 12px;">Hey {name}!</h2>
      <p style="color: #9ca3af; line-height: 1.6; margin-bottom: 28px;">
        {"Verify your account" if purpose == "signup" else "Here's your login OTP"} — enter this code:
      </p>
      <div style="background: #13102a; border: 1px solid rgba(99,102,241,0.3); border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 28px;">
        <div style="font-size: 40px; font-weight: 700; letter-spacing: 12px; color: #a78bfa;">{otp_code}</div>
        <div style="font-size: 13px; color: #6b7280; margin-top: 8px;">Expires in 10 minutes</div>
      </div>
      <p style="color: #6b7280; font-size: 13px;">If you didn't request this, ignore this email.</p>
    </div>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"CodeSensei <{sender_email}>"
        msg["To"] = email
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_login, smtp_password)
            server.sendmail(sender_email, email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

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