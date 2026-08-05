from datetime import date, datetime

# ── LEVEL SYSTEM ──────────────────────────────────────────
LEVELS = [
    {"level": 1,  "title": "Novice",           "min_xp": 0,     "icon": "🌱"},
    {"level": 2,  "title": "Apprentice",        "min_xp": 250,   "icon": "⚡"},
    {"level": 3,  "title": "Developer",         "min_xp": 700,   "icon": "💻"},
    {"level": 4,  "title": "Senior Developer",  "min_xp": 1500,  "icon": "🔥"},
    {"level": 5,  "title": "Tech Lead",         "min_xp": 2800,  "icon": "🚀"},
    {"level": 6,  "title": "Architect",         "min_xp": 4800,  "icon": "🏗️"},
    {"level": 7,  "title": "Expert",            "min_xp": 7500,  "icon": "⭐"},
    {"level": 8,  "title": "Master",            "min_xp": 11000, "icon": "👑"},
    {"level": 9,  "title": "Legend",            "min_xp": 16000, "icon": "🌟"},
    {"level": 10, "title": "Ascended",          "min_xp": 22000, "icon": "🔱"},
]

BADGES = [
    {"id": "first_review",     "name": "First Blood",        "desc": "Completed your first code review",           "icon": "🎯", "xp": 30},
    {"id": "clean_code",       "name": "Clean Coder",        "desc": "Got a score of 80+ on a review",             "icon": "✨", "xp": 50},
    {"id": "security_hawk",    "name": "Security Hawk",      "desc": "Found 5+ security issues total",             "icon": "🔒", "xp": 75},
    {"id": "bug_hunter",       "name": "Bug Hunter",         "desc": "Found 10+ bugs total",                       "icon": "🐛", "xp": 75},
    {"id": "streak_3",         "name": "On Fire",            "desc": "Maintained a 3-day review streak",           "icon": "🔥", "xp": 50},
    {"id": "streak_7",         "name": "Week Warrior",       "desc": "Maintained a 7-day review streak",           "icon": "⚡", "xp": 100},
    {"id": "mission_1",        "name": "Mission Accepted",   "desc": "Completed your first mission",               "icon": "🎮", "xp": 60},
    {"id": "mission_5",        "name": "Mission Master",     "desc": "Completed 5 missions",                       "icon": "🏆", "xp": 150},
    {"id": "boss_slayer",      "name": "Boss Slayer",        "desc": "Completed a Boss Battle mission",            "icon": "👹", "xp": 250},
    {"id": "polyglot",         "name": "Polyglot",           "desc": "Reviewed code in 3+ languages",              "icon": "🌐", "xp": 100},
    {"id": "perfectionist",    "name": "Perfectionist",      "desc": "Got a perfect score of 100",                 "icon": "💎", "xp": 150},
    {"id": "level_5",          "name": "Rising Star",        "desc": "Reached Tech Lead level",                    "icon": "🌠", "xp": 250},
]

def get_level_info(xp):
    current = LEVELS[0]
    next_level = LEVELS[1] if len(LEVELS) > 1 else None

    for i, lvl in enumerate(LEVELS):
        if xp >= lvl["min_xp"]:
            current = lvl
            next_level = LEVELS[i + 1] if i + 1 < len(LEVELS) else None

    xp_for_next = next_level["min_xp"] - xp if next_level else 0
    xp_progress = xp - current["min_xp"]
    xp_needed = (next_level["min_xp"] - current["min_xp"]) if next_level else 1
    progress_pct = min(100, int((xp_progress / xp_needed) * 100)) if xp_needed > 0 else 100

    return {
        "level": current["level"],
        "title": current["title"],
        "icon": current["icon"],
        "current_xp": xp,
        "next_level_xp": next_level["min_xp"] if next_level else xp,
        "xp_for_next": xp_for_next,
        "progress_pct": progress_pct,
        "is_max": next_level is None
    }

def calculate_xp_reward(score, issues_count, language):
    base_xp = 15  # base for submitting a review
    score_bonus = int(score * 0.15)  # up to 15 XP for high scores (score 100 = 15 XP)
    issue_bonus = min(issues_count * 2, 10)  # 2 XP per issue found, max 10
    return base_xp + score_bonus + issue_bonus

def update_streak(user):
    today = date.today()
    if user.last_review_date is None:
        user.streak = 1
    elif user.last_review_date == today:
        pass  # already reviewed today
    elif (today - user.last_review_date).days == 1:
        user.streak += 1  # consecutive day
    else:
        user.streak = 1  # streak broken
    user.last_review_date = today
    return user.streak

def update_mastery(user, bug_count, security_count, performance_count, style_count):
    # mastery increases when you encounter and presumably learn about issues
    # it's a weighted average that moves toward 100 as you consistently write clean code
    total = bug_count + security_count + performance_count + style_count

    if total == 0:
        # clean code - boost all masteries slightly
        user.bug_mastery = min(100, user.bug_mastery + 2)
        user.security_mastery = min(100, user.security_mastery + 2)
        user.performance_mastery = min(100, user.performance_mastery + 2)
        user.style_mastery = min(100, user.style_mastery + 2)
    else:
        # issues found - mastery grows but slower
        if bug_count > 0:
            user.bug_mastery = min(100, user.bug_mastery + max(0, 5 - bug_count))
        else:
            user.bug_mastery = min(100, user.bug_mastery + 3)

        if security_count > 0:
            user.security_mastery = min(100, user.security_mastery + max(0, 5 - security_count))
        else:
            user.security_mastery = min(100, user.security_mastery + 3)

        if performance_count > 0:
            user.performance_mastery = min(100, user.performance_mastery + max(0, 5 - performance_count))
        else:
            user.performance_mastery = min(100, user.performance_mastery + 3)

        if style_count > 0:
            user.style_mastery = min(100, user.style_mastery + max(0, 5 - style_count))
        else:
            user.style_mastery = min(100, user.style_mastery + 3)

    return user

def check_badges(user, reviews, score, new_review):
    earned = []
    review_count = len(reviews)
    total_bugs = sum(r.bug_count for r in reviews)
    total_security = sum(r.security_count for r in reviews)
    languages_used = set(r.language for r in reviews)
    max_score = max([score] + [r.overall_score for r in reviews]) if (reviews or score) else 0
    has_boss_slayer = any(getattr(m, 'difficulty', '') == 'boss' and getattr(m, 'is_completed', False) for m in getattr(user, 'missions', []))

    badge_checks = [
        ("first_review",  review_count >= 1),
        ("clean_code",    max_score >= 80),
        ("security_hawk", total_security >= 5),
        ("bug_hunter",    total_bugs >= 10),
        ("streak_3",      user.streak >= 3),
        ("streak_7",      user.streak >= 7),
        ("mission_1",     user.missions_completed >= 1),
        ("mission_5",     user.missions_completed >= 5),
        ("boss_slayer",   has_boss_slayer),
        ("polyglot",      len(languages_used) >= 3),
        ("perfectionist", max_score == 100),
        ("level_5",       user.level >= 5),
    ]

    for badge_id, condition in badge_checks:
        if condition:
            earned.append(badge_id)

    return earned

def get_badge_details(badge_ids):
    return [b for b in BADGES if b["id"] in badge_ids]

def get_weakness(user):
    masteries = {
        "security": user.security_mastery,
        "bug": user.bug_mastery,
        "performance": user.performance_mastery,
        "style": user.style_mastery
    }
    return min(masteries, key=masteries.get)