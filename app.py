import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
load_dotenv()
from modules.auth import db, User, Review, register_user, login_user
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

@app.route("/login", methods=["GET", "POST"])
def login():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        data = request.get_json()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        success, result = login_user(email, password)
        if success:
            session["user_id"] = result.id
            return jsonify({"success": True})
        return jsonify({"success": False, "error": result})
    return render_template("login.html")

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
        success, result = register_user(name, email, password)
        if success:
            session["user_id"] = result.id
            return jsonify({"success": True})
        return jsonify({"success": False, "error": result})
    return render_template("signup.html")

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

        # get review from groq
        result = review_code(code, language)

        # count issues
        issues = result.get("issues", [])
        counts = count_issues_by_type(issues)

        # save to database
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

if __name__ == "__main__":
    app.run(debug=True)