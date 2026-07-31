from modules.auth import Review, db
from sqlalchemy import func

def get_user_stats(user_id):
    reviews = Review.query.filter_by(user_id=user_id).all()

    if not reviews:
        return {
            "total_reviews": 0,
            "avg_score": 0,
            "total_issues": 0,
            "weakness": "No reviews yet",
            "most_used_language": "N/A",
            "pattern_counts": {"bug": 0, "security": 0, "performance": 0, "style": 0},
            "score_trend": [],
            "recent_reviews": []
        }

    total_reviews = len(reviews)
    avg_score = round(sum(r.overall_score for r in reviews) / total_reviews, 1)
    total_issues = sum(r.issues_count for r in reviews)

    # pattern counts
    pattern_counts = {
        "bug": sum(r.bug_count for r in reviews),
        "security": sum(r.security_count for r in reviews),
        "performance": sum(r.performance_count for r in reviews),
        "style": sum(r.style_count for r in reviews)
    }

    # find biggest weakness
    weakness = max(pattern_counts, key=pattern_counts.get)
    weakness_labels = {
        "bug": "Bug Prevention",
        "security": "Security Practices",
        "performance": "Performance Optimization",
        "style": "Code Style & Readability"
    }

    # most used language
    lang_counts = {}
    for r in reviews:
        lang_counts[r.language] = lang_counts.get(r.language, 0) + 1
    most_used_language = max(lang_counts, key=lang_counts.get)

    # score trend (last 7 reviews)
    score_trend = [r.overall_score for r in reviews[-7:]]

    # recent reviews
    recent = sorted(reviews, key=lambda r: r.created_at, reverse=True)[:5]
    recent_reviews = [{
        "id": r.id,
        "language": r.language,
        "score": r.overall_score,
        "issues": r.issues_count,
        "date": r.created_at.strftime("%d %b %Y"),
        "snippet": r.code_snippet[:60] + "..."
    } for r in recent]

    return {
        "total_reviews": total_reviews,
        "avg_score": avg_score,
        "total_issues": total_issues,
        "weakness": weakness_labels.get(weakness, weakness),
        "most_used_language": most_used_language,
        "pattern_counts": pattern_counts,
        "score_trend": score_trend,
        "recent_reviews": recent_reviews
    }

def get_repeated_mistakes(user_id):
    reviews = Review.query.filter_by(user_id=user_id).all()
    if len(reviews) < 2:
        return []

    pattern_counts = {
        "bug": sum(r.bug_count for r in reviews),
        "security": sum(r.security_count for r in reviews),
        "performance": sum(r.performance_count for r in reviews),
        "style": sum(r.style_count for r in reviews)
    }

    repeated = []
    messages = {
        "bug": f"You've introduced bugs {pattern_counts['bug']} times — focus on testing edge cases and null checks.",
        "security": f"Security issues appeared {pattern_counts['security']} times — study input validation and safe coding practices.",
        "performance": f"Performance issues showed up {pattern_counts['performance']} times — learn about time complexity and efficient data structures.",
        "style": f"Style issues appeared {pattern_counts['style']} times — follow a consistent style guide for your language."
    }

    for key, count in pattern_counts.items():
        if count >= 2:
            repeated.append({"type": key, "count": count, "message": messages[key]})

    return sorted(repeated, key=lambda x: x["count"], reverse=True)