# ⚡ CodeSensei — AI Code Review Assistant

An AI-powered code mentor for junior developers that reviews your code, 
explains issues in plain English, and tracks your improvement over time.

🔗 **Live Demo:** https://codesensei-0r9d.onrender.com

## Features
- 🐛 Bug detection with plain English explanations
- 🔒 Security vulnerability analysis
- ⚡ Performance issue identification
- 📈 Pattern tracking — know your repeated mistakes
- 📊 Skill dashboard with weakness detection
- 🌐 Supports Python, JavaScript, Java, C++, TypeScript, Go, Rust, SQL

## Tech Stack
- **Backend:** Python, Flask, SQLAlchemy, SQLite
- **AI:** Llama 3.3 70B via Groq API
- **Frontend:** HTML, CSS, JavaScript
- **Deployment:** Render

## How it works
1. Sign up and paste your code
2. Select your programming language
3. Get instant AI review with categorized issues and fixes
4. Track your patterns and improvement over time
5. Download detailed reports per review

## Run locally
```bash
git clone https://github.com/bluepixxiee/codesensei.git
cd codesensei
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# Add your GROQ_API_KEY to .env file
python app.py
```
