import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
load_dotenv()
from modules.auth import (db, User, Review, register_user, login_user_check,
                          get_user_by_email, create_otp, verify_otp, send_otp_email)
from modules.reviewer import review_code, count_issues_by_type
from modules.tracker import get_user_stats, get_repeated_mistakes
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = "codesensei_secret_2024"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///codesensei.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# ── helpers ──────────────────────────────────────────────
def is_logged_in():
    return "user_id" in session

def current_user():
    if is_logged_in():
        return User.query.get(session["user_id"])
    return None

# ── public routes ─────────────────────────────────────────
@app.route("/")
def landing():
    return render_template("landing.html", user=current_user())

# SIGNUP - step 1: collect details and send OTP
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        data = request.get_json()
        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not name or not email or not password:
            return jsonify({"success": False, "error": "All fields are required."})
        if len(password) < 6:
            return jsonify({"success": False, "error": "Password must be at least 6 characters."})

        existing = User.query.filter_by(email=email).first()
        if existing and existing.is_verified:
            return jsonify({"success": False, "error": "Email already registered."})

        # delete unverified existing user and recreate
        if existing and not existing.is_verified:
            db.session.delete(existing)
            db.session.commit()

        success, result = register_user(name, email, password)
        if not success:
            return jsonify({"success": False, "error": result})

        # send OTP
        otp_code = create_otp(email, "signup")
        email_sent = send_otp_email(email, otp_code, "signup", name)

        if not email_sent:
            return jsonify({"success": False, "error": "Failed to send OTP. Please try again."})

        # store in session temporarily
        session["pending_email"] = email
        return jsonify({"success": True, "redirect": "/verify-otp/signup"})

    return render_template("signup.html")

# SIGNUP - step 2: verify OTP
@app.route("/verify-otp/<purpose>", methods=["GET", "POST"])
def verify_otp_page(purpose):
    if request.method == "POST":
        data = request.get_json()
        otp_code = data.get("otp", "").strip()
        email = session.get("pending_email", "")

        if not email:
            return jsonify({"success": False, "error": "Session expired. Please try again."})

        success, message = verify_otp(email, otp_code, purpose)
        if not success:
            return jsonify({"success": False, "error": message})

        if purpose == "signup":
            user = get_user_by_email(email)
            user.is_verified = True
            db.session.commit()
            session.pop("pending_email", None)
            session["user_id"] = user.id
            return jsonify({"success": True, "redirect": "/dashboard"})

        elif purpose == "login":
            user = get_user_by_email(email)
            session.pop("pending_email", None)
            session["user_id"] = user.id
            return jsonify({"success": True, "redirect": "/dashboard"})

    return render_template("verify_otp.html", purpose=purpose)

# RESEND OTP
@app.route("/resend-otp", methods=["POST"])
def resend_otp():
    email = session.get("pending_email", "")
    purpose = request.get_json().get("purpose", "signup")

    if not email:
        return jsonify({"success": False, "error": "Session expired."})

    user = get_user_by_email(email)
    name = user.name if user else "there"

    otp_code = create_otp(email, purpose)
    email_sent = send_otp_email(email, otp_code, purpose, name)

    if not email_sent:
        return jsonify({"success": False, "error": "Failed to send OTP."})

    return jsonify({"success": True, "message": "OTP resent successfully."})

# LOGIN - step 1: verify password and send OTP
@app.route("/login", methods=["GET", "POST"])
def login():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        data = request.get_json()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        success, result = login_user_check(email, password)
        if not success:
            return jsonify({"success": False, "error": result})

        if not result.is_verified:
            return jsonify({"success": False, "error": "Account not verified. Please sign up again."})

        # direct login — no OTP needed
        session["user_id"] = result.id
        return jsonify({"success": True, "redirect": "/dashboard"})

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

# ── protected routes ──────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login"))
    user = current_user()
    stats = get_user_stats(user.id)
    mistakes = get_repeated_mistakes(user.id)
    return render_template("dashboard.html", user=user, stats=stats, mistakes=mistakes)

@app.route("/review")
def review_page():
    if not is_logged_in():
        return redirect(url_for("login"))
    return render_template("review.html", user=current_user())

@app.route("/report/<int:review_id>")
def report(review_id):
    if not is_logged_in():
        return redirect(url_for("login"))
    user = current_user()
    rev = Review.query.filter_by(id=review_id, user_id=user.id).first()
    if not rev:
        return redirect(url_for("dashboard"))
    review_data = json.loads(rev.review_output)
    return render_template("report.html", user=user, review=rev, data=review_data)

# ── api routes ────────────────────────────────────────────
@app.route("/api/review", methods=["POST"])
def api_review():
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    try:
        data = request.get_json()
        code = data.get("code", "").strip()
        language = data.get("language", "python")

        if not code:
            return jsonify({"error": "No code provided"}), 400
        if len(code) > 5000:
            return jsonify({"error": "Code too long — max 5000 characters"}), 400

        result = review_code(code, language)
        issues = result.get("issues", [])
        counts = count_issues_by_type(issues)

        user = current_user()
        rev = Review(
            user_id=user.id,
            code_snippet=code,
            language=language,
            review_output=json.dumps(result),
            issues_count=len(issues),
            bug_count=counts["bug"],
            security_count=counts["security"],
            performance_count=counts["performance"],
            style_count=counts["style"],
            overall_score=result.get("overall_score", 50)
        )
        db.session.add(rev)
        db.session.commit()

        return jsonify({
            "success": True,
            "review_id": rev.id,
            "result": result
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats")
def api_stats():
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    user = current_user()
    stats = get_user_stats(user.id)
    return jsonify(stats)

@app.route("/test-email")
def test_email():
    from modules.auth import send_otp_email
    result = send_otp_email(
        "aditisharma230105@gmail.com",
        "123456",
        "signup",
        "Aditi"
    )
    return f"Email sent: {result}"

if __name__ == "__main__":
    app.run(debug=True)