import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from dotenv import load_dotenv
from datetime import datetime, date
import tempfile

load_dotenv()

from modules.auth import db, User, Review, Mission, register_user, login_user_check, get_user_by_email, create_otp, verify_otp, send_otp_email
from modules.reviewer import review_code, count_issues_by_type
from modules.tracker import get_user_stats, get_repeated_mistakes
from modules.gamification import calculate_xp_reward, update_streak, update_mastery, check_badges, get_level_info, get_badge_details, get_weakness, LEVELS, BADGES
from modules.missions import generate_mission, evaluate_solution
from modules.pdf_report import generate_pdf_report

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ascend_secret_2024")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///ascend.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)

db.init_app(app)

with app.app_context():
    db.create_all()
    # migrate existing SQLite DBs to add new columns without wiping data
    try:
        import sqlite3
        db_path = os.path.join("instance", "ascend.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(mission)")
            existing = [row[1] for row in cur.fetchall()]
            if "hints" not in existing:
                cur.execute("ALTER TABLE mission ADD COLUMN hints TEXT")
            if "what_to_learn" not in existing:
                cur.execute("ALTER TABLE mission ADD COLUMN what_to_learn TEXT")
            
            # Auto-repair any old dummy missions created before prompt update
            from modules.missions import FALLBACK_MISSIONS
            for weakness, fb in FALLBACK_MISSIONS.items():
                cur.execute("""
                    UPDATE mission 
                    SET buggy_code = ?, hints = ?, description = ?, what_to_learn = ? 
                    WHERE weakness_type = ? AND (buggy_code LIKE '%pass%' OR LENGTH(buggy_code) < 30 OR hints IS NULL)
                """, (fb["buggy_code"], json.dumps(fb["hints"]), fb["description"], fb["what_to_learn"], weakness))
            
            conn.commit()
            conn.close()
    except Exception as _e:
        print(f"DB migration warning: {_e}")

# ── helpers ──────────────────────────────────────────────
def is_logged_in():
    return "user_id" in session

def current_user():
    if is_logged_in():
        try:
            return db.session.get(User, session["user_id"])
        except:
            return None
    return None

# ── public routes ─────────────────────────────────────────
@app.route("/")
def landing():
    return render_template("landing.html", user=current_user())

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
        if existing and not existing.is_verified:
            db.session.delete(existing)
            db.session.commit()
        success, result = register_user(name, email, password)
        if not success:
            return jsonify({"success": False, "error": result})
        otp_code = create_otp(email, "signup")
        send_otp_email(email, otp_code, "signup", name)
        session["pending_email"] = email
        return jsonify({"success": True, "redirect": "/verify-otp/signup"})
    return render_template("signup.html")

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

@app.route("/resend-otp", methods=["POST"])
def resend_otp():
    email = session.get("pending_email", "")
    purpose = request.get_json().get("purpose", "signup")
    if not email:
        return jsonify({"success": False, "error": "Session expired."})
    user = get_user_by_email(email)
    name = user.name if user else "there"
    otp_code = create_otp(email, purpose)
    send_otp_email(email, otp_code, purpose, name)
    return jsonify({"success": True, "message": "OTP resent successfully."})

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
    try:
        user = current_user()
        if not user:
            session.clear()
            return redirect(url_for("login"))
        reviews = Review.query.filter_by(user_id=user.id).all()
        level_info = get_level_info(user.xp)
        stats = get_user_stats(user.id)
        mistakes = get_repeated_mistakes(user.id)
        earned_badge_ids = check_badges(user, reviews, 0, None)
        badges = get_badge_details(earned_badge_ids)
        active_missions = Mission.query.filter_by(user_id=user.id, is_completed=False).all()
        completed_missions = Mission.query.filter_by(user_id=user.id, is_completed=True).count()

        return render_template("dashboard.html",
            user=user,
            level_info=level_info,
            stats=stats,
            mistakes=mistakes,
            badges=badges,
            active_missions=active_missions,
            completed_missions=completed_missions,
            levels=LEVELS
        )
    except Exception as e:
        print(f"Dashboard error: {e}")
        session.clear()
        return redirect(url_for("login"))

@app.route("/history")
def history_page():
    if not is_logged_in():
        return redirect(url_for("login"))
    user = current_user()
    if not user:
        session.clear()
        return redirect(url_for("login"))
    reviews = Review.query.filter_by(user_id=user.id).order_by(Review.created_at.desc()).all()
    level_info = get_level_info(user.xp)
    formatted_reviews = []
    for r in reviews:
        snippet = r.code_snippet[:100] + ("..." if len(r.code_snippet) > 100 else "")
        score_class = "score-high" if r.overall_score >= 70 else ("score-mid" if r.overall_score >= 50 else "score-low")
        formatted_reviews.append({
            "id": r.id,
            "language": r.language,
            "score": r.overall_score,
            "score_class": score_class,
            "issues_count": r.issues_count,
            "bug_count": r.bug_count,
            "security_count": r.security_count,
            "performance_count": r.performance_count,
            "style_count": r.style_count,
            "snippet": snippet,
            "created_at": r.created_at.strftime("%b %d, %Y at %H:%M") if r.created_at else ""
        })
    return render_template("history.html", user=user, level_info=level_info, reviews=formatted_reviews)

@app.route("/review")
def review_page():
    if not is_logged_in():
        return redirect(url_for("login"))
    return render_template("review.html", user=current_user())

@app.route("/missions")
def missions_page():
    if not is_logged_in():
        return redirect(url_for("login"))
    user = current_user()
    active = Mission.query.filter_by(user_id=user.id, is_completed=False).all()
    completed = Mission.query.filter_by(user_id=user.id, is_completed=True).all()
    return render_template("missions.html", user=user, active_missions=active, completed_missions=completed)

@app.route("/mission/<int:mission_id>")
def mission_detail(mission_id):
    if not is_logged_in():
        return redirect(url_for("login"))
    user = current_user()
    mission = Mission.query.filter_by(id=mission_id, user_id=user.id).first()
    if not mission:
        return redirect(url_for("missions_page"))
    level_info = get_level_info(user.xp)
    hints = json.loads(mission.hints) if mission.hints else []
    what_to_learn = mission.what_to_learn or ""
    return render_template("mission_detail.html",
        user=user, mission=mission, level_info=level_info,
        hints=hints, what_to_learn=what_to_learn
    )

@app.route("/report/<int:review_id>")
def report(review_id):
    if not is_logged_in():
        return redirect(url_for("login"))
    user = current_user()
    rev = Review.query.filter_by(id=review_id, user_id=user.id).first()
    if not rev:
        return redirect(url_for("dashboard"))
    review_data = json.loads(rev.review_output)
    level_info = get_level_info(user.xp)
    return render_template("report.html", user=user, review=rev, data=review_data, level_info=level_info)

# ── api routes ────────────────────────────────────────────
@app.route("/api/review", methods=["POST"])
def api_review():
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    try:
        if request.files.get("file"):
            file = request.files["file"]
            code = file.read().decode("utf-8")
            language = request.form.get("language", "python")
        else:
            data = request.get_json()
            code = data.get("code", "").strip()
            language = data.get("language", "python")

        if not code:
            return jsonify({"error": "No code provided"}), 400
        if len(code) > 10000:
            return jsonify({"error": "Code too long - max 10000 characters"}), 400

        result = review_code(code, language)
        issues = result.get("issues", [])
        counts = count_issues_by_type(issues)
        score = result.get("overall_score", 50)

        user = current_user()

        # save review
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
            overall_score=score
        )
        db.session.add(rev)

        # gamification updates
        xp_earned = calculate_xp_reward(score, len(issues), language)
        user.xp += xp_earned
        user.total_reviews += 1
        user.total_issues_found += len(issues)
        update_streak(user)
        update_mastery(user, counts["bug"], counts["security"], counts["performance"], counts["style"])

        # update level
        level_info = get_level_info(user.xp)
        old_level = user.level
        user.level = level_info["level"]
        leveled_up = user.level > old_level

        db.session.commit()

        # check if mission should be generated
        weakness = get_weakness(user)
        should_suggest_mission = user.total_reviews % 2 == 0 or len(issues) >= 3

        mission_suggestion = None
        if should_suggest_mission:
            difficulty = "easy" if user.level <= 2 else "boss" if user.level >= 7 else "normal"
            mission_suggestion = {
                "weakness": weakness,
                "difficulty": difficulty,
                "message": f"Based on your {weakness} weakness, we have a mission for you!"
            }

        return jsonify({
            "success": True,
            "review_id": rev.id,
            "result": result,
            "xp_earned": xp_earned,
            "total_xp": user.xp,
            "level_info": level_info,
            "leveled_up": leveled_up,
            "streak": user.streak,
            "mission_suggestion": mission_suggestion
        })

    except UnicodeDecodeError:
        return jsonify({"error": "File must be a text/code file"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/generate-mission", methods=["POST"])
def api_generate_mission():
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    try:
        data = request.get_json()
        weakness = data.get("weakness", "bug")
        difficulty = data.get("difficulty", "normal")
        language = data.get("language", "Python")

        user = current_user()
        mission_data, xp_reward = generate_mission(weakness, difficulty, language, user.name)

        mission = Mission(
            user_id=user.id,
            title=mission_data.get("title", "Debugging Mission"),
            description=mission_data.get("description", "Fix the issues in this code."),
            buggy_code=mission_data.get("buggy_code", "# Fix this code"),
            language=language,
            difficulty=difficulty,
            xp_reward=xp_reward,
            weakness_type=weakness,
            hints=json.dumps(mission_data.get("hints", [])),
            what_to_learn=mission_data.get("what_to_learn", "")
        )
        db.session.add(mission)
        db.session.commit()

        return jsonify({
            "success": True,
            "mission_id": mission.id,
            "mission": {
                "title": mission.title,
                "description": mission.description,
                "difficulty": mission.difficulty,
                "xp_reward": mission.xp_reward,
                "hints": mission_data.get("hints", []),
                "what_to_learn": mission_data.get("what_to_learn", "")
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/submit-mission/<int:mission_id>", methods=["POST"])
def api_submit_mission(mission_id):
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    try:
        user = current_user()
        mission = Mission.query.filter_by(id=mission_id, user_id=user.id).first()
        if not mission:
            return jsonify({"error": "Mission not found"}), 404
        if mission.is_completed:
            return jsonify({"error": "Mission already completed"}), 400

        data = request.get_json()
        user_solution = data.get("solution", "")
        hints_used = min(3, max(0, int(data.get("hints_used", 0))))

        penalty_per_hint = max(15, int(mission.xp_reward * 0.15))
        total_penalty = hints_used * penalty_per_hint
        actual_xp_reward = max(10, mission.xp_reward - total_penalty)

        evaluation = evaluate_solution(
            mission.buggy_code,
            user_solution,
            mission.weakness_type,
            mission.language
        )

        if evaluation.get("passed"):
            mission.is_completed = True
            mission.user_solution = user_solution
            mission.completed_at = datetime.utcnow()
            user.xp += actual_xp_reward
            user.missions_completed += 1
            level_info = get_level_info(user.xp)
            old_level = user.level
            user.level = level_info["level"]
            leveled_up = user.level > old_level
            db.session.commit()

            return jsonify({
                "success": True,
                "passed": True,
                "xp_earned": actual_xp_reward,
                "hints_used": hints_used,
                "total_penalty": total_penalty,
                "total_xp": user.xp,
                "level_info": level_info,
                "leveled_up": leveled_up,
                "evaluation": evaluation
            })
        else:
            db.session.commit()
            return jsonify({
                "success": True,
                "passed": False,
                "evaluation": evaluation
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/download-report/<int:review_id>")
def download_report(review_id):
    if not is_logged_in():
        return redirect(url_for("login"))
    try:
        user = current_user()
        rev = Review.query.filter_by(id=review_id, user_id=user.id).first()
        if not rev:
            return jsonify({"error": "Report not found"}), 404

        review_data = json.loads(rev.review_output)
        counts = {
            "bug": rev.bug_count,
            "security": rev.security_count,
            "performance": rev.performance_count,
            "style": rev.style_count
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        generate_pdf_report(
            review_data=review_data,
            code_snippet=rev.code_snippet,
            language=rev.language,
            overall_score=rev.overall_score,
            issue_counts=counts,
            output_path=tmp_path
        )

        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=f"ascend_report_{review_id}.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/user/stats")
def api_user_stats():
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    user = current_user()
    level_info = get_level_info(user.xp)
    return jsonify({
        "xp": user.xp,
        "level": level_info,
        "streak": user.streak,
        "total_reviews": user.total_reviews,
        "missions_completed": user.missions_completed,
        "mastery": {
            "security": round(user.security_mastery, 1),
            "bug": round(user.bug_mastery, 1),
            "performance": round(user.performance_mastery, 1),
            "style": round(user.style_mastery, 1)
        }
    })

if __name__ == "__main__":
    app.run(debug=True)