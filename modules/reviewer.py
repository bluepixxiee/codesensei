import os
import json
import re
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def review_code(code, language):
    prompt = (
        f"You are CodeSensei, an expert security-focused code mentor for junior developers.\n\n"
        f"Review the following {language} code and respond ONLY with a valid JSON object. "
        f"No text before or after the JSON. No markdown. Just raw JSON starting with {{ and ending with }}.\n\n"
        f"Code to review:\n{code}\n\n"
        f"IMPORTANT - Look carefully for ALL of these issue categories:\n\n"
        f"SECURITY (highest priority - never miss these):\n"
        f"- SQL injection (string concatenation in queries)\n"
        f"- Command injection (user input passed to exec/system/shell)\n"
        f"- Path traversal (user input used in file paths)\n"
        f"- Hardcoded credentials, API keys, passwords, tokens, secrets\n"
        f"- eval() or exec() used on user input or external data\n"
        f"- Sensitive data logged to console or files (passwords, card numbers, tokens)\n"
        f"- Missing authentication on sensitive endpoints\n"
        f"- Exposing sensitive data in API responses\n"
        f"- Plain text password storage (should use bcrypt/argon2)\n"
        f"- Weak hashing algorithms (MD5, SHA1 for passwords)\n"
        f"- XSS vulnerabilities\n"
        f"- CSRF vulnerabilities\n"
        f"- Insecure direct object references\n\n"
        f"BUGS (catch all of these):\n"
        f"- Division by zero risk\n"
        f"- Null/undefined/None reference errors\n"
        f"- Array/list index out of bounds\n"
        f"- Unhandled exceptions and missing error handling\n"
        f"- Unclosed file handles or database connections\n"
        f"- Race conditions\n"
        f"- Infinite loops\n"
        f"- Wrong data types\n"
        f"- Off by one errors\n\n"
        f"PERFORMANCE:\n"
        f"- Inefficient loops (using index when direct iteration works)\n"
        f"- N+1 query problems\n"
        f"- Unnecessary repeated operations inside loops\n"
        f"- Missing database indexes\n"
        f"- Loading entire files into memory unnecessarily\n"
        f"- Global mutable state\n\n"
        f"STYLE/QUALITY:\n"
        f"- Deeply nested conditionals (more than 3 levels)\n"
        f"- Functions doing too many things\n"
        f"- Dead code or unused variables\n"
        f"- Poor naming conventions\n"
        f"- Missing input validation\n"
        f"- Magic numbers without constants\n\n"
        f"Scoring guide:\n"
        f"- 85-100: Excellent, production ready\n"
        f"- 70-84: Good, minor issues\n"
        f"- 50-69: Decent, some important fixes needed\n"
        f"- 30-49: Significant problems found\n"
        f"- 0-29: Critical security vulnerabilities present\n\n"
        f"Code with SQL injection, command injection, or hardcoded secrets should NEVER score above 40.\n"
        f"Be thorough — it is better to report too many issues than to miss critical ones.\n\n"
        f"Respond with exactly this JSON structure:\n"
        f"{{\n"
        f'  "overall_score": <integer 0-100>,\n'
        f'  "summary": "<2-3 sentence assessment>",\n'
        f'  "issues": [\n'
        f'    {{\n'
        f'      "type": "<bug|security|performance|style>",\n'
        f'      "severity": "<high|medium|low>",\n'
        f'      "line": "<line number or range>",\n'
        f'      "title": "<short issue title>",\n'
        f'      "description": "<what is wrong and why it matters for a junior developer>",\n'
        f'      "fix": "<exact corrected code>",\n'
        f'      "lesson": "<what to learn to avoid this in future>"\n'
        f'    }}\n'
        f'  ],\n'
        f'  "strengths": ["<thing done well>"],\n'
        f'  "top_learning": "<most important thing to study next>"\n'
        f"}}\n\n"
        f"Return ONLY the JSON object, nothing else."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000
    )

    raw = response.choices[0].message.content.strip()

    # aggressively extract JSON from response
    raw = re.sub(r'```json\s*', '', raw)
    raw = re.sub(r'```\s*', '', raw)
    raw = raw.strip()

    # try to find JSON object in response
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        try:
            start = raw.index('{')
            end = raw.rindex('}') + 1
            json_str = raw[start:end]
            result = json.loads(json_str)
        except (ValueError, json.JSONDecodeError):
            result = {
                "overall_score": 50,
                "summary": "Review completed but formatting had an issue. Please try again.",
                "issues": [],
                "strengths": ["Code was submitted successfully"],
                "top_learning": "Try submitting again for a detailed review."
            }

    return result


def count_issues_by_type(issues):
    counts = {"bug": 0, "security": 0, "performance": 0, "style": 0}
    for issue in issues:
        t = issue.get("type", "style").lower()
        if t in counts:
            counts[t] += 1
    return counts