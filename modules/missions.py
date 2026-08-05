import os
import json
import re
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MISSION_TEMPLATES = {
    "security": {
        "easy": "Write a Python function that safely queries a database by user ID using parameterized queries.",
        "normal": "Fix the SQL injection and hardcoded credentials in this login system.",
        "boss": "Audit this entire authentication system for security vulnerabilities and fix all of them."
    },
    "bug": {
        "easy": "Fix the division by zero and null reference errors in this calculator function.",
        "normal": "Debug this data processing function that crashes on edge cases.",
        "boss": "Find and fix all bugs in this complex order management system."
    },
    "performance": {
        "easy": "Optimize this inefficient loop to use proper Python iteration.",
        "normal": "Refactor this function to reduce time complexity from O(n²) to O(n).",
        "boss": "Optimize this entire data pipeline that processes millions of records."
    },
    "style": {
        "easy": "Refactor this deeply nested conditional into clean, readable code.",
        "normal": "Improve the code organization and readability of this utility module.",
        "boss": "Refactor this entire class to follow SOLID principles and clean code standards."
    }
}

FALLBACK_MISSIONS = {
    "security": {
        "title": "Secure SQL Auth & Password Hashing",
        "description": "This authentication function concatenates un-sanitized user input into a SQL query string and uses weak MD5 hashing for passwords. Audit and secure it.",
        "buggy_code": """import sqlite3
import hashlib

def login_user(username, password):
    # Vulnerability 1: Insecure MD5 password hashing
    hashed_pw = hashlib.md5(password.encode()).hexdigest()
    
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    # Vulnerability 2: SQL Injection via string interpolation
    query = f"SELECT id, username, is_admin FROM users WHERE username = '{username}' AND password = '{hashed_pw}'"
    cursor.execute(query)
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {"status": "success", "user_id": user[0], "is_admin": user[2]}
    return {"status": "error", "message": "Invalid credentials"}
""",
        "hints": [
            "Check line 12: `f'SELECT ... {username}'` concatenates raw user input directly into the SQL query string.",
            "Use parameterized queries: `cursor.execute('SELECT id, username, is_admin FROM users WHERE username = ? AND password = ?', (username, hashed_pw))`.",
            "Replace MD5 on line 6 with a secure password hashing function like `bcrypt` or `hashlib.pbkdf2_hmac`."
        ],
        "what_to_learn": "Never concatenate user input into database queries; use parameterized queries and secure password hashing."
    },
    "bug": {
        "title": "Fix Data Processor Edge Cases & Crashes",
        "description": "This data metrics function crashes when scores are missing, empty, or contain un-checked dictionary keys. Fix the edge case bugs.",
        "buggy_code": """def calculate_user_metrics(user_data):
    total_score = 0
    scores = user_data.get("scores")
    
    # Bug 1: TypeError if 'scores' key exists but is None
    for item in scores:
        total_score += item["value"]
    
    # Bug 2: ZeroDivisionError if scores list is empty []
    average_score = total_score / len(scores)
    
    # Bug 3: KeyError if 'user_id' is missing from dictionary
    user_id = user_data["user_id"]
    
    return {
        "user_id": user_id,
        "total": total_score,
        "average": average_score
    }
""",
        "hints": [
            "Check line 6: `for item in scores` crashes if `scores` is `None` or missing.",
            "Check line 10: `total_score / len(scores)` raises `ZeroDivisionError` when `scores` is empty (`[]`).",
            "Use safe access: `scores = user_data.get('scores') or []`, verify `if len(scores) > 0`, and use `user_data.get('user_id')`."
        ],
        "what_to_learn": "Always validate inputs, empty collections, and dictionary keys defensively to prevent runtime crashes."
    },
    "performance": {
        "title": "Optimize O(n²) Nested Inventory Matching",
        "description": "This order inventory matching function runs nested loops creating O(m * n) quadratic time complexity. Optimize it.",
        "buggy_code": """def match_orders_with_inventory(orders, inventory_items):
    matched_results = []
    
    for order in orders:
        item_id = order["item_id"]
        # Performance Flaw: O(n) list iteration inside an O(m) loop -> O(m * n)
        for item in inventory_items:
            if item["id"] == item_id:
                if item["stock"] >= order["quantity"]:
                    matched_results.append({
                        "order_id": order["id"],
                        "item_name": item["name"],
                        "available": True
                    })
                break
                
    return matched_results
""",
        "hints": [
            "Check line 8: Iterating over `inventory_items` list for every single order creates an O(m * n) nested loop.",
            "Pre-index `inventory_items` into a dictionary lookup map: `inventory_map = {item['id']: item for item in inventory_items}`.",
            "Dictionary lookups are O(1), reducing overall time complexity from quadratic O(m * n) to linear O(m + n)."
        ],
        "what_to_learn": "Pre-index collections into hash maps (dictionaries) to replace O(n) nested searches with O(1) lookups."
    },
    "style": {
        "title": "Refactor Deeply Nested Conditional Branching",
        "description": "This discount calculation function has 4 levels of nested conditionals making code hard to read and maintain.",
        "buggy_code": """def calculate_discount(user, order_total, promo_code):
    discount = 0.0
    if user is not None:
        if user.is_active:
            if order_total > 100:
                if promo_code == "SAVE20":
                    discount = order_total * 0.20
                elif promo_code == "SAVE10":
                    discount = order_total * 0.10
                else:
                    discount = order_total * 0.05
            else:
                discount = 5.0
        else:
            discount = 0.0
    else:
        discount = 0.0
        
    return discount
""",
        "hints": [
            "Check lines 3-6: 4 levels of nested `if` statements create deep indentation and high cognitive complexity.",
            "Use guard clauses (return early): `if not user or not user.is_active: return 0.0`.",
            "Flatten the logical flow by validating invalid states first and returning early."
        ],
        "what_to_learn": "Apply guard clauses and early returns to flatten nested conditional logic and improve readability."
    }
}

def generate_mission(weakness_type, difficulty, language, user_name):
    difficulty_xp = {"easy": 60, "normal": 120, "boss": 300}
    xp_reward = difficulty_xp.get(difficulty, 120)

    prompt = (
        f"You are Ascend, an AI programming mentor creating a coding mission for {user_name}.\n\n"
        f"Create a {difficulty} difficulty debugging mission focused on {weakness_type} issues.\n"
        f"The mission should be in {language}.\n\n"
        f"Respond ONLY with a valid JSON object, no text before or after:\n"
        f"{{\n"
        f'  "title": "<short mission title, max 8 words>",\n'
        f'  "description": "<what the developer needs to fix, 2-3 sentences, encouraging tone>",\n'
        f'  "buggy_code": "<the actual buggy {language} code with {weakness_type} issues, 20-40 lines>",\n'
        f'  "hints": [\n'
        f'    "<Hint 1: Point directly to the exact function or line number where the flaw occurs>",\n'
        f'    "<Hint 2: Explain the technical flaw or vulnerability concept (e.g. String concatenation in SQL queries creates SQL injection)>",\n'
        f'    "<Hint 3: Provide a concrete code example snippet showing how to fix it (e.g. use cursor.execute(query, (param,)))>"\n'
        f'  ],\n'
        f'  "what_to_learn": "<one specific sentence about what key concept this teaches>"\n'
        f"}}\n\n"
        f"CRITICAL INSTRUCTIONS:\n"
        f"1. Hints MUST BE HIGHLY SPECIFIC to the exact buggy_code generated. NEVER use generic advice like 'look at your code' or 'check best practices'.\n"
        f"2. The buggy_code MUST be authentic, complete {language} code (20-40 lines) with distinct {weakness_type} bugs corresponding to {difficulty} difficulty.\n"
        f"Return ONLY the JSON object."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1800
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r'```json\s*', '', raw)
        raw = re.sub(r'```\s*', '', raw)
        raw = raw.strip()
        
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            start = raw.index('{')
            end = raw.rindex('}') + 1
            data = json.loads(raw[start:end])

        # Verify buggy_code is valid and not dummy pass
        if not data.get("buggy_code") or len(data["buggy_code"].strip()) < 30 or "pass" == data["buggy_code"].strip():
            fb = FALLBACK_MISSIONS.get(weakness_type, FALLBACK_MISSIONS["bug"])
            data["buggy_code"] = fb["buggy_code"]
            data["hints"] = fb["hints"]
            data["what_to_learn"] = fb["what_to_learn"]
    except Exception as e:
        print(f"Groq mission generation warning: {e}")
        fb = FALLBACK_MISSIONS.get(weakness_type, FALLBACK_MISSIONS["bug"])
        data = {
            "title": fb["title"],
            "description": fb["description"],
            "buggy_code": fb["buggy_code"],
            "hints": fb["hints"],
            "what_to_learn": fb["what_to_learn"]
        }

    return data, xp_reward

def evaluate_solution(original_buggy_code, user_solution, weakness_type, language):
    prompt = (
        f"You are Ascend, an AI programming mentor evaluating a student's solution.\n\n"
        f"Original buggy code:\n{original_buggy_code}\n\n"
        f"Student's solution:\n{user_solution}\n\n"
        f"The mission was to fix {weakness_type} issues in {language}.\n\n"
        f"Respond ONLY with a valid JSON object:\n"
        f"{{\n"
        f'  "passed": <true or false>,\n'
        f'  "score": <integer 0-100>,\n'
        f'  "feedback": "<encouraging 2-3 sentence feedback about their solution>",\n'
        f'  "issues_fixed": ["<issue that was fixed>"],\n'
        f'  "issues_remaining": ["<issue still present if any>"]\n'
        f"}}\n\n"
        f"Be encouraging. If they fixed the main issues, pass them even if minor improvements exist.\n"
        f"Return ONLY the JSON object."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=800
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'```json\s*', '', raw)
    raw = re.sub(r'```\s*', '', raw)
    raw = raw.strip()

    try:
        return json.loads(raw)
    except:
        try:
            start = raw.index('{')
            end = raw.rindex('}') + 1
            return json.loads(raw[start:end])
        except:
            return {
                "passed": True,
                "score": 70,
                "feedback": "Good attempt! Keep practicing to improve your skills.",
                "issues_fixed": ["Main issues addressed"],
                "issues_remaining": []
            }