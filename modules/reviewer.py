import os
import json
import re
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def review_code(code, language):
    prompt = (
        f"You are CodeSensei, an expert but encouraging code mentor for junior developers.\n\n"
        f"Review the following {language} code carefully and respond ONLY with a valid JSON object. "
        f"No text before or after the JSON. No markdown. Just raw JSON starting with {{ and ending with }}.\n\n"
        f"Code to review:\n{code}\n\n"
        f"Scoring guide:\n"
        f"- 90-100: Excellent code, production ready, minimal issues\n"
        f"- 75-89: Good code, minor improvements needed\n"
        f"- 60-74: Decent code, some important issues to fix\n"
        f"- 45-59: Needs work, multiple issues found\n"
        f"- 25-44: Significant problems, major issues present\n"
        f"- 0-24: Critical issues only, use this range sparingly for truly broken code\n\n"
        f"Be fair and encouraging. Most beginner code should score between 40-70 unless it has critical security vulnerabilities.\n\n"
        f"Respond with exactly this JSON structure:\n"
        f"{{\n"
        f'  "overall_score": <integer 0-100 based on scoring guide above>,\n'
        f'  "summary": "<2-3 sentence overall assessment, be encouraging but honest>",\n'
        f'  "issues": [\n'
        f'    {{\n'
        f'      "type": "<bug|security|performance|style>",\n'
        f'      "severity": "<high|medium|low>",\n'
        f'      "line": "<line number or range>",\n'
        f'      "title": "<short issue title>",\n'
        f'      "description": "<what is wrong and why it matters, explained for a junior developer>",\n'
        f'      "fix": "<exact corrected code or clear fix instruction>",\n'
        f'      "lesson": "<what concept the developer should learn to avoid this in future>"\n'
        f'    }}\n'
        f'  ],\n'
        f'  "strengths": ["<thing done well>", "<another strength>"],\n'
        f'  "top_learning": "<single most important thing this developer should study next>"\n'
        f"}}\n\n"
        f"Be thorough but educational. If the code has no issues, give a high score and empty issues array.\n"
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